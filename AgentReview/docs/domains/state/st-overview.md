---
doc_type: reference
subsystem: state
domain_code: st
version: 1.0.0
status: draft
owners: pmacl
last_reviewed: 2025-12-12
version: 1.1.0
status: active
---

# State Domain

State management, persistence, and caching.

## Components

| Component | Purpose |
|-----------|---------|
| `models.py` | Pydantic state models |
| `checkpointing.py` | PostgreSQL checkpoint saver |

## State Models

- `PRReviewState` - Top-level review state
- `ReviewAgentState` - Per-agent state
- `ContextAgentState` - Context agent state
- `WorkflowAgentState` - Workflow queue state

## Infrastructure

- **PostgreSQL**: Durable checkpoints
- **Redis**: Fast caching, TTL support

## Code Location

`agentreview/state/`

## Domain Documents

- `st-checkpointing.md` - Checkpoint strategy (see [State Management Architecture](../../architecture/state-management.md))
- `st-caching.md` - Redis caching patterns (see [Redis Cache section in State Management](../../architecture/state-management.md))

## Implementation Notes

### Checkpoint Strategy
- Review agents checkpoint after each step using PostgreSQL
- Context agents are stateless (no checkpointing)
- Thread ID format: `{repository}:pr-{pr_number}`
- Retention: Keep last 10 checkpoints per thread, TTL: 30 days

### Caching Patterns
Redis caching implemented with context-specific TTLs:
- **Zoekt search results**: 5 minutes (code changes frequently)
- **LSP analysis**: 10 minutes (symbols more stable)
- **Git history**: 1 hour (history doesn't change)
- Cache key format: `context:{type}:{query_hash}`

### State Accumulation
LangGraph uses Python operators for automatic state merging:
- Lists concatenate via `operator.add`
- Dicts merge via `operator.or_`
- No operator: last write wins

## Related Documentation

- [State Management Architecture](../../architecture/state-management.md) - Design details
- [Configuration](../../guides/configuration.md) - Database setup
