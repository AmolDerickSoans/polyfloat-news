# Polyfloat News - Deployment Guide

## Prerequisites

- **VPS**: 2GB RAM, 1 vCPU (Hetzner €4.45/mo or DigitalOcean $6/mo)
- **OS**: Ubuntu 22.04 LTS (recommended)
- **Domain**: Not required for testing (use ngrok)
- **Python**: 3.11+
- **Docker**: For Nitter instances

## Development Setup (Local)

### 1. Clone Repository

```bash
cd ~/Documents/polyfloat-news
git init
```

### 2. Create Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Start Nitter Containers

```bash
docker-compose up -d
```

Verify instances are running:
```bash
curl http://localhost:8081
curl http://localhost:8082
curl http://localhost:8083
```

### 5. Initialize Database

```bash
python scripts/init_db.py
```

### 6. Start API Server

```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 7. Test with ngrok

```bash
# In another terminal
ngrok http 8000

# Test WebSocket
wscat -c ws://your-ngrok-url.ngrok-free.app/ws/news?user_id=test123
```

---

## VPS Deployment (Production)

### 1. Server Setup

```bash
# SSH into VPS
ssh root@your-vps-ip

# Update system
apt update && apt upgrade -y

# Install dependencies
apt install -y python3.11 python3-pip python3-venv \
    git docker.io docker-compose nginx

# Create user
useradd -m -s /bin/bash newsapi
usermod -aG docker newsapi
```

### 2. Deploy Code

```bash
# Switch to newsapi user
su - newsapi

# Clone repository (or copy files)
cd /opt
git clone https://github.com/your-org/polyfloat-news.git
cd polyfloat-news

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
# Create .env file
cp .env.example .env
nano .env

# Edit as needed
# DATABASE_URL=/opt/polyfloat-news/news_api.db
# LOG_LEVEL=INFO
```

### 4. Initialize Database

```bash
python scripts/init_db.py
```

### 5. Start Nitter Containers

```bash
docker-compose up -d
```

Verify instances:
```bash
curl http://localhost:8081
curl http://localhost:8082
curl http://localhost:8083
```

### 6. Configure Systemd Service

```bash
# Create systemd service file
sudo nano /etc/systemd/system/polyfloat-news.service
```

Paste the following:
```ini
[Unit]
Description=Polyfloat News API
After=network.target docker.service

[Service]
Type=simple
User=newsapi
WorkingDirectory=/opt/polyfloat-news
Environment="PYTHONUNBUFFERED=1"
Environment="DATABASE_URL=/opt/polyfloat-news/news_api.db"
ExecStart=/opt/polyfloat-news/.venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable polyfloat-news
sudo systemctl start polyfloat-news

# Check status
sudo systemctl status polyfloat-news

# View logs
sudo journalctl -u polyfloat-news -f
```

---

## Nginx Configuration (Optional)

### Install Nginx

```bash
sudo apt install -y nginx
```

### Configure Nginx

```bash
sudo nano /etc/nginx/sites-available/polyfloat-news
```

Paste the following:
```nginx
# HTTP Server (for testing)
server {
    listen 80;
    server_name news.polyfloat.com;

    # WebSocket upgrade
    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        # WebSocket timeout
        proxy_read_timeout 86400;
    }

    # API endpoints
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;

        # Rate limiting
        limit_req zone=api_limit burst=20;
    }

    # Health check
    location /health {
        proxy_pass http://127.0.0.1:8000;
    }

    # Rate limiting zone
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
}
```

Enable site and restart Nginx:
```bash
sudo ln -s /etc/nginx/sites-available/polyfloat-news /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## SSL Certificate (When Domain is Ready)

### Using Let's Encrypt (Certbot)

```bash
# Install certbot
sudo apt install -y certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d news.polyfloat.com

# Certbot will update Nginx config automatically

# Test auto-renewal
sudo certbot renew --dry-run
```

### SSL Configuration

Certbot will update your Nginx config to include:
```nginx
server {
    listen 443 ssl http2;
    server_name news.polyfloat.com;

    ssl_certificate /etc/letsencrypt/live/news.polyfloat.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/news.polyfloat.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;

    # ... rest of config
}
```

---

## Monitoring

### Systemd Logs

```bash
# View logs
sudo journalctl -u polyfloat-news -f

# View last 100 lines
sudo journalctl -u polyfloat-news -n 100
```

### Application Logs

