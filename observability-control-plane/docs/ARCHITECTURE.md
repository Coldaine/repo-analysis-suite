# Observability Control Plane - Database Architecture

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         External Clients                                 │
├─────────────────────────────────────────────────────────────────────────┤
│  HTTP API Clients │ Dashboard UI │ Agent Scripts │ Monitoring Tools     │
└─────────────────────┬───────────────────────────────────────────────────┘
                      │
                      │ HTTP/REST
                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       Dashboard Layer (Flask)                            │
│                      dashboard/app.py                                    │
├─────────────────────────────────────────────────────────────────────────┤
│  Endpoints:                                                              │
│  • GET  /api/state          → Current system state                      │
│  • GET  /api/agents         → List all agents                           │
│  • POST /api/register-agent → Register new agent                        │
│  • GET  /api/fixes          → Recent fixes (paginated)                  │
│  • GET  /health             → Health check                              │
│  • GET  /api/metrics        → Prometheus metrics                        │
│  • POST /api/telemetry-report → Receive telemetry                       │
└─────────────────────┬───────────────────────────────────────────────────┘
                      │
                      │ Function Calls
                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    Agent Memory Layer                                    │
│                 scripts/agent_memory.py                                  │
├─────────────────────────────────────────────────────────────────────────┤
│  High-Level API:                                                         │
│  • recall(key, limit)           → Search both databases                 │
│  • remember(key, content, meta) → Store in both databases               │
│  • get_recent_fixes(limit)      → Query Neo4j                           │
│  • get_all_agents()             → Query Neo4j                           │
│  • register_agent(name, server) → Write to Neo4j                        │
│  • find_similar_issues(type)    → Pattern matching                      │
└─────────────────────┬───────────────────────────────────────────────────┘
                      │
                      │ Function Calls
                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                   Database Manager Layer                                 │
│                scripts/database_helpers.py                               │
├─────────────────────────────────────────────────────────────────────────┤
│  DatabaseManager Class:                                                  │
│                                                                          │
│  Neo4j Operations:                    Memori Operations:                │
│  ├─ get_recent_fixes()                ├─ recall_fixes()                 │
│  ├─ find_similar_issues()             └─ remember_fix()                 │
│  ├─ get_fix_success_rate()                                              │
│  ├─ get_all_agents()                  Utilities:                        │
│  ├─ register_agent()                  └─ get_database_stats()           │
│  ├─ get_issue_patterns()                                                │
│  └─ remember_fix()                                                      │
└─────────┬────────────────────────────────────┬───────────────────────────┘
          │                                    │
          │ py2neo                             │ memori + psycopg2
          ▼                                    ▼
┌─────────────────────────┐      ┌────────────────────────────────────────┐
│      Neo4j Graph DB      │      │    PostgreSQL + Memori Vector DB       │
│    bolt://neo4j:7687     │      │ postgresql://postgres:5432/memori      │
├─────────────────────────┤      ├────────────────────────────────────────┤
│ Nodes:                  │      │ Tables:                                 │
│ • Fix                   │      │ • memori_embeddings                     │
│   - issue: String       │      │ • memori_metadata                       │
│   - solution: String    │      │                                         │
│   - success: Boolean    │      │ Features:                               │
│   - ts: Integer         │      │ • Semantic search                       │
│ • Agent                 │      │ • Vector embeddings                     │
│   - name: String*       │      │ • Full-text search                      │
│   - server: String      │      │                                         │
│   - status: String      │      │                                         │
│   - last_seen: Integer  │      │                                         │
│                         │      │                                         │
│ Indexes:                │      │                                         │
│ • fix_timestamp         │      │                                         │
│ • fix_issue             │      │                                         │
│ • fix_success           │      │                                         │
│ • agent_name (unique)   │      │                                         │
│ • agent_status          │      │                                         │
│ • agent_last_seen       │      │                                         │
└─────────────────────────┘      └────────────────────────────────────────┘
```

## Data Flow Diagrams

### 1. Storing a Fix (Write Path)

```
Agent/Dashboard
      │
      │ POST /api/telemetry-report
      │ or direct call to remember()
      ▼
