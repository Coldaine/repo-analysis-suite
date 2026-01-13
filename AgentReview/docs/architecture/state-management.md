---
doc_type: architecture
subsystem: state
version: 1.0.0
status: draft
owners: pmacl
last_reviewed: 2025-12-03
---

# State Management

Pydantic-based state management with operator-driven accumulation, PostgreSQL checkpointing, and Redis caching.

---

## Table of Contents

- [State Schemas](#state-schemas)
- [State Accumulation](#state-accumulation)
- [Checkpoint Strategy](#checkpoint-strategy)
- [Context Caching](#context-caching)
- [Workflow Queue](#workflow-queue)

---

## State Schemas

### Core Models

| Model | Purpose |
|-------|---------|
| `PRReviewState` | Main state for review workflow |
| `ReviewAgentState` | Per-agent state with findings |
| `ContextAgentState` | Minimal state for context gathering |
| `WorkflowAgentState` | Singleton queue state |
| `Finding` | Individual review finding |
| `AgentMetrics` | Metrics for cost/latency tracking |

See [State Domain Documentation](../domains/state/st-overview.md) for full schemas.

---

## State Accumulation

LangGraph uses Python operators for automatic state merging:

```python
class PRReviewState(BaseModel):
    # Lists concatenate via operator.add
    findings: Annotated[list[Finding], operator.add]

    # Dicts merge via operator.or_
    context: Annotated[dict[str, str], operator.or_]

    # No operator: last write wins
    round_number: int
```

---

## Checkpoint Strategy

### PostgreSQL Checkpointer

- Review agents checkpoint after each step
- Context agents don't checkpoint (stateless)
- Thread ID: `{repository}:pr-{pr_number}`
- Enables resumption after failures

### Retention

- Keep last 10 checkpoints per thread
- TTL: 30 days

---

## Context Caching

### Redis Cache

| Context Type | TTL | Reason |
|--------------|-----|--------|
| Zoekt | 5 min | Code changes frequently |
| LSP | 10 min | Symbols more stable |
| Git | 1 hour | History doesn't change |

Cache key: `context:{type}:{query_hash}`

---

## Workflow Queue

Redis-based queue with deduplication:

1. Multiple agents can request same CI run
2. Queue deduplicates by `{type}:{pr}:{checks}`
3. Result broadcast to all subscribers via pub/sub

See [Workflow Domain Documentation](../domains/agents/workflow/wf-overview.md) for queue implementation.
