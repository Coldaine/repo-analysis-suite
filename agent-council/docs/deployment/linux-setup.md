# Linux Deployment Guide

## Prerequisites

### System Requirements
- **OS**: Ubuntu 20.04+ / Debian 11+ / CentOS 8+ / Any modern Linux
- **RAM**: Minimum 1GB, recommended 2GB+
- **Storage**: 10GB free space
- **Python**: 3.8 or higher
- **Network**: Stable internet connection

### Required Software

```bash
# Update system
sudo apt update && sudo apt upgrade -y  # Debian/Ubuntu
sudo yum update -y                       # CentOS/RHEL

# Install Python and dependencies
sudo apt install python3 python3-pip python3-venv git -y  # Debian/Ubuntu
sudo yum install python3 python3-pip git -y               # CentOS/RHEL

# Install AI CLI tools
# Follow individual tool installation guides for:
# - Gemini CLI
# - Jules CLI
# - Qwen CLI
# - Goose CLI
```

## Installation Steps

### 1. Create Dedicated User (Optional but Recommended)

```bash
# Create user for Agent Council
sudo useradd -m -s /bin/bash agentcouncil
sudo passwd agentcouncil

# Add to sudo group if needed
sudo usermod -aG sudo agentcouncil  # Debian/Ubuntu
sudo usermod -aG wheel agentcouncil # CentOS/RHEL

# Switch to new user
su - agentcouncil
```

### 2. Clone Repository

```bash
# Navigate to home directory
cd ~

# Clone repository
git clone https://github.com/yourusername/agent-council.git
cd agent-council

# Set permissions
chmod +x scripts/*.py
```

### 3. Set Up Python Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env  # or vim .env
```

Add your API keys:
```env
# API Keys
GEMINI_API_KEY=your_gemini_key
JULES_API_KEY=your_jules_key
QWEN_API_KEY=your_qwen_key
OPENAI_API_KEY=your_openai_key

# Paths
AGENT_COUNCIL_HOME=/home/agentcouncil/agent-council
AGENT_COUNCIL_DATA=/home/agentcouncil/agent-council/data
AGENT_COUNCIL_LOGS=/home/agentcouncil/agent-council/data/logs

# Configuration
AGENT_COUNCIL_ENV=production
AGENT_COUNCIL_DEBUG=false
```

### 5. Initialize System

```bash
# Run setup script
python scripts/setup.py

# Verify setup
python scripts/status.py
```

## Systemd Service Setup

### 1. Create Service File

```bash
# Create service file
sudo nano /etc/systemd/system/agent-council.service
```

Add the following content:

```ini
[Unit]
Description=Agent Council AI Orchestration System
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=agentcouncil
Group=agentcouncil
WorkingDirectory=/home/agentcouncil/agent-council
Environment="PATH=/home/agentcouncil/agent-council/venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONPATH=/home/agentcouncil/agent-council"
ExecStart=/home/agentcouncil/agent-council/venv/bin/python /home/agentcouncil/agent-council/scripts/start.py
Restart=always
RestartSec=10
StandardOutput=append:/home/agentcouncil/agent-council/data/logs/systemd.log
StandardError=append:/home/agentcouncil/agent-council/data/logs/systemd-error.log

# Resource limits
MemoryLimit=1G
CPUQuota=80%

# Security
PrivateTmp=true
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
```

### 2. Enable and Start Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable agent-council.service

# Start service
sudo systemctl start agent-council.service

# Check status
sudo systemctl status agent-council.service

# View logs
journalctl -u agent-council.service -f
```

### 3. Service Management Commands

```bash
# Stop service
sudo systemctl stop agent-council.service

# Restart service
sudo systemctl restart agent-council.service

# Disable service (don't start on boot)
sudo systemctl disable agent-council.service

# View full logs
journalctl -u agent-council.service --since "1 hour ago"
```

## Alternative: Supervisor Setup

### Install Supervisor

```bash
# Debian/Ubuntu
sudo apt install supervisor -y

# CentOS/RHEL
sudo yum install supervisor -y
```

### Configure Supervisor

```bash
# Create configuration
sudo nano /etc/supervisor/conf.d/agent-council.conf
```

Add configuration:

