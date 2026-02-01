#!/bin/bash

# Lead Router Pro - VPS Deployment Script
# Server: dockside.life (167.88.39.177)

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
VPS_IP="165.22.34.21"
VPS_USER="root"
DOMAIN="v2.dockside.life"
APP_USER="leadrouter"
REPO_URL="https://github.com/kcgerona/Lead-Router-Pro.git"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Lead Router Pro - VPS Deployment Script${NC}"
echo -e "${BLUE}========================================${NC}"

# Function to run commands on VPS
run_on_vps() {
    ssh -o StrictHostKeyChecking=no $VPS_USER@$VPS_IP "$1"
}

# Function to copy files to VPS
copy_to_vps() {
    scp -o StrictHostKeyChecking=no "$1" $VPS_USER@$VPS_IP:"$2"
}

echo -e "${YELLOW}Step 1: Testing VPS Connection...${NC}"
if run_on_vps "echo 'Connection successful'"; then
    echo -e "${GREEN}✓ VPS connection established${NC}"
else
    echo -e "${RED}✗ Failed to connect to VPS${NC}"
    exit 1
fi

echo -e "${YELLOW}Step 2: System Updates and Security Setup...${NC}"
run_on_vps "
    export DEBIAN_FRONTEND=noninteractive
    apt update && apt upgrade -y
    apt install -y curl wget git htop nano ufw fail2ban python3 python3-pip python3-venv python3-dev
    apt install -y build-essential libssl-dev libffi-dev python3-setuptools sqlite3 nginx redis-server
    apt install -y certbot python3-certbot-nginx apache2-utils unattended-upgrades
"

echo -e "${YELLOW}Step 3: Configuring Firewall...${NC}"
run_on_vps "
    ufw default deny incoming
    ufw default allow outgoing
    ufw allow ssh
    ufw allow 80/tcp
    ufw allow 443/tcp
    ufw allow 8000/tcp
    echo 'y' | ufw enable
    systemctl enable fail2ban
    systemctl start fail2ban
    systemctl enable redis-server
    systemctl start redis-server
"

echo -e "${YELLOW}Step 4: Creating Application User...${NC}"
run_on_vps "
    if ! id '$APP_USER' &>/dev/null; then
        adduser --disabled-password --gecos '' $APP_USER
        usermod -aG sudo $APP_USER
        mkdir -p /home/$APP_USER/.ssh
        cp /root/.ssh/authorized_keys /home/$APP_USER/.ssh/ 2>/dev/null || true
        chown -R $APP_USER:$APP_USER /home/$APP_USER/.ssh
        chmod 700 /home/$APP_USER/.ssh
        chmod 600 /home/$APP_USER/.ssh/authorized_keys 2>/dev/null || true
    fi
"

echo -e "${YELLOW}Step 5: Creating Database Directory...${NC}"
run_on_vps "
    mkdir -p /var/lib/leadrouter/db
    mkdir -p /var/log/leadrouter
    chown -R $APP_USER:$APP_USER /var/lib/leadrouter
    chown -R $APP_USER:$APP_USER /var/log/leadrouter
"

