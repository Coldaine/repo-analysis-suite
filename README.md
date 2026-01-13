# Repository Analysis Suite

**A unified toolkit for AI-powered repository analysis, monitoring, and code review.**

This monorepo consolidates several related projects focused on automated repository analysis, code review, and observability for development workflows. All projects leverage LLM agents to provide intelligent insights and automation.

---

## 📦 Projects

### 1. **AgentReview** (`AgentReview/`)

Multi-agent PR review system built on LangGraph. Orchestrates specialized AI agents to provide comprehensive code reviews.

- **Purpose**: Automated pull request review with specialized agents
- **Tech Stack**: LangGraph, Pydantic 2.9+, MCP tools
- **Key Features**:
  - Specialized review agents (CODE_JANITOR, TEST_KILLER, SCOPE_POLICE)
  - Auto-start PostgreSQL for cross-PR learning
  - Integration with Zoekt code search, LSP, Git history
  - Live testing with real LLM calls
- **Status**: ✅ Active, production-ready
- **Recent Updates**:
  - Dependency updates (langchain 1.2.5)
  - PostgreSQL lifecycle management with auto-start
  - Security hardening (SSRF protection, subprocess timeouts)

**Quick Start**:
```bash
cd AgentReview
uv sync
uv run python -m multiagentpanic review --repo owner/repo --pr 123
```

---

### 2. **repo-analysis-system** (`repo-analysis-system/`)

Intelligent platform for monitoring repository health, tracking goals, and detecting architectural divergences across multi-repository portfolios.

- **Purpose**: Portfolio-wide repository health monitoring and charter compliance
- **Tech Stack**: LangGraph, PostgreSQL, Bitwarden Secrets Manager
- **Key Features**:
  - Repository charter tracking and compliance
  - Forensics, Security, and Alignment agents
  - Automated drift detection
  - Webhook and cron-based automation
  - Structured observability and reporting
- **Status**: ✅ Active
- **Recent Updates**:
  - UV migration complete
  - Security patch (CVE-2025-68664 in langchain-core)

**Quick Start**:
```bash
cd repo-analysis-system
uv sync
bws run -- python scripts/run_graph.py analyze --repos "owner/repo"
```

---

### 3. **mcp-monitoring-interface** (`mcp-monitoring-interface/`)

Comprehensive Gradio-based monitoring dashboard for Model Context Protocol (MCP) interactions with Slack bot integration.

- **Purpose**: Real-time monitoring of MCP server interactions
- **Tech Stack**: Gradio, Slack Bolt, httpx
- **Key Features**:
  - Real-time MCP context tracking
  - Slash command integration (`/mcp-monitor`)
  - Interactive dashboards (Metrics, Session Explorer)
  - Performance analytics (latency, token usage, error rates)
  - Context provisioning visualization
- **Status**: ⚠️ Hackathon project (2 commits, last push 2025-11-11)
- **Use Case**: Observability for MCP protocol debugging

**Quick Start**:
```bash
cd mcp-monitoring-interface
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python gradio_app.py  # Dashboard at http://localhost:7860
```

---

### 4. **observability-control-plane** (`observability-control-plane/`)

Autonomous observability infrastructure management using LLM agents, Dagger orchestration, and distributed memory.

- **Purpose**: Self-healing observability infrastructure
- **Tech Stack**: Goose AI, Dagger, Memori, Neo4j, Flask, Docker Compose
- **Key Features**:
  - LLM-powered control plane for infrastructure decisions
  - Distributed memory (Memori + Neo4j) for pattern recognition
  - Per-service telemetry agents
  - Auto-remediation of infrastructure issues
  - Real-time Flask dashboard
- **Status**: 🚧 Scaffolded but unused (1 commit, never deployed)
- **Note**: 3,427 LOC dropped in a single commit, aspirational design

**Architecture**:
- Central Agent (LLM + MCP) makes decisions
- Memori stores fix history
- Neo4j tracks relationships
- Dagger runs health checks
- Dashboard visualizes state

---

## 🎯 Vision & Strategy

### Current State

This monorepo was created by consolidating 4 standalone repositories that share a common theme: **AI-powered development tooling and observability**. As of 2026-01-13:

- **AgentReview** and **repo-analysis-system** are actively used and maintained
- **mcp-monitoring-interface** is a functional prototype from a hackathon
- **observability-control-plane** is an ambitious design that was never deployed

### Going Forward

**⚠️ This monorepo needs active work to unify and consolidate these projects.**

#### Short-Term Priorities

1. **Consolidate overlapping functionality**
   - AgentReview and repo-analysis-system both use LangGraph orchestration
   - Both have monitoring/observability components
   - Potential for shared agent primitives and tooling

2. **Evaluate observability-control-plane**
   - **Option A**: Extract useful patterns and integrate into active projects
   - **Option B**: Archive as research/reference material
   - **Decision needed**: Is self-healing infra a real goal, or was it exploratory?

3. **Unify tech stack**
   - All Python projects should use UV (✅ AgentReview, ✅ repo-analysis-system)
   - Standardize on LangGraph for agent orchestration
   - Shared PostgreSQL schemas for cross-project learning

