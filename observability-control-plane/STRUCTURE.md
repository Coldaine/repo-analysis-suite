# Hybrid Observability Implementation Package Structure

This document defines the complete directory and artifact layout for the implementation package. It is the contract that other modes (Code, Debug, etc.) and engineers should rely on.

All paths below are relative to: ./observability-implementation-package

## Top-Level

- README.md
- STRUCTURE.md
- _repo_plan/ (reference to existing reports at project root; not duplicated)

## 1. Configuration

### 1.1 OpenTelemetry Collector

- config-otel/
  - base/
    - otel-collector-base.yaml
    - otel-attributes-resource-template.yaml
    - otel-sampling-strategy-template.yaml
  - env/
    - dev/otel-collector-dev.yaml
    - staging/otel-collector-staging.yaml
    - prod/otel-collector-prod.yaml
  - topologies/
    - sidecar-agent.yaml
    - gateway.yaml
    - hybrid-gateway-plus-agent.yaml
  - exporters/
    - exporters-grafana-cloud.yaml
    - exporters-lgtm.yaml
    - exporters-langsmith.yaml
    - exporters-logfire.yaml
  - receivers/
    - receivers-http-grpc.yaml
    - receivers-otlp-mixed.yaml
    - receivers-prometheus.yaml
    - receivers-logging.yaml

### 1.2 LGTM Stack

- config-lgtm/
  - local-docker-compose/
    - docker-compose.lgtm.yml
  - kubernetes/
    - loki/
      - loki-config.yaml
      - loki-statefulset.yaml
    - tempo/
      - tempo-config.yaml
      - tempo-deployment.yaml
    - mimir-or-prometheus/
      - mimir-config.yaml
      - mimir-deployment.yaml
      - prometheus-config.yaml
      - prometheus-deployment.yaml
    - grafana/
      - grafana-config.yaml
      - grafana-deployment.yaml
    - ingress/
      - lgtm-ingress.yaml

### 1.3 Integration Config Templates

- config-integrations/
  - shared/
    - env-conventions.md
    - service-naming-and-resources.md
  - python/
    - otel-python-bootstrap-template.md
    - otel-python-auto-instrumentation-example.py
    - otel-python-manual-sdk-snippet.py
  - typescript-js/
    - otel-node-bootstrap-template.md
    - otel-node-sdk-example.ts
    - otel-browser-example.ts
  - rust/
    - otel-rust-bootstrap-template.md
    - otel-rust-tracing-layer-example.rs
  - external-services/
    - grafana-cloud-metrics-logs-traces.md
    - langsmith-integration-template.md
    - logfire-integration-template.md

## 2. Documentation

- docs/
  - architecture-overview.md
  - standards-and-conventions.md
  - resource-attributes-and-naming.md
  - sampling-strategy.md
  - retention-and-cost-guardrails.md
  - security-and-api-keys.md
  - integration-guides/
    - python-integration-guide.md
    - ts-js-integration-guide.md
    - rust-integration-guide.md
    - repo-onboarding-playbook.md
    - lgtm-and-grafana-cloud-routing.md
    - langsmith-and-logfire-usage.md

## 3. Deployment Playbooks

- deploy/
  - local/
    - README.md
    - docker-compose.otel-plus-lgtm.yml
    - bootstrap-local-env.ps1
    - bootstrap-local-env.sh
  - cloud/
    - README.md
    - terraform-stub.md
    - vm-docker-compose.yml
    - systemd-units.md
  - kubernetes/
    - README.md
    - base/
      - otel-collector-daemonset.yaml
      - otel-collector-gateway.yaml
      - lgtm-namespace.yaml
    - overlays/
      - dev/
        - kustomization.yaml
      - staging/
        - kustomization.yaml
      - prod/
        - kustomization.yaml

## 4. Operations and Runbooks

- ops/
  - operations-manual.md
  - runbooks/
    - collector-outage.md
    - lgtm-degradation.md
    - grafana-cloud-slo-breach.md
    - langsmith-logfire-issues.md
  - alerts-and-slos.md
  - maintenance-tasks.md
  - upgrade-and-rollback.md
  - cost-monitoring-and-budgets.md

## 5. Quality Assurance and Validation

- qa/
  - implementation-checklist.md
  - validation-playbook.md
  - e2e-test-scenarios.md
  - performance-benchmarking.md
  - optimization-guide.md
  - troubleshooting-guide.md
  - common-issues.md

## 6. Scripts and Automation

- scripts/
  - validate-connectivity.sh
  - validate-connectivity.ps1
  - send-test-trace.sh
  - send-test-trace.ps1
  - send-test-metric.sh
  - send-test-metric.ps1
  - send-test-log.sh
  - send-test-log.ps1
  - repo-onboarding-helper.md

## Usage Notes

- This structure is intentionally verbose to ensure a single engineer can:
  - Discover the right file for any concern.
  - Copy-paste working templates into each target repo.
  - Follow documented playbooks with minimal ambiguity.
- All language constructs, scripts, and manifest paths referenced here will be provided as concrete templates in subsequent files.