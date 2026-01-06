# Deployment Guide

Complete guide for deploying the Sensor Data Collector in various environments.

---

## Table of Contents

- [Deployment Overview](#deployment-overview)
- [Prerequisites](#prerequisites)
- [Local Development Deployment](#local-development-deployment)
- [Production Deployment](#production-deployment)
- [Docker Deployment](#docker-deployment)
- [System Service Deployment](#system-service-deployment)
- [Cloud Deployment](#cloud-deployment)
- [Cloudflare Tunnel Setup](#cloudflare-tunnel-setup)
- [Environment Configuration](#environment-configuration)
- [Monitoring & Maintenance](#monitoring--maintenance)
- [Troubleshooting](#troubleshooting)
- [Security Best Practices](#security-best-practices)

---

## Deployment Overview

### Deployment Scenarios

| Scenario | Use Case | Complexity |
|----------|----------|------------|
| **Local Development** | Testing, development | Low |
| **Single Server** | Small deployment, < 20 sensors | Low |
| **System Service** | Always-on production server | Medium |
| **Docker Container** | Containerized deployment | Medium |
| **Cloud VM** | Remote hosting | Medium-High |
| **Kubernetes** | Large-scale, multi-instance | High |

### Network Requirements

- Access to local network where sensors are located
- Outbound HTTPS access to external data endpoint
- (Optional) Inbound access for frontend communication

---

## Prerequisites

### System Requirements

**Minimum:**
- OS: Linux, macOS, or Windows
- Python: 3.9 or higher
- RAM: 256MB
- Disk: 100MB
- Network: Access to sensor network

**Recommended:**
- OS: Linux (Ubuntu 20.04+, Debian 11+)
- Python: 3.11
- RAM: 512MB
- Disk: 1GB
- CPU: 2+ cores for multiple sensors

### Software Prerequisites

```bash
# Update system (Ubuntu/Debian)
sudo apt update && sudo apt upgrade -y

# Install Python 3.9+
sudo apt install python3 python3-pip python3-venv

# Install Git
sudo apt install git

# Optional: Install cloudflared
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb
```

---

## Local Development Deployment

### Quick Start

```bash
# 1. Clone repository
git clone <repository-url>
cd sensor-data-collector/backend

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp env.example.txt .env
nano .env  # Edit with your settings

# 5. Run development server
uvicorn app.main:app --reload --port 8000
```

### Development Configuration

`.env` file for development:

```env
# Use local test endpoint
EXTERNAL_ENDPOINT_URL=http://localhost:8000/api/test/upload/csv
EXTERNAL_ENDPOINT_TOKEN=test-sensor-api-key-12345

# Short polling interval for testing
POLLING_INTERVAL=30

# Development CORS
FRONTEND_URL=http://localhost:5173

# Server config
HOST=127.0.0.1
PORT=8000
```

### Verify Installation

```bash
# Check health endpoint
curl http://localhost:8000/health

# View API docs
open http://localhost:8000/docs
```

---

## Production Deployment

### Step-by-Step Production Setup

#### 1. Server Preparation

```bash
# Create dedicated user
sudo useradd -m -s /bin/bash sensorapp
sudo su - sensorapp

# Create application directory
mkdir -p /home/sensorapp/sensor-collector
cd /home/sensorapp/sensor-collector
```

#### 2. Application Setup

```bash
# Clone repository
git clone <repository-url> .
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

#### 3. Production Configuration

Create `/home/sensorapp/sensor-collector/backend/.env`:

```env
# Production endpoint
EXTERNAL_ENDPOINT_URL=https://oberlin.communityhub.cloud/api/data-hub/upload/csv
EXTERNAL_ENDPOINT_TOKEN=your-production-token-here

# Production settings
POLLING_INTERVAL=60
FRONTEND_URL=https://your-frontend-domain.com

# Server config
HOST=0.0.0.0
PORT=8000
```

**Secure the configuration file:**

```bash
chmod 600 .env
chown sensorapp:sensorapp .env
```

#### 4. Test Production Setup

```bash
# Activate virtual environment
source venv/bin/activate

# Run server
uvicorn app.main:app --host 0.0.0.0 --port 8000

# In another terminal, test
curl http://localhost:8000/health
```

---

## Docker Deployment

### Dockerfile

Create `backend/Dockerfile`:

```dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app ./app

# Create non-root user
RUN useradd -m -u 1000 sensorapp && chown -R sensorapp:sensorapp /app
USER sensorapp

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  sensor-collector:
    build: ./backend
    container_name: sensor-collector
    restart: unless-stopped
    ports:
      - "8000:8000"
    env_file:
      - backend/.env
    environment:
      - HOST=0.0.0.0
      - PORT=8000
    networks:
      - sensor-network
    # Mount for logs (optional)
    volumes:
      - ./logs:/app/logs

networks:
  sensor-network:
    driver: bridge
```

### Build and Run

```bash
# Build image
docker-compose build

# Start service
docker-compose up -d

# View logs
docker-compose logs -f

# Stop service
docker-compose down
```

### Docker Best Practices

**Multi-stage Build:**

```dockerfile
# Stage 1: Builder
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY app ./app
ENV PATH=/root/.local/bin:$PATH
USER nobody
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0"]
```

---

## System Service Deployment

### systemd Service (Linux)

Create `/etc/systemd/system/sensor-collector.service`:

```ini
[Unit]
Description=Sensor Data Collector API
After=network.target
Documentation=https://github.com/your-repo/sensor-data-collector

[Service]
Type=simple
User=sensorapp
Group=sensorapp
WorkingDirectory=/home/sensorapp/sensor-collector/backend
Environment="PATH=/home/sensorapp/sensor-collector/backend/venv/bin"
EnvironmentFile=/home/sensorapp/sensor-collector/backend/.env

ExecStart=/home/sensorapp/sensor-collector/backend/venv/bin/uvicorn \
    app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 1

Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=sensor-collector

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/home/sensorapp/sensor-collector

[Install]
WantedBy=multi-user.target
```

### Service Management

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable sensor-collector

# Start service
sudo systemctl start sensor-collector

# Check status
sudo systemctl status sensor-collector

# View logs
sudo journalctl -u sensor-collector -f

# Restart service
sudo systemctl restart sensor-collector

# Stop service
sudo systemctl stop sensor-collector

# Disable service
sudo systemctl disable sensor-collector
```

### Log Rotation

Create `/etc/logrotate.d/sensor-collector`:

```
/var/log/sensor-collector/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 sensorapp sensorapp
    sharedscripts
    postrotate
        systemctl reload sensor-collector > /dev/null
    endscript
}
```

---

## Cloud Deployment

### AWS EC2

#### 1. Launch Instance

```bash
# Launch Ubuntu instance (t2.micro is sufficient for testing)
# Security Group: Allow inbound on port 8000 (or use ALB)
```

#### 2. Connect and Setup

```bash
# Connect via SSH
ssh -i your-key.pem ubuntu@ec2-xx-xx-xx-xx.compute.amazonaws.com

# Update system
sudo apt update && sudo apt upgrade -y

# Follow Production Deployment steps above
```

#### 3. Configure Security Group

```
Inbound Rules:
- Port 8000 (TCP) from your IP or 0.0.0.0/0 (if using public access)
- Port 22 (SSH) from your IP

Outbound Rules:
- Allow all (for sensor access and external endpoint)
```

#### 4. (Optional) Use Application Load Balancer

```bash
# Configure ALB with:
# - Target Group: Port 8000
# - Health Check: GET /health
# - SSL/TLS certificate for HTTPS
```

### Google Cloud Platform

#### 1. Create Compute Engine Instance

```bash
gcloud compute instances create sensor-collector \
    --image-family=ubuntu-2004-lts \
    --image-project=ubuntu-os-cloud \
    --machine-type=e2-micro \
    --zone=us-central1-a
```

#### 2. Configure Firewall

```bash
gcloud compute firewall-rules create allow-sensor-api \
    --allow=tcp:8000 \
    --source-ranges=0.0.0.0/0 \
    --description="Allow Sensor Collector API"
```

#### 3. Connect and Deploy

```bash
gcloud compute ssh sensor-collector --zone=us-central1-a
# Follow production deployment steps
```

### Digital Ocean

#### 1. Create Droplet

- Choose Ubuntu 20.04 or 22.04
- Select Basic plan ($4-6/month is sufficient)
- Add SSH key
- Enable monitoring (recommended)

#### 2. Deploy Application

```bash
ssh root@your-droplet-ip
# Follow production deployment steps
```

### Heroku (Not Recommended)

Heroku is not ideal for this application because:
- Needs persistent network access to local sensors
- Typically sensors are on private networks
- Better suited for local or VPN-connected deployment

---

## Cloudflare Tunnel Setup

Cloudflare Tunnel allows secure access to your local backend from a hosted frontend.

### One-Time Setup

```bash
# Install cloudflared
# macOS
brew install cloudflared

# Linux
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb

# Windows
# Download from cloudflare.com
```

### Quick Tunnel (No Configuration)

```bash
# Start tunnel (generates random URL)
cloudflared tunnel --url http://localhost:8000

# Output:
# Your quick Tunnel has been created! Visit it at:
# https://random-words.trycloudflare.com
```

**Use this URL in your frontend configuration.**

### Named Tunnel (Persistent URL)

#### 1. Login to Cloudflare

```bash
cloudflared tunnel login
```

#### 2. Create Tunnel

```bash
cloudflared tunnel create sensor-collector
```

#### 3. Configure Tunnel

Create `~/.cloudflared/config.yml`:

```yaml
tunnel: sensor-collector
credentials-file: /home/sensorapp/.cloudflared/<TUNNEL-ID>.json

ingress:
  - hostname: sensors.yourdomain.com
    service: http://localhost:8000
  - service: http_status:404
```

#### 4. Create DNS Record

```bash
cloudflared tunnel route dns sensor-collector sensors.yourdomain.com
```

#### 5. Run Tunnel

```bash
cloudflared tunnel run sensor-collector
```

#### 6. Run as Service

Create `/etc/systemd/system/cloudflared.service`:

```ini
[Unit]
Description=Cloudflare Tunnel
After=network.target

[Service]
Type=simple
User=sensorapp
ExecStart=/usr/local/bin/cloudflared tunnel run sensor-collector
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable cloudflared
sudo systemctl start cloudflared
```

---

## Environment Configuration

### Production Environment Variables

```env
# External Endpoint (Required)
EXTERNAL_ENDPOINT_URL=https://oberlin.communityhub.cloud/api/data-hub/upload/csv
EXTERNAL_ENDPOINT_TOKEN=your-secure-token-here

# Polling Configuration
POLLING_INTERVAL=60  # seconds

# CORS Configuration
FRONTEND_URL=https://your-frontend-domain.com

# Server Configuration
HOST=0.0.0.0
PORT=8000

# Optional: Logging Level
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR

# Optional: Timeout Settings
REQUEST_TIMEOUT=10  # seconds
```

### Security Checklist

- [ ] Use strong, unique token for `EXTERNAL_ENDPOINT_TOKEN`
- [ ] Set restrictive `FRONTEND_URL` (not `*`)
- [ ] File permissions: `chmod 600 .env`
- [ ] Don't commit `.env` to git
- [ ] Use secrets manager in production (e.g., AWS Secrets Manager)
- [ ] Enable HTTPS (via reverse proxy or Cloudflare)
- [ ] Implement rate limiting
- [ ] Add API authentication

---

## Monitoring & Maintenance

### Health Checks

```bash
# Basic health check
curl http://localhost:8000/health

# Full API check
curl http://localhost:8000/api/sensors

# Check specific sensor status
curl http://localhost:8000/api/sensors/{sensor-id}/status
```

### Log Monitoring

```bash
# systemd logs
sudo journalctl -u sensor-collector -f

# Docker logs
docker-compose logs -f sensor-collector

# File logs (if configured)
tail -f /var/log/sensor-collector/app.log
```

### Monitoring Metrics

**Key Metrics to Monitor:**

1. **API Availability**
   - Endpoint: `GET /health`
   - Expected: 200 OK
   - Alert if: Down for > 5 minutes

2. **Sensor Status**
   - Check `last_active` timestamps
   - Alert if: No update for > 5 minutes

3. **Upload Success Rate**
   - Monitor sensor `last_error` fields
   - Alert if: Error rate > 10%

4. **System Resources**
   - CPU usage
   - Memory usage
   - Disk space
   - Network connectivity

### Setting Up Monitoring (Example: Uptime Kuma)

```bash
# Install Uptime Kuma
docker run -d --name uptime-kuma \
  -p 3001:3001 \
  -v uptime-kuma:/app/data \
  louislam/uptime-kuma:1

# Add monitors for:
# - http://localhost:8000/health (HTTP)
# - Each sensor status endpoint
```

### Backup & Recovery

**What to Backup:**

1. **Configuration**
   - `.env` file
   - Any custom config files

2. **Sensor Data** (if adding database)
   - Database files
   - Sensor registry

**Backup Script:**

```bash
#!/bin/bash
BACKUP_DIR="/home/sensorapp/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup
mkdir -p $BACKUP_DIR
cp /home/sensorapp/sensor-collector/backend/.env \
   $BACKUP_DIR/env_$DATE

# Keep only last 7 backups
find $BACKUP_DIR -name "env_*" -mtime +7 -delete
```

**Automate with cron:**

```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * /home/sensorapp/backup.sh
```

---

## Troubleshooting

### Common Issues

#### Service Won't Start

**Check logs:**
```bash
sudo journalctl -u sensor-collector -n 50
```

**Common causes:**
- Port 8000 already in use
- Missing dependencies
- Incorrect .env configuration
- File permission issues

**Solutions:**
```bash
# Check port usage
sudo lsof -i :8000

# Reinstall dependencies
pip install -r requirements.txt

# Check permissions
ls -la /home/sensorapp/sensor-collector/backend/.env
```

#### Cannot Connect to Sensors

**Test sensor connectivity:**
```bash
# Test Purple Air
curl http://192.168.1.100/json

# Test network
ping 192.168.1.100
```

**Common causes:**
- Sensor offline
- Wrong IP address
- Network firewall blocking
- Not on same network

**Solutions:**
- Verify sensor IP in sensor settings
- Check network configuration
- Ensure backend is on same network as sensors
- Check firewall rules

#### Upload Failures

**Test external endpoint:**
```bash
curl -X POST https://oberlin.communityhub.cloud/api/data-hub/upload/csv \
  -H "Authorization: Bearer your-token" \
  -F "file=@test.csv"
```

**Common causes:**
- Invalid token
- Network connectivity issues
- External endpoint down

**Solutions:**
- Verify `EXTERNAL_ENDPOINT_TOKEN`
- Check internet connectivity
- Contact external endpoint administrator

#### High Memory Usage

**Check memory:**
```bash
free -h
ps aux | grep uvicorn
```

**Solutions:**
- Reduce polling frequency
- Limit number of active sensors
- Add more RAM
- Implement database for sensor storage

### Debug Mode

Enable debug logging:

```python
# In main.py (temporary, for debugging)
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## Security Best Practices

### Network Security

1. **Firewall Configuration**
   ```bash
   # Allow only necessary ports
   sudo ufw default deny incoming
   sudo ufw default allow outgoing
   sudo ufw allow 8000/tcp
   sudo ufw allow 22/tcp
   sudo ufw enable
   ```

2. **Use Reverse Proxy**
   - Nginx or Apache
   - Handle SSL/TLS termination
   - Add rate limiting
   - Hide internal ports

### Application Security

1. **Environment Variables**
   - Never commit `.env`
   - Use secrets manager
   - Rotate tokens regularly

2. **Authentication**
   - Add API authentication
   - Use strong passwords
   - Implement OAuth2 if needed

3. **Input Validation**
   - Already implemented via Pydantic
   - Keep dependencies updated

4. **Rate Limiting**
   ```python
   # Add to main.py
   from slowapi import Limiter
   limiter = Limiter(key_func=get_remote_address)
   ```

### Updates & Patches

```bash
# Update application
cd /home/sensorapp/sensor-collector
git pull
source backend/venv/bin/activate
pip install --upgrade -r backend/requirements.txt
sudo systemctl restart sensor-collector

# Update system
sudo apt update && sudo apt upgrade -y
```

---

## Appendix

### Deployment Checklist

- [ ] Server provisioned and accessible
- [ ] Python 3.9+ installed
- [ ] Application deployed
- [ ] Virtual environment created
- [ ] Dependencies installed
- [ ] `.env` configured with production values
- [ ] `.env` permissions set to 600
- [ ] Service configured (systemd or Docker)
- [ ] Service enabled and started
- [ ] Health check passing
- [ ] Cloudflare tunnel configured (if needed)
- [ ] Sensors added and tested
- [ ] Monitoring configured
- [ ] Backups configured
- [ ] Documentation accessible to team

### Useful Commands

```bash
# Check service status
sudo systemctl status sensor-collector

# View recent logs
sudo journalctl -u sensor-collector -n 100

# Follow logs in real-time
sudo journalctl -u sensor-collector -f

# Restart service
sudo systemctl restart sensor-collector

# Test API
curl http://localhost:8000/health

# Check disk space
df -h

# Check memory
free -h

# Check CPU
top

# Network connectivity
ping google.com

# DNS lookup
nslookup oberlin.communityhub.cloud
```

---

**Last Updated:** January 2026

