# Observability Control Plane

**Autonomous observability infrastructure management using LLM agents, Dagger orchestration, and distributed memory.**

---

## Features

- 🤖 **LLM-Powered Control Plane**: Central agent using Goose AI + MCP for intelligent decision-making
- 🧠 **Distributed Memory**: Memori + Neo4j for pattern recognition and historical fix recall
- 🐳 **Dagger Orchestration**: Containerized health checks and memory sync
- 📊 **Real-Time Dashboard**: Flask + HTMX monitoring interface
- 🔄 **Per-Service Agents**: Template-based telemetry validation for every app
- 🌐 **Cross-Platform**: Works on Linux/macOS/Windows with graceful degradation

---

## Quick Start

### Prerequisites

- Docker + Docker Compose
- Python 3.12+
- Dagger CLI (optional, for health checks)

### 1. Clone and Configure

```bash
git clone https://github.com/yourorg/observability-control
cd observability-control

# Copy environment template and fill in secrets
cp .env.example .env
# Edit .env and set:
#   - MEMORI_DB_PASSWORD
#   - NEO4J_PASSWORD
#   - GOOSEAI_API_KEY
```

### 2. Start Services

```bash
# Start all services (MCP, Memori, Neo4j, Postgres, Dashboard)
docker compose up -d

# Check service health
docker compose ps
```

### 3. Verify Dashboard

```bash
# Open dashboard in browser
python scripts/manage.py dashboard

# Or navigate manually to:
# http://localhost:5555
```

### 4. Run Health Check

```bash
# Requires Dagger CLI
python scripts/manage.py health

# Or directly:
dagger call periodic-health-check --issue="initial-setup"
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Observability Control Plane                  │
└─────────────────────────────────────────────────────────────────┘
                                   │
        ┌──────────────────────────┼──────────────────────────┐
        │                          │                           │
   ┌────▼────┐              ┌─────▼──────┐            ┌──────▼──────┐
   │ Central │              │  Dashboard  │            │   Dagger    │
   │  Agent  │◄────────────►│  (Flask)    │            │ Pipelines   │
   │(LLM+MCP)│              │             │            │             │
   └────┬────┘              └─────┬──────┘            └──────┬──────┘
        │                          │                           │
        │                   ┌──────▼──────┐                   │
        │                   │   Memori    │                   │
        │                   │  (Memory)   │                   │
        │                   └──────┬──────┘                   │
        │                          │                           │
   ┌────▼────────────────────┬────▼────┬───────────────────┬─▼──────┐
   │                         │         │                   │         │
┌──▼─────┐            ┌─────▼──┐  ┌──▼──────┐      ┌────▼─────┐   │
│ Neo4j  │            │Postgres│  │   MCP    │      │ Per-App  │   │
│ Graph  │            │   DB   │  │ Server   │      │ Agents   │   │
└────────┘            └────────┘  └──────────┘      └──────────┘   │
```

### Components

| Component | Purpose | Port |
|-----------|---------|------|
| **Central Agent** (`obs_agent.py`) | LLM-based control plane brain | N/A |
| **Dashboard** | Flask + HTMX monitoring UI | 5555 |
| **MCP Server** | Tool execution gateway | 8433 |
| **Memori** | Memory store (recall/remember) | Internal |
| **Neo4j** | Graph database for fix history | 7474, 7687 |
| **Postgres** | Memori backend storage | 5432 |

---

## Configuration

See [`.env.example`](.env.example) for all configuration options.

### Required Environment Variables

```bash
# Database
MEMORI_DB_PASSWORD=<strong-password>
NEO4J_PASSWORD=<strong-password>

# LLM Client
GOOSEAI_API_KEY=<your-api-key>
```

### Optional Environment Variables

```bash
# LLM Model
GOOSE_MODEL=gpt-neo-20b
LLM_BASE_URL=https://api.goose.ai/v1

# Platform Features
ENABLE_UNIX_TOOLS=false          # Set true for Linux/macOS rsync support
MEMORY_SYNC_ENABLED=false        # Enable central memory sync
```

---

## Management Commands

Use `scripts/manage.py` for common operations:

```bash
# Show help
python scripts/manage.py help

# Open dashboard in browser
python scripts/manage.py dashboard

# Run health check
python scripts/manage.py health

# Reset all services (WARNING: destroys data)
python scripts/manage.py reset

# Backup data directories
python scripts/manage.py backup

# Sync memory to central server
python scripts/manage.py memory-sync
```

---

## Per-Application Telemetry

Deploy telemetry agents to each application:

### 1. Copy Template

```bash
cp -r app-template /path/to/your-app/observability
```

### 2. Configure Environment