┌─────────────────┐
│ agent_memory.   │
│ remember()      │
└─────┬───────────┘
      │
      │ Parses metadata, determines success
      ▼
┌─────────────────────────────┐
│ db_manager.remember_fix()   │
└─────┬───────────────────────┘
      │
      ├──────────────┬─────────────────┐
      │              │                 │
      ▼              ▼                 ▼
┌──────────┐   ┌──────────┐    ┌─────────────┐
│ Neo4j    │   │ Memori   │    │ Log Entry   │
│ CREATE   │   │ add()    │    │ INFO level  │
│ (f:Fix)  │   │          │    │             │
└──────────┘   └──────────┘    └─────────────┘
```

### 2. Querying Fixes (Read Path)

```
Dashboard/API
      │
      │ GET /api/fixes?limit=20
      │ or /api/state
      ▼
┌─────────────────────┐
│ agent_memory.       │
│ get_recent_fixes()  │
└─────┬───────────────┘
      │
      ▼
┌─────────────────────────────────┐
│ db_manager.get_recent_fixes()   │
└─────┬───────────────────────────┘
      │
      │ MATCH (f:Fix) RETURN ...
      │ ORDER BY f.ts DESC
      ▼
┌─────────────────┐
│ Neo4j Query     │
│ Returns List    │
└─────┬───────────┘
      │
      │ Format timestamps
      │ Convert to ISO 8601
      ▼
┌─────────────────┐
│ JSON Response   │
│ to Client       │
└─────────────────┘
```

### 3. Semantic Search (Hybrid Path)

```
Agent Script
      │
      │ recall("issue:connection", limit=10)
      ▼
┌─────────────────────────────────┐
│ agent_memory.recall()           │
│ Detects "issue:" prefix         │
└─────┬───────────────────────────┘
      │
      ├─────────────────┬──────────────────┐
      │                 │                  │
      ▼                 ▼                  │
┌──────────────┐  ┌─────────────────┐    │
│ Memori       │  │ Neo4j           │    │
│ recall()     │  │ find_similar()  │    │
│              │  │ WHERE CONTAINS  │    │
└──────┬───────┘  └──────┬──────────┘    │
      │                   │                │
      │                   │                │
      └─────────┬─────────┘                │
                │                          │
                │ Combine results          │
                │ Deduplicate              │
                ▼                          │
      ┌────────────────────┐               │
      │ Merged Results     │               │
      │ [Memori] + [Neo4j] │               │
      └────────┬───────────┘               │
               │                           │
               │ Return to caller          │
               ▼                           │
         Application Code ◄────────────────┘
```

### 4. Agent Registration Flow

```
obs_agent.py startup
      │
      │ register_agent("obs-agent-1", "prod-server-1")
      ▼
┌─────────────────────────┐
│ agent_memory.           │
│ register_agent()        │
└─────┬───────────────────┘
      │
      ▼
┌─────────────────────────────────┐
│ db_manager.register_agent()     │
└─────┬───────────────────────────┘
      │
      │ MERGE (a:Agent {name: $name})
      │ SET a.server = $server,
      │     a.status = 'active',
      │     a.last_seen = timestamp()
      ▼
┌─────────────────────────────────┐
│ Neo4j Graph                      │
│ Creates or updates Agent node    │
└─────┬───────────────────────────┘
      │
      │ Success/Failure
      ▼
┌─────────────────┐
│ Boolean Result  │
│ True/False      │
└─────────────────┘
```

## Component Interactions

### Database Manager (database_helpers.py)

```
DatabaseManager
├── __init__()
│   ├── Connect to Neo4j (py2neo.Graph)
│   └── Check Memori availability
│
├── Neo4j Operations
│   ├── get_recent_fixes(limit)
│   ├── find_similar_issues(issue_type, limit)
│   ├── get_fix_success_rate(fix_type)
│   ├── get_all_agents()
│   ├── register_agent(name, server)
│   └── get_issue_patterns(days)
│
├── Memori Operations
│   ├── recall_fixes(context, limit)
│   └── remember_fix(issue, solution, success)
│
└── Utilities
    └── get_database_stats()
