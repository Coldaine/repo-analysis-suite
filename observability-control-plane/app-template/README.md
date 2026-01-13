# Application Telemetry Template

This template provides per-service telemetry validation for the observability control plane.

## Usage

1. **Copy this template** to your application repository:
   ```bash
   cp -r app-template /path/to/your-app/observability
   ```

2. **Configure environment variables** in your app's `.env`:
   ```bash
   SERVICE_NAME=your-service-name
   OBS_CONTROL_URL=http://central-dashboard:5555

   # Telemetry providers
   LANGSMITH_API_KEY=your-key
   LOGFIRE_TOKEN=your-token
   OTEL_EXPORTER_OTLP_ENDPOINT=http://collector:4318
   DEPLOYMENT_ENVIRONMENT=dev
   ```

3. **Run the telemetry agent**:
   ```bash
   python observability/scripts/telemetry_agent.py
   ```

4. **Automate checks** (optional):
   Add to your CI/CD pipeline:
   ```yaml
   # .github/workflows/telemetry-check.yml
   - name: Validate Telemetry Config
     run: python observability/scripts/telemetry_agent.py
   ```

## Customization

- Edit `prompts/telemetry-agent.md` to adjust validation rules
- Modify `scripts/telemetry_agent.py` to add service-specific checks
- Integrate with your service's health check endpoints
