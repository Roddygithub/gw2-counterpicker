# GW2 CounterPicker - Deployment Guide

## Overview

This guide covers deploying GW2 CounterPicker v4.0 (Core Engine) to a production server.

## Prerequisites

- Ubuntu/Debian Linux server
- Python 3.11+
- Git
- Sudo access
- Domain name (optional)

## Server Setup

### 1. Install System Dependencies

```bash
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip git nginx
```

### 2. Create Application User

```bash
sudo useradd -m -s /bin/bash syff
sudo usermod -aG sudo syff
```

### 3. Clone Repository

```bash
sudo su - syff
cd ~
git clone https://github.com/YOUR_USERNAME/gw2-counterpicker.git
cd gw2-counterpicker
```

### 4. Create Virtual Environment

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 5. Configure Environment

Create `.env` file (optional):

```bash
# Application settings
APP_ENV=production
LOG_LEVEL=INFO

# Database path (default: data/)
DB_PATH=data

# Server settings
HOST=0.0.0.0
PORT=8001
```

### 6. Create Systemd Service

Create `/etc/systemd/system/gw2-counterpicker.service`:

```ini
[Unit]
Description=GW2 CounterPicker - WvW Intelligence Tool
After=network.target

[Service]
Type=simple
User=syff
Group=syff
WorkingDirectory=/home/syff/gw2-counterpicker
Environment="PATH=/home/syff/gw2-counterpicker/venv/bin"
ExecStart=/home/syff/gw2-counterpicker/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8001 --workers 2
Restart=always
RestartSec=10

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/home/syff/gw2-counterpicker/data

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable gw2-counterpicker
sudo systemctl start gw2-counterpicker
sudo systemctl status gw2-counterpicker
```

### 7. Configure Nginx (Optional)

Create `/etc/nginx/sites-available/gw2-counterpicker`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support (if needed)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    location /static {
        alias /home/syff/gw2-counterpicker/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/gw2-counterpicker /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 8. SSL Certificate (Optional)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## GitHub Actions Setup

### Required Secrets

Configure these secrets in your GitHub repository settings:

- `SSH_HOST`: `82.64.171.203`
- `SSH_PORT`: `2222`
- `SSH_USER`: `syff`
- `SSH_KEY`: Your private SSH key (generate with `ssh-keygen`)
- `DEPLOY_PATH`: `/home/syff/gw2-counterpicker`

### Generate SSH Key

On your local machine:

```bash
ssh-keygen -t ed25519 -C "github-actions@gw2-counterpicker"
```

Add the public key to the server:

```bash
ssh-copy-id -p 2222 syff@82.64.171.203
```

Copy the private key content to GitHub Secrets as `SSH_KEY`.

## Manual Deployment

Use the deployment script:

```bash
cd /home/syff/gw2-counterpicker
./scripts/deploy.sh
```

Or manually:

```bash
cd /home/syff/gw2-counterpicker
git pull origin main
source venv/bin/activate
pip install -r requirements.txt --upgrade
sudo systemctl restart gw2-counterpicker
```

## Monitoring

### Check Service Status

```bash
sudo systemctl status gw2-counterpicker
```

### View Logs

```bash
sudo journalctl -u gw2-counterpicker -f
```

### Health Check

```bash
curl http://localhost:8001/health
```

Expected response:
```json
{
  "status": "operational",
  "message": "GW2 CounterPicker v4.0 - Stats Engine",
  "stats_status": {
    "total_fights": 123,
    "win_rate": 65.4,
    "status": "active",
    "engine": "stats_based"
  }
}
```

## Database Backup

Backup the TinyDB database:

```bash
cd /home/syff/gw2-counterpicker
tar -czf backup-$(date +%Y%m%d).tar.gz data/
```

Restore from backup:

```bash
tar -xzf backup-YYYYMMDD.tar.gz
sudo systemctl restart gw2-counterpicker
```

## Troubleshooting

### Service won't start

Check logs:
```bash
sudo journalctl -u gw2-counterpicker -n 50 --no-pager
```

Check permissions:
```bash
ls -la /home/syff/gw2-counterpicker/data/
```

### Port already in use

Check what's using port 8001:
```bash
sudo lsof -i :8001
```

### High memory usage

Reduce workers in systemd service:
```ini
ExecStart=/home/syff/gw2-counterpicker/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8001 --workers 1
```

## Performance Tuning

### Uvicorn Workers

For production, use 2-4 workers based on CPU cores:

```bash
--workers $(nproc)
```

### Database Optimization

TinyDB is lightweight but for high traffic, consider:
- Regular database compaction
- Archiving old fights (>6 months)
- Indexing frequently queried fields

### Nginx Caching

Add caching for static assets in nginx config:

```nginx
location /static {
    alias /home/syff/gw2-counterpicker/static;
    expires 30d;
    add_header Cache-Control "public, immutable";
}
```

## Security Checklist

- [ ] Firewall configured (UFW)
- [ ] SSH key authentication only
- [ ] Non-root user for application
- [ ] SSL certificate installed
- [ ] Regular security updates
- [ ] Database backups automated
- [ ] Rate limiting enabled
- [ ] File upload validation active

## Maintenance

### Weekly Tasks

- Check disk space: `df -h`
- Review logs for errors
- Verify backups

### Monthly Tasks

- Update system packages: `sudo apt update && sudo apt upgrade`
- Review and archive old fight data
- Check SSL certificate expiry

### Quarterly Tasks

- Review and update dependencies
- Performance analysis
- Security audit

## Support

For issues or questions:
- Check logs: `sudo journalctl -u gw2-counterpicker -f`
- Review GitHub issues
- Check application health: `curl http://localhost:8001/health`