Logs are written to stdout/stderr and captured by systemd.

### Health Checks

```bash
# Check API health
curl http://localhost:8000/health

# Check WebSocket connection
wscat -c ws://localhost:8000/ws/news?user_id=health_check
```

### Stats Endpoint

```bash
curl http://localhost:8000/api/v1/stats
```

---

## Backup Strategy

### Database Backup

```bash
# Create backup script
nano /opt/polyfloat-news/scripts/backup.sh
```

```bash
#!/bin/bash
# Backup script

BACKUP_DIR="/opt/polyfloat-news/backups"
DB_PATH="/opt/polyfloat-news/news_api.db"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup database
cp $DB_PATH $BACKUP_DIR/news_api_$TIMESTAMP.db

# Keep last 7 days
find $BACKUP_DIR -name "news_api_*.db" -mtime +7 -delete

# Optional: Upload to S3
# aws s3 cp $BACKUP_DIR/news_api_$TIMESTAMP.db s3://backups/polyfloat-news/
```

```bash
chmod +x /opt/polyfloat-news/scripts/backup.sh

# Add to crontab (daily at 2 AM)
crontab -e
```

```
0 2 * * * /opt/polyfloat-news/scripts/backup.sh
```

---

## Troubleshooting

### Service Won't Start

```bash
# Check service status
sudo systemctl status polyfloat-news

# View logs
sudo journalctl -u polyfloat-news -n 50

# Common issues:
# - Port 8000 already in use
# - Python dependencies missing
# - Database not initialized
# - Nitter containers not running
```

### Nitter Instances Not Responding

```bash
# Check containers
docker ps -a | grep nitter

# View logs
docker logs nitter-1
docker logs nitter-2
docker logs nitter-3

# Restart containers
docker-compose restart
```

### WebSocket Connection Fails

```bash
# Check Nginx configuration
sudo nginx -t

# Check if WebSocket upgrade is working
curl -i -H "Connection: Upgrade" -H "Upgrade: websocket" http://localhost:8000/ws/news

# Check Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### High Memory Usage

```bash
# Check memory
free -h
htop

# If SQLite is growing:
# - Check for old news items
# - Run cleanup script
python scripts/cleanup_db.py

# Restart service to free memory
sudo systemctl restart polyfloat-news
```

### Database Locked

```bash
# Check SQLite locks
sqlite3 news_api.db "PRAGMA database_list;"

# If WAL mode issues:
sqlite3 news_api.db "PRAGMA journal_mode=WAL;"
```

---

## Scaling Up

### Adding More Nitter Instances

Edit `docker-compose.yml`:
```yaml
services:
  nitter-1: ...  # existing
  nitter-2: ...  # existing
  nitter-3: ...  # existing
  nitter-4:      # new
    image: zedeus/nitter:latest
    container_name: nitter-4
    ports:
      - "8084:8080"
    restart: always
```

Update `NitterScraper.INSTANCES` in code:
```python
INSTANCES = [
    "http://localhost:8081",
    "http://localhost:8082",
    "http://localhost:8083",
    "http://localhost:8084",  # new
]
```

### Adding More VPS Instances

1. Deploy same setup on new VPS
2. Add load balancer (Nginx or HAProxy)
3. Configure round-robin or least-connections

---

## Rollback

### Revert to Previous Version

```bash
cd /opt/polyfloat-news
git log --oneline -10

# Checkout previous version
git checkout abc123

# Restart service
sudo systemctl restart polyfloat-news
```

### Restore Database Backup

```bash
# Stop service
sudo systemctl stop polyfloat-news

# Restore backup
cp /opt/polyfloat-news/backups/news_api_20251228_020000.db \
   /opt/polyfloat-news/news_api.db

# Start service
sudo systemctl start polyfloat-news
```

---

## Cost Summary

| Component | Monthly Cost |
|-----------|--------------|
| VPS (2GB RAM, 1 vCPU) | $4.95 - $6 |
| Domain (if needed) | $1 - $2 |
| SSL Certificate | $0 (Let's Encrypt) |
| Monitoring (optional) | $0 - $10 |
| Backup Storage (S3, optional) | $0 - $5 |
| **TOTAL** | **$5.95 - $23/month** |

---

## Next Steps

1. Deploy to VPS
2. Test with ngrok
3. Add domain and SSL (when ready)
4. Set up monitoring
5. Configure backups
6. Test Polyfloat terminal integration
