#!/usr/bin/env python3
import os
import json
import httpx
import sys
from datetime import datetime

# Override per repo when copying the template
SERVICE_NAME = os.getenv("SERVICE_NAME", "your-service-name")


def gather_diagnostics():
    """Gather telemetry configuration diagnostics"""
    return {
        "service_name": SERVICE_NAME,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "langsmith_configured": os.getenv("LANGSMITH_API_KEY") is not None,
        "logfire_configured": os.getenv("LOGFIRE_TOKEN") is not None,
        "otel_exporter_otlp_endpoint": os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "NOT_SET"),
        "deployment_environment": os.getenv("DEPLOYMENT_ENVIRONMENT", "dev"),
    }


def main():
    diagnostics = gather_diagnostics()

    # Optional: push diagnostics to central dashboard
    central_url = os.getenv("OBS_CONTROL_URL")  # e.g. http://your-lab:5555
    if central_url:
        try:
            httpx.post(
                f"{central_url}/api/telemetry-report",
                json=diagnostics,
                timeout=2.0,
            )
            print(f"Reported to central: {central_url}")
        except Exception as e:
            print(f"WARNING: failed to report to central: {e}", file=sys.stderr)

    print(json.dumps(diagnostics, indent=2))


if __name__ == "__main__":
    main()
