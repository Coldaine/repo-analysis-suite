---
doc_type: reference
subsystem: agents/workflow
domain_code: wf
version: 1.0.0
status: draft
owners: pmacl
last_reviewed: 2025-12-03
---

# Workflow Agent Domain

Singleton agent that handles CI/CD operations.

## Responsibilities

- CI runner management
- Test execution
- Queue management with deduplication
- GitHub Actions integration

## Characteristics

- **Singleton**: Only one instance across all reviews
- **Shared queue**: Multiple review agents can request CI runs
- **Deduplication**: Prevents redundant test executions

## Code Location

`agentreview/agents/workflow.py`

## Related Documentation

- [System Design](../../../architecture/system-design.md) - Workflow agent role
- [Testing Guide](../../../guides/testing.md) - Test execution details