```

### Agent Memory (agent_memory.py)

```
agent_memory module
├── recall(key, limit)
│   ├── If key starts with "issue:"
│   │   ├── Query Memori
│   │   ├── Query Neo4j
│   │   └── Merge results
│   └── Else: Query Memori only
│
├── remember(key, content, metadata)
│   ├── Parse success from metadata/content
│   ├── Store in Memori
│   └── If "issue:" key: Store in Neo4j
│
├── get_recent_fixes(limit)
│   └── Wrapper → db_manager.get_recent_fixes()
│
├── get_all_agents()
│   └── Wrapper → db_manager.get_all_agents()
│
├── register_agent(name, server)
│   └── Wrapper → db_manager.register_agent()
│
└── find_similar_issues(issue_type, limit)
    └── Direct Neo4j query
```

### Dashboard API (dashboard/app.py)

```
Flask Application
├── Routes
│   ├── GET  /                    → index()
│   ├── GET  /api/state           → api_state()
│   ├── GET  /api/agents          → api_agents()
│   ├── POST /api/register-agent  → api_register_agent()
│   ├── GET  /api/fixes           → api_fixes()
│   ├── POST /api/telemetry-report→ telemetry_report()
│   ├── GET  /health              → health()
│   └── GET  /api/metrics         → api_metrics()
│
├── Error Handlers
│   ├── 404 → JSON error response
│   └── 500 → JSON error response
│
└── Helpers
    └── _system_disk_usage() → psutil disk check
```

## Database Initialization

```
scripts/init_neo4j.py
      │
      │ Read NEO4J_URI, NEO4J_PASSWORD
      ▼
┌────────────────────────┐
│ Connect to Neo4j       │
└────────┬───────────────┘
         │
         ▼
┌────────────────────────────────────────┐
│ Create Indexes                          │
│ • CREATE INDEX fix_timestamp           │
│ • CREATE INDEX fix_issue               │
│ • CREATE INDEX fix_success             │
│ • CREATE INDEX agent_name              │
│ • CREATE INDEX agent_status            │
│ • CREATE INDEX agent_last_seen         │
└────────┬───────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────┐
│ Create Constraints                      │
│ • CREATE CONSTRAINT agent_name_unique  │
└────────┬───────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────┐
│ Verify Setup                            │
│ • Count total nodes                     │
│ • Count Fix nodes                       │
│ • Count Agent nodes                     │
│ • Log statistics                        │
└─────────────────────────────────────────┘
```

## Error Handling Strategy

```
┌─────────────────────────────────────┐
│ Any Database Operation              │
└─────────────┬───────────────────────┘
              │
              ▼
        ┌─────────┐
        │ Try:    │
        └────┬────┘
             │
             ├─→ Success → Return data
             │
             └─→ Exception
                    │
                    ▼
            ┌───────────────┐
            │ Log Error     │
            │ (logger.error)│
            └───────┬───────┘
                    │
                    ▼
            ┌───────────────────────┐
            │ Return Safe Default   │
            │ • Empty list []       │
            │ • False               │
            │ • 0.0                 │
            │ • Empty dict {}       │
            └───────┬───────────────┘
                    │
                    ▼
            ┌───────────────────────┐
            │ Application Continues │
            │ (No crash)            │
            └───────────────────────┘
```

## Monitoring and Observability

### Health Check Flow

```
GET /health
      │
      ▼
┌──────────────────────────┐
│ Check Disk Usage         │
│ psutil.disk_usage('/')   │
└──────┬───────────────────┘
       │
       ▼
┌──────────────────────────┐
│ Check Memory Usage       │
│ psutil.virtual_memory()  │
└──────┬───────────────────┘
       │
       ▼
