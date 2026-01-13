# Agent Council - AI Orchestration System

An autonomous AI agent orchestration system that coordinates multiple AI tools (Gemini, Jules, Qwen, and Goose) to work together on continuous development workflows.

## Overview

Agent Council implements a timer-based round-robin orchestration pattern where different AI agents collaborate on development tasks. Each agent has specialized capabilities and operates on its own schedule, sharing context through a persistent state management system.

## Key Features

- **Timer-based Scheduling**: Simple, reliable scheduling without complex frameworks
- **Persistent State Management**: JSON-based memory system maintains context between runs
- **Multi-Agent Coordination**: Round-robin execution with shared context
- **Headless Operation**: Fully automated, non-interactive agent execution
- **Platform Agnostic**: Python-based design runs on Windows, Linux, and macOS
- **Error Recovery**: Automatic retry with exponential backoff
- **Comprehensive Logging**: Full audit trail of all agent interactions
- **Context Sharing**: Agents build on each other's work through shared memory

## Agent Roster

| Agent  | Role | Schedule | Purpose |
|--------|------|----------|---------|
| **Gemini** | Reviewer | Every 10 minutes | Reviews progress, proposes next steps, architectural decisions |
| **Jules** | Developer | Every 60 minutes | Executes development tasks, writes code, implements features |
| **Qwen** | Analyst | Every 30 minutes | Analyzes code quality, suggests improvements, documentation |
| **Goose** | Executor | Every 15 minutes | Runs commands, tests, deployment tasks |

## System Architecture

```
┌─────────────────────────────────────────┐
│         Orchestration Engine            │
├─────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐            │
│  │  Timer   │  │ Scheduler │            │
│  │  System  │  │   (RR)    │            │
│  └──────────┘  └──────────┘            │
├─────────────────────────────────────────┤
│         Agent Layer                     │
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐     │
│  │Gem  │ │Jules│ │Qwen │ │Goose│     │
│  └─────┘ └─────┘ └─────┘ └─────┘     │
├─────────────────────────────────────────┤
│      State Management                   │
│  ┌──────────┐  ┌──────────┐           │
│  │  Memory  │  │  Context │           │
│  │   Store  │  │  Builder │           │
│  └──────────┘  └──────────┘           │
├─────────────────────────────────────────┤
│         Logging System                  │
│  ┌──────────────────────────┐          │
│  │ Structured JSON Logging  │          │
│  └──────────────────────────┘          │
└─────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.8 or higher
- Gemini CLI installed and configured
- Jules CLI with valid API key
- Qwen CLI installed
- Goose CLI installed
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/agent-council.git
cd agent-council

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Run setup
python scripts/setup.py
```

### Running the Orchestrator

```bash
# Start the orchestration system
python scripts/start.py

# Check status
python scripts/status.py

# Stop gracefully
python scripts/stop.py
```

## Configuration

The system uses YAML configuration files in `config/`:

- `agents.yaml` - Agent schedules and parameters
- `prompts/` - System prompts for each agent
- `secrets.env` - API keys and sensitive data (not in git)

See [docs/deployment/](docs/deployment/) for detailed configuration guides.

## Documentation

- [Architecture Overview](ARCHITECTURE.md) - System design and components
- [Linux Deployment](docs/deployment/linux-setup.md) - Deploy on Linux servers
- [Windows Deployment](docs/deployment/windows-setup.md) - Run on Windows
- [Agent Specifications](docs/agents/) - Detailed agent documentation
- [Contributing](CONTRIBUTING.md) - How to contribute to the project

## Platform Considerations

### Development
- **Windows**: Direct development on your current environment
- **Linux**: Better for production deployment
- **Docker**: Containerized deployment option

### Production Deployment
Recommended: Linux VPS or container for 24/7 operation
- Better process management with systemd
- Native shell scripting support
- More efficient resource usage
- Easier Docker deployment

See [docs/deployment/linux-vs-windows.md](docs/deployment/linux-vs-windows.md) for detailed comparison.

## Project Structure

```
agent-council/
├── src/                 # Core orchestration code
│   ├── orchestrator.py  # Main orchestration engine
│   ├── agents/          # Agent implementations
│   ├── scheduler/       # Scheduling logic
│   ├── state/           # State management
│   └── utils/           # Utilities
├── config/              # Configuration files
│   ├── agents.yaml      # Agent settings
│   └── prompts/         # Agent prompts
├── data/                # Runtime data
│   ├── state/           # Persistent state
│   ├── logs/            # Agent logs
│   └── workspace/       # Working directory
├── scripts/             # Management scripts
├── tests/               # Test suite
└── docs/                # Documentation
```

## Monitoring

The system provides comprehensive monitoring through:
- Structured JSON logs per agent
- Status dashboard (via `status.py`)
- Performance metrics
- Error tracking and alerts

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

## Roadmap

- [ ] Web dashboard for monitoring
- [ ] Slack/Discord notifications
- [ ] Dynamic agent scheduling
- [ ] Plugin system for new agents
- [ ] Distributed execution support
- [ ] Advanced context strategies

## Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Check the [documentation](docs/)
- Review [examples](docs/examples/)

---

**Agent Council** - Orchestrating AI agents for autonomous development workflows