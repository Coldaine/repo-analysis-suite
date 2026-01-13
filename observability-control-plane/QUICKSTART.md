# Quickstart Guide

Get the observability control plane running in **5 minutes**.

---

## Step 1: Clone Repository

```bash
git clone https://github.com/yourorg/observability-control
cd observability-control
```

---

## Step 2: Create `.env` File

```bash
cp .env.example .env
```

**Edit `.env` and set these 3 required variables:**

```bash
MEMORI_DB_PASSWORD=change-this-to-strong-password
NEO4J_PASSWORD=change-this-to-another-strong-password
GOOSEAI_API_KEY=your-goose-ai-api-key-from-https://goose.ai
```

**Tip:** Generate strong passwords using:
```bash
# Linux/macOS
openssl rand -base64 32

# Windows PowerShell
[System.Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Minimum 0 -Maximum 256 }))
```

---

## Step 3: Start Services

```bash
docker compose up -d
```

**Wait for services to become healthy** (~30 seconds):

```bash
docker compose ps
# All services should show "Up" and "healthy"
```

**Expected output:**
```
NAME                  STATUS
mcp                   Up (healthy)
postgres              Up (healthy)
memori                Up
neo4j                 Up (healthy)
dashboard             Up
```

---

## Step 4: Open Dashboard

**Automatic (recommended):**
```bash
python scripts/manage.py dashboard
```

**Manual:**
Open http://localhost:5555 in your browser

---

## Step 5: Verify It Works

You should see:
- ✅ Dashboard loads successfully
- ✅ Disk usage displayed
- ✅ Last check timestamp (may be empty initially)
- ✅ System status indicators

**Screenshot of expected dashboard:**
```
┌────────────────────────────────────────┐
│  Observability Control Plane Dashboard │
├────────────────────────────────────────┤
│  Disk Usage: 45% (128 GB free)         │
│  Last Check: 2025-01-23 10:30:45       │
│  Status: Healthy                       │
│                                        │
│  Recent Fixes: (empty)                 │
└────────────────────────────────────────┘
```

---

## Next Steps

### Run Your First Health Check

```bash
python scripts/manage.py health
```

This will:
1. Run a Dagger-based health check
2. Collect system metrics
3. Report status to the dashboard
4. Create initial memory entries

### Deploy to an Application

Copy the telemetry template to one of your services:

```bash
# Example: Django app
cp -r app-template ~/my-django-app/observability

# Configure the app's .env
cd ~/my-django-app
echo "SERVICE_NAME=my-django-app" >> .env
echo "OBS_CONTROL_URL=http://localhost:5555" >> .env

# Run telemetry check
python observability/scripts/telemetry_agent.py
```

### Explore the Control Plane

**View prompts:**
```bash
cat prompts/control-plane.md
```

**Check agent memory:**
```bash
docker compose logs memori
```

**Query Neo4j graph:**
1. Open http://localhost:7474
2. Login with username `neo4j` and your `NEO4J_PASSWORD`
3. Run: `MATCH (n) RETURN n LIMIT 10`

**Read full documentation:**
See [README.md](README.md) for complete details.

---

## Common First-Time Issues

### Issue: "Services won't start"

**Solution 1 - Check .env file:**
```bash
cat .env
# Verify MEMORI_DB_PASSWORD and NEO4J_PASSWORD are set
```

**Solution 2 - Check Docker resources:**
```bash
docker info
# Ensure sufficient memory (4GB+) and disk space (10GB+)
```

**Solution 3 - View detailed logs:**
```bash
docker compose logs --tail=50
```

---

### Issue: Dashboard shows "ERROR: Unable to fetch recent fixes"

**This is normal on first boot!** Memori has no data yet.

**To populate data:**
```bash
# Run a health check to generate some data
python scripts/manage.py health
```

---

### Issue: "Dagger command not found"

**Option 1 - Install Dagger (recommended):**
```bash
# macOS
brew install dagger/tap/dagger

# Linux
curl -L https://dl.dagger.io/dagger/install.sh | sh

# Windows
# Download from https://dagger.io/install
```

**Option 2 - Skip health checks:**
Health checks are optional. You can still use the dashboard and manual agent operations without Dagger.

---

### Issue: Port 5555 already in use

**Change dashboard port:**

Edit `.env`:
```bash
DASHBOARD_PORT=8080  # or any available port
```

Restart services:
```bash
docker compose down
docker compose up -d
```

---

## Platform-Specific Notes

### Windows

**Memory Sync:**
Memory sync uses `rsync` which isn't available by default on Windows. Set this in `.env`:
```bash
MEMORY_SYNC_ENABLED=false
```

**Git Bash:**
Run all commands from Git Bash (not CMD or PowerShell) for best compatibility.

### macOS

**Docker Desktop:**
Ensure Docker Desktop is running before starting services.

**Permissions:**
If you get permission errors, add execute permissions:
```bash
chmod +x scripts/*.py
chmod +x memory/*.sh
```

### Linux

**Docker without sudo:**
Add your user to the docker group:
```bash
sudo usermod -aG docker $USER
newgrp docker
```

---

## Quick Reference

### Essential Commands

```bash
# Show all management commands
python scripts/manage.py help

# Open dashboard
python scripts/manage.py dashboard

# Run health check
python scripts/manage.py health

# View service status
docker compose ps

# View logs
docker compose logs -f dashboard

# Stop all services
docker compose down

# Reset everything (DESTROYS DATA)
docker compose down -v
docker compose up -d
```

### Service URLs

| Service | URL | Purpose |
|---------|-----|---------|
| Dashboard | http://localhost:5555 | Main UI |
| Neo4j Browser | http://localhost:7474 | Graph explorer |
| MCP Server | http://localhost:8433 | Tool gateway |

### Data Directories

| Directory | Purpose | Safe to delete? |
|-----------|---------|-----------------|
| `memory/` | Agent memory files | ⚠️ Loses history |
| `pg-data/` | Postgres database | ⚠️ Loses Memori data |
| `neo4j-data/` | Neo4j graph | ⚠️ Loses fix history |

**Backup before deleting:**
```bash
python scripts/manage.py backup
```

---

## Getting Help

**Check logs first:**
```bash
docker compose logs
```

**Verify configuration:**
```bash
# Check .env
cat .env

# Check Docker Compose config
docker compose config
```

**Still stuck?**
- Read [README.md](README.md) for detailed documentation
- Check [Troubleshooting](README.md#troubleshooting) section
- Open an issue: https://github.com/yourorg/observability-control/issues

---

## Success Checklist

- [ ] All services show "Up" in `docker compose ps`
- [ ] Dashboard loads at http://localhost:5555
- [ ] No error messages in `docker compose logs`
- [ ] Disk usage displayed in dashboard
- [ ] `.env` file configured with strong passwords
- [ ] Health check runs successfully (if Dagger installed)

**Congratulations!** Your observability control plane is ready. See [README.md](README.md) for advanced usage.
