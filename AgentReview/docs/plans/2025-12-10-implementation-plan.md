# Implementation Plan — Codebase Review Actions (2025-12-10)

Author: Automated code review (on behalf of repo maintainers)
Date: 2025-12-10

Overview
--------
This implementation plan lays out prioritized tasks that directly address the findings in
`docs/reports/2025-12-10-codebase-review.md`. It is structured as a set of workstreams with
concrete tasks, owners, estimates, and acceptance criteria. The highest priority items are
tasked to prevent runtime failures or fix correctness issues (hard crashes, brittle JSON parsing).

Goals
-----
- Eliminate runtime crashes due to improper `asyncio.run()` usage and ensure compatibility with async runtimes.
- Improve reliability of LLM outputs by adopting structured outputs / schema validation.
- Improve performance and cost control by parallelizing context gathering with bounded concurrency and cost budget enforcement.
- Reduce duplication in MCP tool resolution and make tool selection capability-driven.
- Run a dependency and security audit and propose versioning & upgrades for key packages.

Scope & Approach
----------------
The initial scope focuses on the highest priority tasks (1 and 2 below). Each workstream includes a concrete code plan, tests, and acceptance criteria.

Timeboxing & Estimates
----------------------
- Priority #1 (Async Fix): 2–4 hours
- Priority #2 (Structured Output): 1–2 days
- Priority #3 (Concurrency): 1 day
- Priority #4 (Tool Registry): 2–3 days
- Priority #5 (Dependency Audit / Upgrades): 1 day

Workstreams
-----------

Workstream A — Fix `asyncio.run` bridging (Critical)
--------------------------------------------------
Summary: Remove unsafe `asyncio.run()` wrappers or create a safe sync bridge that handles both sync and async contexts.

Tasks:
- A1: Convert `AgentFactory.create_context_agent` to return a pure async function (remove `create_context_agent` sync wrapper) and refactor all call sites to use the async API. (Files: `src/multiagentpanic/factory/agent_factory.py`) 
- A2: Replace `asyncio.run(run_mcp_tool(...))` in `src/multiagentpanic/tools/git.py` with a safe async call (if calling from sync code, use `anyio.from_thread.run`). Ensure `run_mcp_tool` is async.
- A3: Add tests to simulate running within a running event loop (pytest-asyncio) and ensure no RuntimeError is raised.

Owner: Devs working on orchestration or rapid integration (1 dev)

Acceptance Criteria:
- No code path uses `asyncio.run(...)` in modules that may be called from an event loop.
- Unit tests for `AgentFactory.create_context_agent` and `tools/git.get_status_mcp` show correct behavior within a running event loop.

Risks: Small risk of test failures if other modules expect the sync wrapper; mitigation is to add a small shim layer or maintain compatibility for libraries that rely on a sync interface while migrating code to full async usage.

Workstream B — Structured Output & Schema Validation (Critical)
----------------------------------------------------------------
Summary: Replace ad hoc JSON parsing of LLM responses with robust structured output parsing using Pydantic (or LangChain 1.x structured outputs) and add model-profile checks.

Tasks:
- B1: Define Pydantic models for review agent plan & analysis: `ReviewPlan`, `ContextRequest`, `ReviewFindings`. Add validation and types for fields required. (Files: `src/multiagentpanic/domain/schemas.py`) 
- B2: Update `_review_agent_plan` and `_review_agent_analyze` to use `llm.with_structured_output(ReviewPlan)` and `llm.with_structured_output(ReviewFindings)` (or the recommended LangChain 1.x pattern) if LLM supports it. Otherwise, use robust parsers that test success; log raw output and emit parse metrics.
- B3: Add unit tests for: good JSON, JSON with extra fields, malformed output, code fences, and markdown-wrapped JSON.
- B4: Add a fallback parse that includes a growth step: attempt with function-calling or model-profile-based parsing, then fallback to heuristic extraction but log as an error and keep raw content for diagnostics.

Owner: Core LLM integration team (1–2 devs)

Acceptance Criteria:
- All agent planning and analysis code uses typed schemas and tests cover parsing success and failure modes.
- For unsupported models (no structured output), the code logs a clear parse error containing the raw LLM response and returns a parse error state rather than silently continuing.

Workstream C — Parallelize & Budget Context Gathering (Performance / Cost)
-------------------------------------------------------------------------
Summary: Parallelize context gatherers with bounded concurrency, add a session-level cost accumulator, and enforce `settings.llm.max_cost_per_review`.

Tasks:
- C1: Add concurrency controls via `asyncio.Semaphore` owned by PRReviewState or AgentFactory settings; default concurrency = `context_agent_budget`.
- C2: Replace serial `for req in ...` loops with `asyncio.gather(*tasks)` that respects the semaphore. Track per-context token usage and cost from LLM summaries/tools.
- C3: Add a cost accumulator object to `PRReviewState` to enforce `settings.llm.max_cost_per_review`. Tests should mock costs to exceed budgets and assert behavior (abort or partial report with `cost_limit_hit`).