```ini
[program:agent-council]
command=/home/agentcouncil/agent-council/venv/bin/python /home/agentcouncil/agent-council/scripts/start.py
directory=/home/agentcouncil/agent-council
user=agentcouncil
autostart=true
autorestart=true
startsecs=10
stopwaitsecs=600
stdout_logfile=/home/agentcouncil/agent-council/data/logs/supervisor.log
stderr_logfile=/home/agentcouncil/agent-council/data/logs/supervisor-error.log
environment=PATH="/home/agentcouncil/agent-council/venv/bin:%(ENV_PATH)s",PYTHONPATH="/home/agentcouncil/agent-council"
```

### Start with Supervisor

```bash
# Reload configuration
sudo supervisorctl reread
sudo supervisorctl update

# Start process
sudo supervisorctl start agent-council

# Check status
sudo supervisorctl status agent-council
```

## Cron Alternative (Simple Timer)

For simpler deployments, use cron:

```bash
# Edit crontab
crontab -e

# Add entry to run every minute (checks internal timers)
* * * * * cd /home/agentcouncil/agent-council && ./venv/bin/python scripts/run_cycle.py >> data/logs/cron.log 2>&1

# Or run continuously with restart
@reboot cd /home/agentcouncil/agent-council && while true; do ./venv/bin/python scripts/start.py; sleep 10; done &
```

## Monitoring

### System Status

```bash
# Check if running
ps aux | grep agent-council

# Check service status
sudo systemctl status agent-council

# Monitor resource usage
htop  # Interactive process viewer
top -p $(pgrep -f agent-council)

# Check logs
tail -f ~/agent-council/data/logs/orchestrator/*.log

# Watch all agent logs
tail -f ~/agent-council/data/logs/*/*.log
```

### Monitoring Script

Create `monitor.sh`:

```bash
#!/bin/bash

# Monitor Agent Council
while true; do
    clear
    echo "=== Agent Council Status ==="
    echo "Time: $(date '+%Y-%m-%d %H:%M:%S')"
    echo

    # Check process
    if pgrep -f "agent-council" > /dev/null; then
        echo -e "Status: \033[32mRUNNING\033[0m"

        # Get process info
        ps aux | grep agent-council | grep -v grep | head -1

        # Memory usage
        echo "Memory: $(ps aux | grep agent-council | grep -v grep | awk '{print $6/1024 " MB"}')"
    else
        echo -e "Status: \033[31mSTOPPED\033[0m"
    fi

    echo
    echo "=== Recent Activity ==="
    tail -n 10 ~/agent-council/data/logs/orchestrator/*.log

    sleep 5
done
```

Make executable:
```bash
chmod +x monitor.sh
./monitor.sh
```

## Log Management

### Log Rotation

Create `/etc/logrotate.d/agent-council`:

```bash
sudo nano /etc/logrotate.d/agent-council
```

Add configuration:

```
/home/agentcouncil/agent-council/data/logs/*/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 agentcouncil agentcouncil
    sharedscripts
    postrotate
        systemctl reload agent-council >/dev/null 2>&1 || true
    endscript
}
```

### Log Analysis

```bash
# Search for errors
grep -r ERROR ~/agent-council/data/logs/

# Count agent executions
grep "Agent executed" ~/agent-council/data/logs/orchestrator/*.log | wc -l

# View JSON logs with jq
cat ~/agent-council/data/logs/gemini/*.jsonl | jq '.'

# Get execution times
grep "duration" ~/agent-council/data/logs/*/*.jsonl | jq '.duration'
```

## Performance Optimization

### System Tuning

```bash
# Increase file descriptor limits
echo "* soft nofile 65536" | sudo tee -a /etc/security/limits.conf
echo "* hard nofile 65536" | sudo tee -a /etc/security/limits.conf

# Optimize Python
export PYTHONOPTIMIZE=1
export PYTHONDONTWRITEBYTECODE=1

# CPU governor for performance
sudo cpupower frequency-set -g performance
```

### Resource Monitoring

```bash
# Install monitoring tools
sudo apt install sysstat iotop nethogs -y

# Monitor disk I/O
iotop -o

# Monitor network
nethogs

# System activity
sar -u 1 10  # CPU usage
sar -r 1 10  # Memory usage
```

## Backup and Recovery

### Automated Backup Script

Create `backup.sh`:

