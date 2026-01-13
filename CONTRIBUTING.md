# Contributing to Repository Analysis Suite

## Current Status

This monorepo was created on **2026-01-13** by consolidating 4 standalone repositories:

- **AgentReview** (62 commits, actively maintained)
- **repo-analysis-system** (18 commits, actively maintained)
- **mcp-monitoring-interface** (2 commits, hackathon prototype)
- **observability-control-plane** (1 commit, scaffolded but unused)

**⚠️ The monorepo is in active consolidation. Significant architectural changes are expected.**

---

## Immediate Work Needed

### 1. Consolidation Tasks

- [ ] **Extract shared agent primitives**
  - Both AgentReview and repo-analysis-system use LangGraph
  - Create `lib/agents/` with common prompt templates, workflow patterns, and tool integrations
  - Deduplicate Pydantic models and state schemas

- [ ] **Unify database strategy**
  - AgentReview uses PostgreSQL for cross-PR learning
  - repo-analysis-system uses PostgreSQL for state management
  - Design shared schema or clear separation strategy

- [ ] **Migrate mcp-monitoring-interface to UV**
  - Currently uses pip + requirements.txt
  - Should use pyproject.toml + uv for consistency
  - Update documentation

- [ ] **Decide on observability-control-plane**
  - Integrate useful patterns into active projects, OR
  - Archive as reference material
  - Don't let it sit as dead weight

### 2. Documentation Improvements

- [ ] Create `docs/` directory with architecture diagrams
- [ ] Document agent workflow patterns
- [ ] Create integration guide for using projects together
- [ ] Add troubleshooting guide
- [ ] Document PostgreSQL schema and migration strategy

### 3. Infrastructure

- [ ] **Unified docker-compose.yml** at monorepo root
  - Start all services (PostgreSQL, Neo4j, Redis, etc.)
  - Shared network for inter-service communication
  - Volume management strategy

- [ ] **Shared configuration**
  - Environment variable standards across all projects
  - Bitwarden Secrets Manager integration patterns
  - Logging and telemetry configuration

- [ ] **CI/CD**
  - GitHub Actions for testing each project
  - Shared test utilities and fixtures
  - Automated dependency updates (Renovate or Dependabot)

### 4. Code Quality

- [ ] **Linting and formatting**
  - Standardize on ruff or black + isort
  - Pre-commit hooks for all projects
  - Type checking with mypy

- [ ] **Testing**
  - Shared test utilities in `lib/testing/`
  - Integration tests that span multiple projects
  - Mock/fixture sharing

---

## Development Workflow

### Setting Up

1. **Clone the monorepo**:
   ```bash
   git clone https://github.com/Coldaine/repo-analysis-suite.git
   cd repo-analysis-suite
   ```

2. **Choose your project**:
   ```bash
   cd AgentReview  # or repo-analysis-system, etc.
   ```

3. **Install dependencies**:
   ```bash
   # For UV-based projects (AgentReview, repo-analysis-system)
   uv sync

   # For pip-based projects (mcp-monitoring-interface, observability-control-plane)
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

### Making Changes

1. **Create a feature branch** from `main`
2. **Make your changes** in the relevant project directory
3. **Test locally** using the project's test suite
4. **Update documentation** if you change APIs or workflows
5. **Commit with clear messages** describing what changed and why
6. **Push and create a PR**

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`

**Scopes**: `AgentReview`, `repo-analysis-system`, `mcp-monitoring`, `control-plane`, `lib`, `docs`, `ci`

**Examples**:
```
feat(AgentReview): add SSRF protection to database URL validation

- Add _is_safe_host() function with URL scheme validation
- Reject private IPs and metadata endpoints
- Prevents attackers from using DB URLs to probe networks

Fixes #44 (review comment from qodo-code-review)
```

```
refactor(lib): extract common agent primitives from AgentReview and repo-analysis-system

- Create lib/agents/base.py with AgentBase class
- Extract prompt templates to lib/agents/prompts/
- Share Pydantic models for LLM responses

This is the first step toward unified agent orchestration.
```

---

## Project-Specific Guidelines

### AgentReview

- All agents must have clear prompts in `agents/prompts.py`
- New review agents require templates in `factory/agent_factory.py`
- Database changes need migration scripts
- Integration tests must use mocking (no live API keys)

### repo-analysis-system

- Use Bitwarden Secrets Manager for all secrets
- LangGraph workflows go in `src/`
- Documentation in `docs/` following existing structure
- All analysis must be observable (logging, metrics, reports)

### mcp-monitoring-interface

- Gradio UI changes should be tested in browser
- Slack bot changes require testing in a Slack workspace
- Keep the mock MCP server updated for local testing

### observability-control-plane

- **Do not add features until consolidation decision is made**
- If integrating patterns, extract to `lib/` first
- If archiving, document useful patterns before removal

---

## Testing Strategy

### Unit Tests
- Test individual functions and classes in isolation
- Use mocks for external dependencies (LLMs, databases, APIs)
- Aim for 80%+ coverage on business logic

### Integration Tests
- Test agent workflows end-to-end
- Use real databases (PostgreSQL in Docker)
- Mock only external APIs (LLM providers, GitHub, etc.)

### System Tests
- Test interactions between projects
- Example: repo-analysis-system triggering AgentReview for PR analysis
- Use Docker Compose to spin up full stack

---

## Architecture Principles

As we consolidate, follow these principles:

1. **Shared libraries over duplication**
   - If two projects need the same code, it goes in `lib/`
   - Exception: project-specific business logic stays in project dir

2. **Clear boundaries**
   - Each project should have a well-defined responsibility
   - Inter-project communication through well-defined interfaces
   - Avoid tight coupling

3. **Observable by default**
   - All agent actions should be logged
   - Metrics for performance (latency, token usage, error rates)
   - Tracing for debugging complex workflows

4. **Security-first**
   - No secrets in code or environment files
   - Input validation for all user-provided data
   - Sanitize error messages before displaying

5. **Developer experience**
   - Fast setup (one command to start working)
   - Clear documentation with examples
   - Helpful error messages

---

## Questions?

This is a work in progress. If you're unsure about:
- Where code should live (project dir vs `lib/`)
- How to integrate with other projects
- Architecture decisions

Create an issue for discussion before implementing.

---

**Last Updated**: 2026-01-13
