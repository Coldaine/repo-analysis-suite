# v0.1 Alpha: Live Execution & Documentation Overhaul

## Why
We need to move from a mocked prototype to a functional "v0.1 Alpha" that uses real LLM calls and has accurate, consistent documentation. The previous documentation was outdated, and the orchestrator was using mock data.

## Changes

### 1. Functional Implementation
- **No Mocks**: Removed mock report generation from `orchestrator.py`.
- **Live Testing**: Rewrote `tests/integration/test_01_e2e_simple_review.py` to perform valid live reviews using real API keys.
- **Specialized Prompts**: Integrated `prompts.py` (TEST_KILLER, CODE_JANITOR, SCOPE_POLICE) into `agent_factory.py`.
- **CLI**: Implemented `MultiagentPanic review` command with `--local-file` support.

### 2. Configuration & Secrets
- **Env Var Auto-detection**: `settings.py` now automatically picks up `Z_AI_API_KEY`, `GITHUB_TOKEN`, `EXA_API_KEY`, etc.
- **No .env Files**: Removed documentation encouraging .env files; relying on environment injection (Bitwarden/Platform).

### 3. Documentation "Overkill"
- **AGENTS.md**: Complete rewrite to serve as the single source of truth for architecture, commands, and philosophy.
- **CLAUDE.md**: Symlinked to `AGENTS.md`.
- **System Design**: Updated `docs/architecture/system-design.md` to match reality.

## Verification
- ✅ **Automated**: `pytest tests/integration/test_01_e2e_simple_review.py` passes with live ZAI keys.
- ✅ **Manual**: Validated CLI command `python -m multiagentpanic review` outputs correct findings.

## Risks
- **Cost**: Live tests consume tokens. (Mitigated by z.ai unlimited tier).
- **Latency**: Tests are slower (~30s+).

## Next Steps
- Merge this PR.
- Connect MCP servers (Zoekt, Git) in the next sprint.