```bash
#!/bin/bash

# Backup configuration
BACKUP_DIR="/home/agentcouncil/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/agent-council-backup-$TIMESTAMP.tar.gz"

# Create backup directory
mkdir -p $BACKUP_DIR

# Create backup
cd /home/agentcouncil
tar -czf $BACKUP_FILE \
    --exclude='agent-council/venv' \
    --exclude='agent-council/data/logs' \
    agent-council/

# Keep only last 7 backups
ls -t $BACKUP_DIR/agent-council-backup-*.tar.gz | tail -n +8 | xargs -r rm

echo "Backup created: $BACKUP_FILE"
```

### Cron Backup

```bash
# Add to crontab
0 3 * * * /home/agentcouncil/backup.sh >> /home/agentcouncil/backup.log 2>&1
```

### Restore Process

```bash
# Stop service
sudo systemctl stop agent-council

# Extract backup
tar -xzf /home/agentcouncil/backups/agent-council-backup-20240101_030000.tar.gz

# Restore virtual environment
cd agent-council
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start service
sudo systemctl start agent-council
```

## Security Hardening

### File Permissions

```bash
# Secure sensitive files
chmod 600 ~/.agent-council/.env
chmod 700 ~/agent-council/data/state

# Set ownership
chown -R agentcouncil:agentcouncil ~/agent-council
```

### Firewall Configuration

```bash
# If using web interface (future feature)
sudo ufw allow 8080/tcp

# Enable firewall
sudo ufw enable
```

### SELinux (CentOS/RHEL)

```bash
# Set context
sudo semanage fcontext -a -t bin_t "/home/agentcouncil/agent-council/scripts(/.*)?"
sudo restorecon -Rv /home/agentcouncil/agent-council/
```

## Troubleshooting

### Common Issues

#### 1. Permission Denied

```bash
# Fix permissions
chmod +x scripts/*.py
chmod -R 755 ~/agent-council
chmod 600 .env
```

#### 2. Module Not Found

```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt

# Check Python path
echo $PYTHONPATH
export PYTHONPATH=/home/agentcouncil/agent-council:$PYTHONPATH
```

#### 3. Service Won't Start

```bash
# Check service logs
journalctl -u agent-council -n 50

# Run manually to see errors
cd ~/agent-council
./venv/bin/python scripts/start.py --debug

# Check systemd status
systemctl status agent-council.service
```

#### 4. High Memory Usage

```bash
# Check memory
free -h

# Find memory leaks
valgrind --tool=memcheck python scripts/start.py

# Limit memory in systemd
# Edit /etc/systemd/system/agent-council.service
# Add: MemoryLimit=512M
```

### Debug Mode

```bash
# Enable debug logging
export AGENT_COUNCIL_DEBUG=true
python scripts/start.py --debug

# Trace execution
python -m trace -t scripts/start.py

# Profile performance
python -m cProfile scripts/start.py
```

## Docker Deployment

### Dockerfile

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app
ENV AGENT_COUNCIL_HOME=/app

CMD ["python", "scripts/start.py"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  agent-council:
    build: .
    restart: unless-stopped
    env_file: .env
    volumes:
      - ./data:/app/data
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
```

### Run with Docker

```bash
# Build image
docker build -t agent-council .

# Run container
docker run -d \
    --name agent-council \
    --restart unless-stopped \
    --env-file .env \
    -v $(pwd)/data:/app/data \
    agent-council

# View logs
docker logs -f agent-council
```

## Cloud Deployment

### AWS EC2

```bash
# Launch t2.micro instance with Ubuntu
# SSH into instance
ssh -i key.pem ubuntu@ec2-instance

# Follow standard Linux setup
# Use systemd for service management
```

### DigitalOcean

```bash
# Create $5 droplet
# SSH into droplet
ssh root@droplet-ip

# Follow setup instructions
# Configure firewall
ufw allow 22
ufw enable
```

## Next Steps

1. **Test the installation**:
   ```bash
   python scripts/test_agents.py
   ```

2. **Configure monitoring** with Prometheus/Grafana

3. **Set up alerts** with email/Slack notifications

4. **Implement log aggregation** with ELK stack

5. **Configure CI/CD** for automated updates

For Windows deployment, see [windows-setup.md](windows-setup.md).