```bash
# In your app's .env
SERVICE_NAME=my-service
OBS_CONTROL_URL=http://localhost:5555
LANGSMITH_API_KEY=your-key
LOGFIRE_TOKEN=your-token
OTEL_EXPORTER_OTLP_ENDPOINT=http://collector:4318
```

### 3. Run Telemetry Check

```bash
cd /path/to/your-app
python observability/scripts/telemetry_agent.py
```

---

## Development

### Local Development

```bash
# Install dependencies
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt

# Run dashboard locally
cd dashboard
python app.py
```

### Testing Changes

```bash
# Test obs_agent in dry-run mode
python scripts/obs_agent.py --dry-run periodic-check

# Test resource monitoring
python scripts/resource_monitor.py
```

---

## Troubleshooting

### Services Won't Start

**Check logs:**
```bash
docker compose logs memori
docker compose logs neo4j
docker compose logs postgres
```

**Verify environment variables:**
```bash
# Ensure .env exists and has all required variables
cat .env
```

### Dashboard Shows Errors

**Check Memori connection:**
```bash
docker compose logs memori
```

**Verify Postgres is healthy:**
```bash
docker compose exec postgres pg_isready -U memori
```

### Memory Sync Fails (Windows)

Memory sync uses `rsync` which is not available on Windows by default. Options:

1. **Disable sync**: Set `MEMORY_SYNC_ENABLED=false` in `.env`
2. **Use WSL**: Install WSL2 and run sync commands from Linux
3. **Manual sync**: Copy `memory/` directory manually when needed

---

## Platform Compatibility

| Feature | Linux | macOS | Windows |
|---------|-------|-------|---------|
| Core Services | ✅ | ✅ | ✅ |
| Dashboard | ✅ | ✅ | ✅ |
| Disk Monitoring | ✅ | ✅ | ✅ |
| Memory Sync | ✅ | ✅ | ⚠️ Manual |
| Health Checks | ✅ | ✅ | ✅ |

**Legend:** ✅ Full Support | ⚠️ Partial/Manual | ❌ Not Supported

---

## Architecture Details

### Control Plane Flow

1. **Periodic Check** (via Dagger or manual trigger)
   - Runs health checks on all monitored services
   - Collects metrics, logs, traces from OTEL collectors
   - Reports status to central agent

2. **Central Agent Decision Loop**
   - Receives issue reports
   - Queries Memori for similar past issues
   - Queries Neo4j graph for fix history
   - Uses LLM + MCP to decide on remediation
   - Executes fixes via MCP tools

3. **Memory Recording**
   - Successful fixes stored in Memori
   - Relationships stored in Neo4j graph
   - Future similar issues auto-resolved

4. **Dashboard Visualization**
   - Real-time status of all services
   - Recent fix history
   - Disk usage and resource metrics
   - Manual intervention controls

### Dagger Functions

Available Dagger functions in `daggerfile.py`:

```python
# Periodic health check
dagger call periodic-health-check --issue="disk-full"

# Sync memory to central server
dagger call sync-memory-to-central

# Container with full context
dagger call container
```

### MCP Tool Integration

The central agent can call these MCP tools:

- **docker**: Container management
- **github**: Repository operations
- **filesystem**: File operations
- **postgres**: Database queries
- **neo4j**: Graph queries
- **ntfy**: Notifications

Configure allowed tools in `docker-compose.yml` under the `mcp` service.

---

## Observability Integration

This control plane is designed to manage observability infrastructure across 20+ repositories. It integrates with:

### LGTM Stack
- **Loki**: Log aggregation
- **Grafana**: Visualization and alerting
- **Tempo**: Distributed tracing
- **Mimir/Prometheus**: Metrics storage

### SaaS Platforms
- **Grafana Cloud**: Managed LGTM
- **LangSmith**: LLM observability
- **Logfire**: Structured logging

### OpenTelemetry
- **Central Collector**: Aggregates all telemetry
- **Per-App Sidecars**: Local collection and forwarding

See the main implementation package documentation for full integration details.

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make changes and test
4. Submit a pull request

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Support

- **Issues**: https://github.com/yourorg/observability-control/issues
- **Docs**: https://github.com/yourorg/observability-control/wiki
- **Main Package**: See repository root for full observability implementation package

---

## Related Documentation

- **Architecture Overview**: See main package documentation
- **Integration Guides**: Per-language guides in main package
- **Security**: API key management and secrets handling
- **Operations**: Runbooks and maintenance procedures
- **QA**: Validation scenarios and testing

---

## Version History

- **v1.0.0** (2025-01-23): Initial release
  - LLM-powered control plane
  - Memori + Neo4j memory system
  - Dashboard with HTMX
  - Dagger orchestration
  - Cross-platform support
