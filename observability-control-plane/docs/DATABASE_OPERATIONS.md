# Database Operations Guide

This document describes the database operations for the observability control plane, including Neo4j READ/WRITE operations and Memori configuration.

## Overview

The observability control plane uses two database systems:

1. **Neo4j** - Graph database for storing agents, fixes, and relationships
2. **Memori** - Vector database with PostgreSQL backend for semantic search

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Application Layer                       │
├─────────────────────────────────────────────────────────┤
│  dashboard/app.py          scripts/obs_agent.py         │
│         │                           │                    │
│         └───────────┬───────────────┘                    │
│                     │                                    │
│         ┌───────────▼──────────────┐                     │
│         │  scripts/agent_memory.py │  (High-level API)  │
│         └───────────┬──────────────┘                     │
│                     │                                    │
│         ┌───────────▼────────────────┐                   │
│         │ scripts/database_helpers.py│ (Database Manager)│
│         └───────────┬────────────────┘                   │
│                     │                                    │
│         ┌───────────┴───────────┐                        │
│         │                       │                        │
│    ┌────▼─────┐          ┌─────▼──────┐                 │
│    │  Neo4j   │          │   Memori   │                  │
│    │  Graph   │          │ PostgreSQL │                  │
│    └──────────┘          └────────────┘                  │
└─────────────────────────────────────────────────────────┘
```

## Files Created

### 1. `scripts/database_helpers.py`

Core database management class with comprehensive Neo4j READ/WRITE operations and Memori integration.

**Key Features:**
- `DatabaseManager` class for unified database access
- Neo4j connection management with error handling
- Memori initialization with PostgreSQL
- READ operations: get_recent_fixes, find_similar_issues, get_all_agents, etc.
- WRITE operations: remember_fix, register_agent
- Database statistics and health checks

**Usage:**
```python
from scripts.database_helpers import db_manager

# Get recent fixes
fixes = db_manager.get_recent_fixes(limit=20)

# Register an agent
db_manager.register_agent("agent-1", "server-1")

# Find similar issues
similar = db_manager.find_similar_issues("connection", limit=5)

# Get database stats
stats = db_manager.get_database_stats()
```

### 2. `scripts/agent_memory.py` (Enhanced)

Enhanced memory operations that integrate both Memori and Neo4j. Maintains backward compatibility with existing code.

**Key Features:**
- Enhanced `recall()` - searches both Memori and Neo4j
- Enhanced `remember()` - stores in both databases
- Helper functions: `get_recent_fixes()`, `get_all_agents()`, `register_agent()`, `find_similar_issues()`
- Graceful fallback when databases are unavailable

**Usage:**
```python
from scripts.agent_memory import recall, remember, get_all_agents

# Store a fix
remember("issue:connection-timeout", "Increased timeout to 30s",
         metadata={"success": True})

# Recall similar fixes
fixes = recall("issue:connection", limit=10)

# Get all registered agents
agents = get_all_agents()
```

### 3. `dashboard/app.py` (Updated)

Updated dashboard to query Neo4j for agents and display recent fixes.

**Changes:**
- `/api/state` now queries Neo4j for agents and fixes
- `/api/agents` endpoint for listing all agents
- `/api/register-agent` endpoint for agent registration
- `/api/fixes` endpoint with pagination
- `/health` endpoint with database connectivity check
- Proper error handling and logging

### 4. `scripts/init_neo4j.py`

Neo4j initialization script that creates indexes and constraints for better performance.

**Features:**
- Creates indexes on Fix and Agent nodes
- Creates unique constraint on agent names
- Verifies database setup
- Reports database statistics

**Usage:**
```bash
# Set environment variables first
export NEO4J_PASSWORD="your-password"
export NEO4J_URI="bolt://neo4j:7687"

# Run initialization
python scripts/init_neo4j.py
```

### 5. `scripts/test_database.py`

Comprehensive test suite for database operations.

**Test Coverage:**
- DatabaseManager class functionality
- agent_memory module functions
- Error handling
- Database connectivity
- Neo4j queries
- Memori operations

**Usage:**
```bash
# Set environment variables
export NEO4J_PASSWORD="your-password"
export DATABASE_URL="postgresql://memori:password@postgres:5432/memori"

# Run tests
python scripts/test_database.py
```

## Database Schema

### Neo4j Graph Schema

#### Fix Node
```cypher
(:Fix {
  issue: String,         # Issue description
  solution: String,      # Solution applied
  success: Boolean,      # Whether fix was successful
  ts: Integer           # Timestamp (milliseconds since epoch)
})
```

#### Agent Node
```cypher
(:Agent {
  name: String,          # Unique agent name
  server: String,        # Server hostname
  status: String,        # 'active', 'inactive', etc.
  last_seen: Integer    # Last heartbeat timestamp
})
```

### Indexes

- `fix_timestamp` - Index on Fix.ts for time-based queries
- `fix_issue` - Index on Fix.issue for searching issues
- `fix_success` - Index on Fix.success for filtering by success
- `agent_name` - Unique index on Agent.name
- `agent_status` - Index on Agent.status
- `agent_last_seen` - Index on Agent.last_seen

## Environment Variables

### Required

```bash
# Neo4j Configuration
NEO4J_URI="bolt://neo4j:7687"
NEO4J_PASSWORD="your-neo4j-password"