┌──────────────────────────┐
│ Check Database           │
│ get_recent_fixes(1)      │
└──────┬───────────────────┘
       │
       ▼
┌──────────────────────────┐
│ Aggregate Status         │
│ • healthy                │
│ • degraded               │
│ • unhealthy              │
└──────┬───────────────────┘
       │
       ▼
┌──────────────────────────┐
│ Return JSON + HTTP Code  │
│ 200, 503                 │
└──────────────────────────┘
```

### Metrics Endpoint

```
GET /api/metrics
      │
      ▼
┌──────────────────────────────────┐
│ Gather System Metrics            │
│ • Disk usage (bytes)             │
│ • Memory usage (bytes)           │
│ • CPU usage (percent)            │
│ • Agent count (from database)    │
└──────┬───────────────────────────┘
       │
       ▼
┌──────────────────────────────────┐
│ Format as Prometheus Metrics     │
│ # HELP dashboard_disk_usage_bytes│
│ # TYPE dashboard_disk_usage_bytes│
│ dashboard_disk_usage_bytes 12345 │
│ ...                              │
└──────┬───────────────────────────┘
       │
       ▼
┌──────────────────────────────────┐
│ Return text/plain response       │
└──────────────────────────────────┘
```

## Security Considerations

1. **Credentials**: All database credentials from environment variables
2. **No Hardcoded Secrets**: All passwords/tokens configurable
3. **Connection Encryption**: Neo4j uses bolt:// (can upgrade to bolt+s://)
4. **Input Validation**: All user inputs validated before database queries
5. **SQL Injection**: Using parameterized queries (py2neo handles this)
6. **Error Messages**: Errors logged but sanitized for API responses

## Performance Characteristics

### Neo4j Queries
- **Indexed Queries**: O(log n) lookup time
- **Full Scans**: O(n) for pattern matching without indexes
- **Agent Lookup**: O(1) with unique constraint
- **Recent Fixes**: O(k log n) where k = limit

### Memori Operations
- **Vector Search**: O(log n) with indexing
- **Embedding Generation**: Depends on model (typically <1s)
- **Storage**: O(1) insertion time

### Caching Strategy
- **No Cache**: Currently direct queries to databases
- **Future**: Consider Redis for frequently accessed data

## Scaling Considerations

### Current Limits
- Single Neo4j instance
- Single PostgreSQL instance
- No connection pooling configuration
- No query result caching

### Future Improvements
1. **Read Replicas**: Add Neo4j read replicas
2. **Connection Pooling**: Configure py2neo pool size
3. **Caching**: Redis cache for hot data
4. **Sharding**: Partition data by time/server
5. **Batch Operations**: Bulk inserts for high-volume data

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Compose                        │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │  Dashboard   │  │   Neo4j      │  │  PostgreSQL  │ │
│  │  Flask:5555  │  │   bolt:7687  │  │    :5432     │ │
│  │              │  │   http:7474  │  │              │ │
│  └──────┬───────┘  └──────────────┘  └──────────────┘ │
│         │                                               │
│         │                                               │
│  ┌──────▼────────────────────────────────────────────┐ │
│  │  obs_agent.py (runs periodically via cron/systemd)│ │
│  └───────────────────────────────────────────────────┘ │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## File Dependency Graph

```
dashboard/app.py
    │
    ├─→ scripts/agent_memory.py
    │       │
    │       ├─→ scripts/database_helpers.py
    │       │       │
    │       │       ├─→ py2neo
    │       │       └─→ memori
    │       │
    │       ├─→ memori (direct)
    │       └─→ py2neo (direct)
    │
    └─→ psutil

scripts/obs_agent.py
    │
    ├─→ scripts/agent_memory.py (via from memori import)
    ├─→ py2neo (direct)
    └─→ httpx

scripts/init_neo4j.py
    └─→ py2neo

scripts/test_database.py
    │
    ├─→ scripts/database_helpers.py
    └─→ scripts/agent_memory.py
```

This architecture provides a robust, scalable foundation for the observability control plane with proper separation of concerns, error handling, and extensibility.