4. **Merge mcp-monitoring-interface capabilities**
   - Could become a monitoring layer for AgentReview's MCP tool usage
   - Integrate Gradio dashboards into repo-analysis-system's observability

#### Medium-Term Goals

- **Shared agent library**: Extract common agent patterns (prompts, tools, workflows)
- **Unified observability**: Single dashboard for all repo analysis and review activities
- **Cross-project learning**: PostgreSQL database shared across AgentReview and repo-analysis-system
- **Consolidated deployment**: Docker Compose setup for running entire suite locally

#### Long-Term Vision

Create a **comprehensive AI-powered DevOps platform** that:
- Reviews PRs with specialized agents
- Monitors repository health and compliance
- Tracks observability signals across development workflows
- Self-heals infrastructure issues (if we pursue that direction)
- Provides unified dashboards and notifications

---

## 🛠️ Development

### Prerequisites

- Python 3.12+
- UV (for dependency management)
- Docker + Docker Compose (for databases and services)
- PostgreSQL 16+ (local or cloud)
- Bitwarden Secrets Manager CLI (for repo-analysis-system)

### Monorepo Structure

```
repo-analysis-suite/
├── AgentReview/              # PR review with multi-agent orchestration
├── repo-analysis-system/     # Portfolio health monitoring
├── mcp-monitoring-interface/ # MCP protocol observability
├── observability-control-plane/ # Self-healing infrastructure (unused)
├── README.md                 # This file
└── ROADMAP.md                # Consolidation plan (TODO)
```

### Running Projects

Each project has its own README with detailed setup instructions. Generally:

```bash
# For UV-based projects (AgentReview, repo-analysis-system)
cd <project>/
uv sync
uv run <command>

# For pip-based projects (mcp-monitoring-interface, observability-control-plane)
cd <project>/
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python <entrypoint>
```

### Shared Configuration

**Environment Variables** (via Bitwarden Secrets Manager):
- `Z_AI_API_KEY` - Z.ai API key for LLM calls
- `GITHUB_TOKEN` - GitHub API access
- `POSTGRES_URL` - Shared PostgreSQL connection string
- See individual project READMEs for project-specific vars

**PostgreSQL Database**:
- AgentReview uses `agentreview_dev` database for cross-PR learning
- repo-analysis-system can use a shared or separate database
- Consider consolidating schemas in the future

---

## 📊 Project Status

| Project | LOC | Commits | Last Updated | Status |
|---------|-----|---------|--------------|--------|
| AgentReview | 11,562 | 62 | 2026-01-13 | ✅ Active |
| repo-analysis-system | 8,474 | 18 | 2026-01-13 | ✅ Active |
| mcp-monitoring-interface | 1,847 | 2 | 2025-11-11 | ⚠️ Prototype |
| observability-control-plane | 3,427 | 1 | 2025-11-24 | 🚧 Unused |
| **Total** | **25,310** | **83** | - | - |

---

## 🗺️ Roadmap

### Phase 1: Consolidation (Next 2-4 weeks)

- [ ] Create shared `lib/` directory for common code
- [ ] Extract agent primitives from AgentReview and repo-analysis-system
- [ ] Migrate mcp-monitoring-interface to UV
- [ ] Decide fate of observability-control-plane (integrate or archive)
- [ ] Unified docker-compose.yml for local development
- [ ] Shared PostgreSQL schema design

### Phase 2: Integration (1-2 months)

- [ ] Cross-project agent communication (repo-analysis-system → AgentReview)
- [ ] Unified dashboard combining all monitoring views
- [ ] Shared telemetry and observability layer
- [ ] Common configuration management
- [ ] Consolidated documentation site

### Phase 3: Platform (3-6 months)

- [ ] Single unified CLI for all operations
- [ ] Production deployment strategy (Docker, k8s, or Modal)
- [ ] Monitoring and alerting for the entire suite
- [ ] Public API for external integrations
- [ ] Plugin system for custom agents and tools

---

## 📝 Contributing

This is a personal project monorepo currently in active consolidation. Contributions welcome once the architecture stabilizes.

### Current Focus Areas

1. **Deduplication**: Identify and merge overlapping functionality
2. **Standardization**: Unified tooling, dependencies, and patterns
3. **Documentation**: Comprehensive guides for each project and integration points
4. **Testing**: Shared test infrastructure and CI/CD

---

## 📄 License

MIT License - see individual project directories for original license files.

---

## 🔗 Related Documentation

- [AgentReview AGENTS.md](AgentReview/AGENTS.md) - Agent instructions and prompts
- [repo-analysis-system docs/](repo-analysis-system/docs/) - Architecture and workflow docs
- [mcp-monitoring-interface README.md](mcp-monitoring-interface/README.md) - Dashboard setup guide
- [observability-control-plane README.md](observability-control-plane/README.md) - Control plane architecture

---

**Last Updated**: 2026-01-13
**Status**: 🚧 Active consolidation in progress
