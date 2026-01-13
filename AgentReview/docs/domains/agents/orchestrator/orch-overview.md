---
doc_type: reference
subsystem: agents/orchestrator
domain_code: orch
version: 1.1.0
status: draft
owners: pmacl
last_reviewed: 2025-01-13
---

# Orchestrator Domain

The orchestrator is the entry point and decision maker for PR reviews.

## Responsibilities

- Receives PR webhooks from GitHub
- Analyzes PR metadata (size, files changed, labels)
- Decides review strategy (which agents, how many rounds)
- Spawns review agents in parallel
- Collects and synthesizes findings
- Decides when to proceed to healing rounds
- Produces final review summary

## Graph Structure

The orchestrator uses a LangGraph StateGraph with the following flow:

```
load_memory → init_pr → plan_agents → run_review_agents → collect → END
```

### Nodes

| Node | Purpose |
|------|---------|
| `load_memory` | Load cross-PR learning data (repo_memory, similar_prs, repo_conventions) |
| `init_pr` | Initialize PR state with metadata and diff |
| `plan_agents` | Decide which review agents to spawn |
| `run_review_agents` | Execute review agent subgraphs in parallel |
| `collect` | Aggregate reports, determine overall verdict |

### Cross-PR Learning

The `load_memory` node enables learning across PRs by loading:

- **repo_memory**: Historical patterns, common issues, learned heuristics
- **similar_prs**: Previously reviewed PRs with similar characteristics
- **repo_conventions**: Repository-specific coding conventions

This data helps agents make more informed decisions based on past reviews.

## Code Location

`src/multiagentpanic/agents/orchestrator.py`

## Key Methods

- `build_graph()` - Constructs the LangGraph workflow
- `load_memory()` - Cross-PR learning data loader
- `init_pr()` - PR state initialization
- `plan_agents()` - Agent selection logic
- `run_review_agents()` - Subgraph execution
- `collect()` - Result aggregation
- `run()` - Main entry point

## Related Documentation

- [System Design](../../../architecture/system-design.md) - Overall architecture
- [Agent Factory](../../../architecture/agent-factory.md) - How agents are created
- [State Management](../../../architecture/state-management.md) - State flow