# PostgreSQL/Memori Configuration
DATABASE_URL="postgresql://memori:password@postgres:5432/memori"
```

### Optional

```bash
# Logging
OBS_AGENT_LOG_LEVEL="INFO"  # DEBUG, INFO, WARNING, ERROR
```

## API Endpoints

### GET `/api/state`
Returns current control plane state including agents and recent fixes.

**Response:**
```json
{
  "agents": [
    {
      "name": "agent-1",
      "status": "active",
      "server": "server-1",
      "last_seen": "2025-01-23T12:00:00Z"
    }
  ],
  "recent_fixes": [
    "connection-timeout -> Increased timeout to 30s (2025-01-23 12:00:00)"
  ],
  "disk_usage": "...",
  "last_check": "2025-01-23T12:00:00Z"
}
```

### GET `/api/agents`
Returns all registered agents.

**Response:**
```json
{
  "agents": [
    {
      "name": "agent-1",
      "status": "active",
      "server": "server-1",
      "last_seen": "2025-01-23T12:00:00Z"
    }
  ]
}
```

### POST `/api/register-agent`
Register a new agent or update existing one.

**Request:**
```json
{
  "name": "agent-1",
  "server": "server-1"
}
```

**Response:**
```json
{
  "status": "registered",
  "name": "agent-1",
  "server": "server-1"
}
```

### GET `/api/fixes?limit=20`
Get recent fixes with pagination.

**Response:**
```json
{
  "fixes": [
    {
      "issue": "connection-timeout",
      "solution": "Increased timeout to 30s",
      "timestamp": 1706011200000,
      "success": true
    }
  ],
  "count": 1,
  "limit": 20
}
```

### GET `/health`
Health check endpoint with database connectivity check.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-23T12:00:00Z",
  "checks": {
    "disk": {"status": "ok", "usage_percent": 45.2},
    "memory": {"status": "ok", "usage_percent": 67.8},
    "database": {"status": "ok", "connected": true}
  }
}
```

## Common Operations

### Storing a Fix

```python
from scripts.agent_memory import remember

remember(
    "issue:connection-timeout",
    "Increased timeout to 30s and added retry logic",
    metadata={"success": True, "server": "prod-1"}
)
```

### Querying Similar Issues

```python
from scripts.agent_memory import find_similar_issues

# Find all connection-related issues
similar = find_similar_issues("connection", limit=10)
for issue in similar:
    print(f"{issue['issue']}: {issue['solution']}")
    print(f"  Occurred {issue['occurrence_count']} times")
```

### Registering an Agent

```python
from scripts.agent_memory import register_agent

# Register agent with server info
success = register_agent("obs-agent-1", "prod-server-1")
```

### Getting Agent Health

```python
from scripts.agent_memory import get_all_agents
from datetime import datetime, timedelta

agents = get_all_agents()
now = datetime.now().timestamp() * 1000

for agent in agents:
    last_seen = agent.get('last_seen', 0)
    age = (now - last_seen) / 1000 / 60  # minutes

    if age > 60:
        print(f"⚠ Agent {agent['name']} hasn't reported in {age:.0f} minutes")
    else:
        print(f"✓ Agent {agent['name']} is healthy")
```

## Error Handling

All database operations handle connection failures gracefully:

1. **Neo4j unavailable**: Operations return empty lists/False, log warnings
2. **Memori unavailable**: Falls back to Neo4j only, logs warnings
3. **Both unavailable**: Returns empty data, doesn't crash application

Example:
```python
from scripts.database_helpers import db_manager

# Check database availability
stats = db_manager.get_database_stats()
if not stats['neo4j_connected']:
    print("⚠ Neo4j is not connected")
if not stats['memori_available']:
    print("⚠ Memori is not available")

# Operations still work, just return empty results
fixes = db_manager.get_recent_fixes()  # Returns [] if Neo4j down
```

## Troubleshooting

### Neo4j Connection Issues

```bash
# Check Neo4j is running
docker ps | grep neo4j

# Test connection
python -c "from py2neo import Graph; Graph('bolt://neo4j:7687', auth=('neo4j', 'password'))"

# Check logs
docker logs neo4j
```

### Memori/PostgreSQL Issues

```bash
# Check PostgreSQL is running
docker ps | grep postgres

# Test connection
psql "postgresql://memori:password@localhost:5432/memori"

# Check Memori configuration
python -c "import memori; print(memori.__version__)"
```

### Running Tests

```bash
# Run full test suite
python scripts/test_database.py

# Run with debug logging
OBS_AGENT_LOG_LEVEL=DEBUG python scripts/test_database.py
```

## Performance Considerations

1. **Indexes**: All key fields are indexed for fast queries
2. **Connection Pooling**: py2neo handles connection pooling automatically
3. **Batch Operations**: For bulk inserts, consider using transactions
4. **Query Limits**: Always use LIMIT in queries to prevent large result sets

## Future Enhancements

Potential improvements to consider:

1. **Pagination**: Add offset support to all query functions
2. **Relationships**: Add relationships between fixes and agents in Neo4j
3. **Caching**: Add Redis cache layer for frequently accessed data
4. **Metrics**: Export Prometheus metrics from database operations
5. **Backup**: Implement automated backup procedures
6. **Migration**: Add database migration system for schema changes

## References

- [Neo4j Python Driver (py2neo)](https://py2neo.org/)
- [Memori Documentation](https://github.com/yourusername/memori)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
