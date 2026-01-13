# Database Operations - Quick Start Guide

Get up and running with the observability control plane database operations in 5 minutes.

## Prerequisites

- Python 3.8+
- Docker and Docker Compose (for Neo4j and PostgreSQL)
- Git Bash or Linux terminal

## Step 1: Install Dependencies

```bash
cd E:\_projectsGithub\observability-implementation-package
pip install -r requirements.txt
```

Expected output:
```
Successfully installed memori-0.3.1 httpx-0.27.0 flask-3.0.0 flask-htmx-0.3.0
py2neo-2021.2.0 psycopg2-binary-2.9.0 dagger-io-0.12.0 psutil-5.9.0 docker-7.0.0
```

## Step 2: Start Databases

### Option A: Using Docker Compose (Recommended)

```bash
# Start Neo4j and PostgreSQL
docker-compose up -d neo4j postgres

# Verify they're running
docker ps | grep -E 'neo4j|postgres'
```

### Option B: Manual Docker Commands

```bash
# Start Neo4j
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/your-password \
  neo4j:latest

# Start PostgreSQL
docker run -d \
  --name postgres \
  -p 5432:5432 \
  -e POSTGRES_USER=memori \
  -e POSTGRES_PASSWORD=change-me \
  -e POSTGRES_DB=memori \
  postgres:15
```

## Step 3: Set Environment Variables

```bash
# Neo4j credentials
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_PASSWORD="your-password"  # Change to match your setup

# PostgreSQL/Memori credentials
export DATABASE_URL="postgresql://memori:change-me@localhost:5432/memori"

# Optional: Set log level
export OBS_AGENT_LOG_LEVEL="INFO"
```

**Windows (PowerShell):**
```powershell
$env:NEO4J_URI = "bolt://localhost:7687"
$env:NEO4J_PASSWORD = "your-password"
$env:DATABASE_URL = "postgresql://memori:change-me@localhost:5432/memori"
```

## Step 4: Initialize Neo4j Database

```bash
cd scripts
python init_neo4j.py
```

Expected output:
```
2025-01-23 12:00:00 - __main__ - INFO - Connected to Neo4j at bolt://localhost:7687
2025-01-23 12:00:00 - __main__ - INFO - Creating indexes...
2025-01-23 12:00:00 - __main__ - INFO - ✓ Executed: CREATE INDEX fix_timestamp...
2025-01-23 12:00:00 - __main__ - INFO - ✓ Executed: CREATE INDEX fix_issue...
...
2025-01-23 12:00:00 - __main__ - INFO - Database statistics:
2025-01-23 12:00:00 - __main__ - INFO -   Total nodes: 0
2025-01-23 12:00:00 - __main__ - INFO -   Fix nodes: 0
2025-01-23 12:00:00 - __main__ - INFO -   Agent nodes: 0
2025-01-23 12:00:00 - __main__ - INFO - ✓ Neo4j initialization complete!
```

## Step 5: Run Tests

```bash
python test_database.py
```

Expected output:
```
============================================================
DATABASE OPERATIONS TEST SUITE
============================================================
Started at: 2025-01-23T12:00:00

Environment Check:
  NEO4J_URI: bolt://localhost:7687
  NEO4J_PASSWORD: SET
  DATABASE_URL: postgresql://memori:change-me@localhost:5432/memori

============================================================
Testing DatabaseManager Class
============================================================

1. Testing get_database_stats...
Database Stats:
  neo4j_connected: True
  memori_available: True
  total_nodes: 1
  total_fixes: 1
  total_agents: 1

...

ALL TESTS COMPLETED
```

## Step 6: Start the Dashboard

```bash
cd ../dashboard
python app.py
```

Expected output:
```
 * Serving Flask app 'app'
 * Debug mode: off
WARNING: This is a development server. Do not use it in a production deployment.
 * Running on http://0.0.0.0:5555
```

## Step 7: Verify Everything Works

Open another terminal and test the endpoints:

```bash
# Health check
curl http://localhost:5555/health

# Get all agents
curl http://localhost:5555/api/agents

# Get recent fixes
curl http://localhost:5555/api/fixes?limit=5

# Register a test agent
curl -X POST http://localhost:5555/api/register-agent \
  -H "Content-Type: application/json" \
  -d '{"name": "test-agent-1", "server": "localhost"}'

# Check it was registered
curl http://localhost:5555/api/agents
```

## Step 8: Use in Your Code

### Example 1: Store a Fix

```python
from scripts.agent_memory import remember

# Store a fix
remember(
    "issue:database-connection",
    "Increased connection pool size to 50",
    metadata={"success": True, "server": "prod-1"}
)
```

### Example 2: Query Fixes

```python
from scripts.agent_memory import get_recent_fixes, find_similar_issues

# Get recent fixes
fixes = get_recent_fixes(limit=10)
for fix in fixes:
    print(f"{fix['issue']}: {fix['solution']}")

# Find similar issues
similar = find_similar_issues("connection", limit=5)
for issue in similar:
    print(f"{issue['issue']} occurred {issue['occurrence_count']} times")
```

