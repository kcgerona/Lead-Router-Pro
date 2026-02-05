#!/bin/bash
# SQLite Database Management Script for Lead Router Pro

set -e

DB_PATH="./data/smart_lead_router.db"
BACKUP_DIR="./backups"

echo "🗄️  SQLite Database Management"
echo "=============================="

# Create directories if they don't exist
mkdir -p data backups

case "$1" in
    "backup")
        echo "📦 Creating backup..."
        cp "$DB_PATH" "$BACKUP_DIR/smart_lead_router_$(date +%Y%m%d_%H%M%S).db"
        echo "✅ Backup completed in $BACKUP_DIR"
        ;;
    
    "restore")
        if [ -z "$2" ]; then
            echo "❌ Please specify backup file to restore"
            echo "Usage: $0 restore <backup_file>"
            exit 1
        fi
        echo "🔄 Restoring from $2..."
        cp "$2" "$DB_PATH"
        echo "✅ Database restored"
        ;;
    
    "list")
        echo "📋 Available backups:"
        ls -la "$BACKUP_DIR"/*.db 2>/dev/null || echo "No backups found"
        ;;
    
    "info")
        if [ -f "$DB_PATH" ]; then
            echo "📊 Database Information:"
            echo "   File: $DB_PATH"
            echo "   Size: $(du -h "$DB_PATH" | cut -f1)"
            echo "   Modified: $(stat -c %y "$DB_PATH")"
            
            # Quick record count
            python3 -c "
import sqlite3
conn = sqlite3.connect('$DB_PATH')
cursor = conn.cursor()
tables = ['accounts', 'vendors', 'leads', 'users', 'activity_log']
for table in tables:
    try:
        cursor.execute(f'SELECT COUNT(*) FROM {table}')
        count = cursor.fetchone()[0]
        print(f'   {table}: {count:,} records')
    except:
        pass
conn.close()
"
        else
            echo "❌ Database file not found: $DB_PATH"
        fi
        ;;
    
    "init")
        echo "🆕 Initializing new database..."
        if [ -f "$DB_PATH" ]; then
            echo "⚠️  Database already exists. Backup first:"
            echo "   $0 backup"
        else
            python3 -c "
from database.simple_connection import SimpleDatabase
db = SimpleDatabase()
print('✅ Database initialized successfully')
"
        fi
        ;;
    
    *)
        echo "Usage: $0 {backup|restore|list|info|init}"
        echo ""
        echo "Commands:"
        echo "  backup     - Create a timestamped backup"
        echo "  restore    - Restore from backup file"
        echo "  list       - List available backups"
        echo "  info       - Show database information"
        echo "  init       - Initialize new database"
        echo ""
        echo "Examples:"
        echo "  $0 backup"
        echo "  $0 restore ./backups/smart_lead_router_20240204_120000.db"
        echo "  $0 list"
        echo "  $0 info"
        ;;
esac