Owner: Performance / platform team (1–2 devs)

Acceptance Criteria:
- `_spawn_context_agents` runs concurrent requests up to the configured concurrency; tests validate concurrency limits and a behavior change when budget exceeded.

Workstream D — Tool Registry & MCP Capability Resolution (Design & Refactor)
-----------------------------------------------------------------------
Summary: Replace ad hoc `_resolve_mcp_tool` semantics and prefix matching with a registry where tools are registered with a capability tag (e.g., `search`, `read`, `symbol`, `blame`), enabling safer tool selection and fallback.

Tasks:
- D1: Add a `ToolRegistry` class that maps `capability -> [tools]`. Populate using `MCPToolProvider.get_tools()` and tool metadata. (Files: `src/multiagentpanic/tools/mcp_tools.py`, new `tool_registry.py`)
- D2: Rewrite `_resolve_mcp_tool` or replace with `tool_registry.get_tool(capability, filter=...)` to return the best tool for a capability with optional fallback. Remove string prefix matching in the factory code.
- D3: Add tests to validate registry resolution and fallback logic.

Owner: Tooling team (1–2 devs)

Acceptance Criteria:
- Tool resolution is capability-based and tests ensure correct fallback and selection behavior.

Workstream E — Dependency Audit & LangChain 1.x Migration (Platform)
-------------------------------------------------------------------
Summary: Run SCA, update pinned versions, and create a migration plan for LangChain and related libraries to 1.x.

Tasks:
- E1: Run `pip-audit` and/or use GitHub Dependabot and action job to flag insecure dependencies; create issues for packages with advisories.
- E2: Create a migration branch and test matrix for LangChain 1.x / LangGraph 1.0 / provider SDK upgrades (OpenAI 2.x, LangChain 1.x changes). Update usage to `llm.with_structured_output`, model profile usage, structured middleware features.
- E3: Add CI job(s) to test against: (a) base dependency set, (b) LangChain 1.x variant.

Owner: Platform & QA team (2 devs)

Acceptance Criteria:
- SCA is active and PRs are created for critical/medium advisories.
- A validated plan for upgrading to LangChain 1.x and needed code changes is available.

Workstream Z — Safety & Observability improvements
-------------------------------------------------
Summary: Add cost & token metrics, and ensure Langfuse & Prometheus capture per-agent & per-model metrics.

Tasks:
- Z1: Add dashboard templates and metrics (per-agent-token-usage, per-review-cost, per-context-latency).
- Z2: Add test coverage and integration tests for budget enforcement.

Owner: Observability/Platform (1 dev)

Acceptance Criteria:
- Metric coverage for LLM cost & tokens is complete and dashboards exist for observability.

Transition plan & next steps (first 7 days)
----------------------------------------
Day 1: Implement Async Fix & small smoke tests (A1–A3). Add a CI job to run tests in an async environment (pytest-asyncio).
Day 2–3: Implement Structured Output for `_review_agent_plan` & `_review_agent_analyze` (B1–B4) and add parsing tests.
Day 4: Implement Parallelization & Budget enforcement (C1–C3) and unit/integration tests for budget logic.
Day 5: Start Tool Registry (D1–D3) and make it optional via a feature flag—keep current behavior until registry passes tests.
Day 6: Run SCA & start LangChain 1.x compatibility plan (E1–E3).
Day 7: Observability improvements (Z1–Z2), create dashboards and ensure metrics are tracked.

Risks & mitigations
-------------------
- Upgrading LangChain may require significant changes; minimize risk by pinning to a specific minor and test thoroughly.
- Removing `asyncio.run` could break sync callers; add a shims layer with deprecation messages for the sync interface.
- Budget enforcement may cause incomplete reviews; add a graceful fallback reporting mechanism to surface `cost_limit_hit` to the PR reviewer.

Acceptance & Sign-off
---------------------
This plan is ready for implementation. Once core PRs are created for the workstreams and pass CI, update this plan with PR links and status.

---

Appendix: Useful references & code locations
- `src/multiagentpanic/factory/agent_factory.py` — core review agent subgraph + _spawn_context_agents + LLM parse logic
- `src/multiagentpanic/tools/mcp_tools.py` — MCP provider & tool discovery
- `src/multiagentpanic/tools/git.py` — git tool and async bridging
- `src/multiagentpanic/observability/config.py` — metrics and Langfuse

---

If you approve this plan I can: 1) create individual issues and PRs for Priority #1 then #2, 2) implement Priority #1 with tests and open a draft PR, or 3) implement Priority #2 and open a draft PR with tests. Pick one to start.

