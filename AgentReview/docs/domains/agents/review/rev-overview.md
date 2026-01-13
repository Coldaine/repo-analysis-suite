---
doc_type: reference
subsystem: agents/review
domain_code: rev
version: 1.0.0
status: draft
owners: pmacl
last_reviewed: 2025-12-03
---

# Review Agents Domain

Four specialized review agents that analyze code with domain expertise.

## Agent Types

| Agent | Focus |
|-------|-------|
| Alignment | Requirements & design alignment |
| Dependencies | Imports, versions, compatibility |
| Testing | Coverage & test quality |
| Security | Vulnerabilities & secrets |

## Characteristics

- **Persistent**: Accumulate context across healing rounds
- **Parallel**: All 4 run simultaneously in each round
- **Can spawn**: Create context agents for additional information

## Code Location

`agentreview/agents/review/`

## Domain Documents

- `rev-alignment.md` - Alignment agent details (TODO)
- `rev-dependencies.md` - Dependencies agent details (TODO)
- `rev-testing.md` - Testing agent details (TODO)
- `rev-security.md` - Security agent details (TODO)

## Related Documentation

- [System Design](../../../architecture/system-design.md) - Agent hierarchy
- [Context Agents](../context/ctx-overview.md) - Agents spawned by review agents
