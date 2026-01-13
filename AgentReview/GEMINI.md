# AgentReview (Multi-Agent Panic)

A multi-agent PR review system built on LangGraph that orchestrates specialized AI agents to provide comprehensive code reviews.

## Project Overview

*   **Type:** Python Codebase (Multi-Agent System)
*   **Purpose:** Automated PR review using specialized agents (Alignment, Dependencies, Testing, Security).
*   **Architecture:**
    *   **Orchestrator:** Manages the review process using LangGraph.
    *   **Agents:** Dynamic review agents created from templates.
    *   **Context:** Uses MCP (Model Context Protocol) tools (Zoekt, LSP, Git) for code understanding.
    *   **Observability:** Self-hosted stack with Langfuse, Prometheus, and Grafana.

## Tech Stack

*   **Language:** Python 3.11+
*   **Core Frameworks:** LangGraph, LangChain, Pydantic (Settings & Models)
*   **Data Store:** PostgreSQL (LangGraph Checkpointing), Redis (Caching)
*   **Observability:** Langfuse, Prometheus, Grafana, OpenTelemetry
*   **Package Manager:** `uv`
*   **Task Runner:** `just`
*   **Testing:** `pytest`

## Development Workflow

### Setup & Installation

The project uses `uv` for dependency management and `just` as a command runner.

```bash
just install  # Install dependencies
just check    # Verify environment configuration
just env      # Create .env from example if missing
```

### Running the Application

To run a review (CLI entry point):

```bash
# Review a PR (requires env vars for API keys)
python -m multiagentpanic review --repo owner/repo --pr 123 --local-file path/to/file.py
```

### Testing & Quality Assurance

Tests are split into unit (mocked) and integration (live LLM calls).

```bash
just test       # Run all tests
just test-cov   # Run tests with coverage report
just ci         # Run lint, typecheck, and tests
```

**Testing Conventions:**
*   **Unit Tests:** Use `mock_settings` fixture (autouse) in `tests/conftest.py` to mock API keys.
*   **Integration Tests:** Located in `tests/integration/`. These utilize real LLM calls and require valid API keys in `.env`.
*   **Mocking:** `unittest.mock` and custom fixtures (`mock_github`, `mock_mcp`) are used heavily in unit tests.

### Code Quality

Code style is enforced via `ruff` and `mypy`.

```bash
just format     # Format code with ruff
just lint       # Lint code with ruff
just fix        # Fix linting issues
just typecheck  # Run static type checking with mypy
```

## Observability

To spin up the local observability stack (Langfuse, Grafana, Prometheus):

```bash
just obs-up     # Start services via Docker Compose
just obs-down   # Stop services
```

*   **Langfuse:** http://localhost:3000
*   **Grafana:** http://localhost:3001

## Key Files & Directories

*   `src/multiagentpanic/`: Main package source.
    *   `cli.py`: CLI entry point (Typer application).
    *   `agents/orchestrator.py`: Main LangGraph orchestrator logic.
    *   `factory/`: Logic for dynamic agent creation.
    *   `config/settings.py`: Pydantic settings definition.
*   `tests/`: Test suite (unit/ and integration/).
*   `Justfile`: Command runner definitions.
*   `pyproject.toml`: Project metadata and dependencies.
*   `docker-compose.observability.yml`: Infrastructure configuration.
*   `docs/`: Extensive project documentation (Architecture, Guides).

## Environment Variables

See `.env.example` for required variables. API keys (`Z_AI_API_KEY`, `GITHUB_TOKEN`, etc.) are auto-detected by `pydantic-settings`.
