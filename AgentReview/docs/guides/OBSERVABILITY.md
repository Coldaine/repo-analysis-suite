# Observability

Self-hosted observability stack using Langfuse for LLM tracing, Prometheus for metrics, Grafana for visualization, Tempo for distributed tracing, and Loki for logs.

## Stack Overview

- **Langfuse**: LLM-specific tracing, cost tracking, prompt analysis
- **Prometheus**: Time-series metrics collection and storage
- **Grafana**: Unified visualization and alerting
- **Tempo**: Distributed tracing for request flows
- **Loki**: Log aggregation and querying
- **Promtail**: Log collection agent

## Setup

See [`docker-compose.observability.yml`](../../docker-compose.observability.yml) for the complete stack definition.

## Implementation

See [`src/multiagentpanic/observability`](../../src/multiagentpanic/observability) for the integration code.