### Example 3: Agent Registration

```python
from scripts.agent_memory import register_agent, get_all_agents

# Register agent
success = register_agent("obs-agent-1", "prod-server-1")
print(f"Registration: {'SUCCESS' if success else 'FAILED'}")

# List all agents
agents = get_all_agents()
for agent in agents:
    print(f"Agent: {agent['name']} on {agent['server']} - {agent['status']}")
```

## Common Issues and Solutions

### Issue: "Neo4j connection failed"

**Solution:**
```bash
# Check Neo4j is running
docker ps | grep neo4j

# Check logs
docker logs neo4j

# Restart Neo4j
docker restart neo4j

# Wait for startup (check logs)
docker logs -f neo4j
# Look for: "Remote interface available at http://localhost:7474/"
```

### Issue: "Memori initialization failed"

**Solution:**
```bash
# Check PostgreSQL is running
docker ps | grep postgres

# Test connection
psql "postgresql://memori:change-me@localhost:5432/memori"

# If connection fails, check password and recreate
docker rm -f postgres
docker run -d --name postgres -p 5432:5432 \
  -e POSTGRES_USER=memori \
  -e POSTGRES_PASSWORD=change-me \
  -e POSTGRES_DB=memori \
  postgres:15
```

### Issue: "ImportError: No module named 'memori'"

**Solution:**
```bash
# Install memori
pip install memori>=0.3.1

# Verify installation
python -c "import memori; print('Memori OK')"
```

### Issue: "py2neo connection error"

**Solution:**
```bash
# Install py2neo
pip install py2neo>=2021.2.0

# Test connection
python -c "from py2neo import Graph; g = Graph('bolt://localhost:7687', auth=('neo4j', 'your-password')); print('Connected')"
```

## Next Steps

1. **Explore the API**: Visit http://localhost:5555/api/state
2. **Read the docs**: Check `docs/DATABASE_OPERATIONS.md`
3. **Review architecture**: See `docs/ARCHITECTURE.md`
4. **Integrate with agents**: Update `scripts/obs_agent.py` to use the new functions
5. **Monitor health**: Set up `/health` endpoint monitoring

## Development Workflow

### Making Changes

1. **Edit code** in `scripts/database_helpers.py` or `scripts/agent_memory.py`
2. **Run tests** with `python scripts/test_database.py`
3. **Restart dashboard** (Ctrl+C, then `python dashboard/app.py`)
4. **Test endpoint** with curl or browser

### Adding New Features

1. **Add function** to `DatabaseManager` class in `database_helpers.py`
2. **Add wrapper** in `agent_memory.py` if needed
3. **Add endpoint** in `dashboard/app.py` if needed
4. **Add test** in `test_database.py`
5. **Update docs** in `DATABASE_OPERATIONS.md`

### Debugging

```bash
# Enable debug logging
export OBS_AGENT_LOG_LEVEL="DEBUG"

# Run with verbose output
python test_database.py

# Check Neo4j browser
open http://localhost:7474
# Run Cypher query: MATCH (n) RETURN n LIMIT 25
```

## Useful Commands

```bash
# Check all environment variables
env | grep -E 'NEO4J|DATABASE'

# View Neo4j data
docker exec -it neo4j cypher-shell -u neo4j -p your-password
# Then: MATCH (n) RETURN n LIMIT 10;

# View PostgreSQL data
docker exec -it postgres psql -U memori -d memori
# Then: \dt (list tables)

# Clear all data (WARNING: Destructive!)
docker exec -it neo4j cypher-shell -u neo4j -p your-password
# Then: MATCH (n) DETACH DELETE n;

# Restart everything
docker-compose restart neo4j postgres
```

## Production Checklist

Before deploying to production:

- [ ] Change all default passwords
- [ ] Set strong NEO4J_PASSWORD
- [ ] Set strong PostgreSQL password
- [ ] Enable Neo4j authentication
- [ ] Configure SSL/TLS for Neo4j (bolt+s://)
- [ ] Configure PostgreSQL SSL
- [ ] Set up database backups
- [ ] Configure log rotation
- [ ] Set up monitoring/alerting
- [ ] Review and adjust connection pool sizes
- [ ] Enable Neo4j metrics
- [ ] Configure firewall rules

## Getting Help

- **Documentation**: See `docs/DATABASE_OPERATIONS.md`
- **Architecture**: See `docs/ARCHITECTURE.md`
- **Implementation**: See `docs/IMPLEMENTATION_SUMMARY.md`
- **Issues**: Check logs in `docker logs <container>`
- **Neo4j Browser**: http://localhost:7474
- **Dashboard**: http://localhost:5555

## Quick Reference

```bash
# Start services
docker-compose up -d neo4j postgres

# Initialize database
python scripts/init_neo4j.py

# Run tests
python scripts/test_database.py

# Start dashboard
python dashboard/app.py

# Check health
curl http://localhost:5555/health

# View agents
curl http://localhost:5555/api/agents

# View fixes
curl http://localhost:5555/api/fixes
```

That's it! You're now ready to use the observability control plane database operations.
