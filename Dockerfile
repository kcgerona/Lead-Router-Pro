FROM python:3.11-slim-bullseye

WORKDIR /app

RUN cat /etc/resolv.conf

# Install system dependencies
RUN apt-get clean && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app

# Create necessary writable directories and set ownership
# /app/data and /app/data/security for DB and security_data.json (ip_security)
# Do not create smart_lead_router.db here - let the app create it on first run so we never overwrite existing DB
RUN mkdir -p /app/data/security /app/security_data /app/uploads /app/logs /app/storage/security && \
    chown -R app:app /app && \
    chmod -R 775 /app/data /app/security_data /app/uploads /app/logs /app/storage

# Switch to non-root user
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
