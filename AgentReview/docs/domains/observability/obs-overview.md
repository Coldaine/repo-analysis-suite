---
doc_type: reference
subsystem: observability
domain_code: obs
version: 1.0.0
status: draft
owners: pmacl
last_reviewed: 2025-12-03
---

# Observability Domain

Metrics, tracing, and monitoring infrastructure.

## Stack

| Component | Purpose |
|-----------|---------|
| Langfuse | LLM tracing (self-hosted) |
| Prometheus | Metrics collection |
| Grafana | Visualization |
| Tempo | Distributed tracing |
| Loki | Log aggregation |

## Custom Metrics

- `agent_spawns_total` - Agent creation count
- `review_cost_dollars` - Cost per review
- `review_latency_seconds` - Review duration
- `llm_tokens_used` - Token consumption

## Code Location

`agentreview/observability/`

## Domain Documents

- `obs-metrics.md` - Metric definitions (TODO)
- `obs-dashboards.md` - Grafana dashboard configs (TODO)

## Related Documentation

- [Observability Guide](../../guides/observability.md) - Setup and usage
- [Configuration](../../guides/configuration.md) - Environment variables