echo -e "${YELLOW}Step 6: Cloning Repository...${NC}"
run_on_vps "
    sudo -u $APP_USER bash -c '
        cd /home/$APP_USER
        if [ -d \"Lead-Router-Pro\" ]; then
            cd Lead-Router-Pro
            git pull
        else
            git clone $REPO_URL
            cd Lead-Router-Pro
        fi
        python3 -m venv venv
        source venv/bin/activate
        pip install --upgrade pip
        pip install -r requirements.txt
    '
"

echo -e "${YELLOW}Step 7: Creating Environment File...${NC}"
run_on_vps "
    sudo -u $APP_USER bash -c '
        cd /home/$APP_USER/Lead-Router-Pro
        if [ ! -f .env ]; then
            cp .env.example .env
            sed -i \"s/ENVIRONMENT=.*/ENVIRONMENT=production/\" .env
            sed -i \"s/DEBUG=.*/DEBUG=False/\" .env
            sed -i \"s|DATABASE_URL=.*|DATABASE_URL=sqlite:///var/lib/leadrouter/db/smart_lead_router.db|\" .env
            echo \"ALLOWED_HOSTS=$DOMAIN,www.$DOMAIN,$VPS_IP\" >> .env
            echo \"LOG_LEVEL=INFO\" >> .env
            echo \"LOG_FILE=/var/log/leadrouter/app.log\" >> .env
        fi
    '
"

echo -e "${YELLOW}Step 8: Creating Systemd Service...${NC}"
run_on_vps "cat > /etc/systemd/system/leadrouter.service << 'EOF'
[Unit]
Description=Lead Router Pro FastAPI application
After=network.target

[Service]
Type=exec
User=$APP_USER
Group=$APP_USER
RuntimeDirectory=leadrouter
WorkingDirectory=/home/$APP_USER/Lead-Router-Pro
Environment=PATH=/home/$APP_USER/Lead-Router-Pro/venv/bin
ExecStart=/home/$APP_USER/Lead-Router-Pro/venv/bin/uvicorn main_working_final:app --host 0.0.0.0 --port 8000 --workers 4
ExecReload=/bin/kill -s HUP \$MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF"

echo -e "${YELLOW}Step 9: Creating Nginx Configuration...${NC}"
run_on_vps "cat > /etc/nginx/sites-available/$DOMAIN << 'EOF'
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN $VPS_IP;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection \"1; mode=block\";

    # Rate limiting
    limit_req_zone \$binary_remote_addr zone=api:10m rate=10r/s;

    # Main application
    location / {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_redirect off;
        
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Webhook endpoints - higher rate limits
    location /api/v1/webhooks/ {
        limit_req zone=api burst=50 nodelay;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_redirect off;
        
        client_max_body_size 10M;
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://127.0.0.1:8000/api/v1/webhooks/health;
        access_log off;
    }
}
EOF"

echo -e "${YELLOW}Step 10: Enabling Nginx Site...${NC}"
run_on_vps "
    ln -sf /etc/nginx/sites-available/$DOMAIN /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default
    nginx -t
    systemctl restart nginx
"

echo -e "${YELLOW}Step 11: Creating Monitoring Script...${NC}"
run_on_vps "cat > /home/$APP_USER/monitor.sh << 'EOF'
#!/bin/bash
LOG_FILE=\"/var/log/leadrouter/monitor.log\"
API_URL=\"http://localhost:8000/api/v1/webhooks/health\"

if ! systemctl is-active --quiet leadrouter; then
    echo \"\$(date): Lead Router service is down!\" >> \$LOG_FILE
    systemctl restart leadrouter
fi

HTTP_STATUS=\$(curl -s -o /dev/null -w \"%{http_code}\" \$API_URL)
if [ \"\$HTTP_STATUS\" != \"200\" ]; then
    echo \"\$(date): API health check failed with status \$HTTP_STATUS\" >> \$LOG_FILE
fi

DISK_USAGE=\$(df / | awk 'NR==2{print \$5}' | sed 's/%//')
if [ \"\$DISK_USAGE\" -gt 80 ]; then
    echo \"\$(date): Disk usage is at \${DISK_USAGE}%\" >> \$LOG_FILE
fi
EOF

chmod +x /home/$APP_USER/monitor.sh
chown $APP_USER:$APP_USER /home/$APP_USER/monitor.sh
"

echo -e "${YELLOW}Step 12: Creating Backup Script...${NC}"
run_on_vps "cat > /home/$APP_USER/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR=\"/home/$APP_USER/backups\"
DB_PATH=\"/var/lib/leadrouter/db/smart_lead_router.db\"
DATE=\$(date +%Y%m%d_%H%M%S)

mkdir -p \$BACKUP_DIR

if [ -f \"\$DB_PATH\" ]; then
    cp \$DB_PATH \"\$BACKUP_DIR/db_backup_\$DATE.db\"
fi

tar -czf \"\$BACKUP_DIR/app_backup_\$DATE.tar.gz\" -C /home/$APP_USER Lead-Router-Pro

find \$BACKUP_DIR -name \"*.db\" -mtime +7 -delete
find \$BACKUP_DIR -name \"*.tar.gz\" -mtime +7 -delete
EOF

chmod +x /home/$APP_USER/backup.sh
chown $APP_USER:$APP_USER /home/$APP_USER/backup.sh
"

echo -e "${YELLOW}Step 13: Setting up Cron Jobs...${NC}"
run_on_vps "
    sudo -u $APP_USER bash -c '
        (crontab -l 2>/dev/null; echo \"*/5 * * * * /home/$APP_USER/monitor.sh\") | crontab -
        (crontab -l 2>/dev/null; echo \"0 2 * * * /home/$APP_USER/backup.sh\") | crontab -
    '
"

echo -e "${YELLOW}Step 14: Starting Services...${NC}"
run_on_vps "
    systemctl daemon-reload
    systemctl enable leadrouter
    systemctl start leadrouter
    systemctl status leadrouter --no-pager
"

echo -e "${YELLOW}Step 15: Testing Application...${NC}"
sleep 5
if run_on_vps "curl -s http://localhost:8000/api/v1/webhooks/health | grep -q 'healthy'"; then
    echo -e "${GREEN}✓ Application is running and healthy${NC}"
else
    echo -e "${RED}✗ Application health check failed${NC}"
    run_on_vps "journalctl -u leadrouter --no-pager -n 20"
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Deployment Summary:${NC}"
echo -e "${GREEN}✓ Server configured and secured${NC}"
echo -e "${GREEN}✓ Application deployed${NC}"
echo -e "${GREEN}✓ Services started${NC}"
echo -e "${GREEN}✓ Monitoring configured${NC}"
echo -e "${GREEN}✓ Backup strategy implemented${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Configure SSL: sudo certbot --nginx -d $DOMAIN -d www.$DOMAIN"
echo "2. Update .env file with your GHL credentials"
echo "3. Update GHL webhook URLs to: https://$DOMAIN/api/v1/webhooks/..."
echo "4. Test all webhook endpoints"
echo ""
echo -e "${BLUE}Application URL: http://$DOMAIN${NC}"
echo -e "${BLUE}Health Check: http://$DOMAIN/health${NC}"
echo -e "${BLUE}SSH Access: ssh $APP_USER@$VPS_IP${NC}"
echo -e "${BLUE}Logs: sudo journalctl -u leadrouter -f${NC}"
