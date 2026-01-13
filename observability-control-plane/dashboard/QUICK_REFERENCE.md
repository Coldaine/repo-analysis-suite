# Dashboard API Quick Reference

## Starting the Dashboard

```bash
# From project root
cd dashboard
python app.py

# Or via Docker Compose
docker compose up dashboard
```

Dashboard will be available at: `http://localhost:5555`

## Quick Test Commands

### 1. Health Check
```bash
curl http://localhost:5555/health | jq
```

### 2. Submit Telemetry Report
```bash
curl -X POST http://localhost:5555/api/telemetry-report \
  -H "Content-Type: application/json" \
  -d '{
    "service_name": "my-app",
    "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
    "langsmith_configured": true,
    "logfire_configured": false,
    "otel_exporter_otlp_endpoint": "http://collector:4318",
    "deployment_environment": "production"
  }' | jq
```

### 3. Register Agent
```bash
curl -X POST http://localhost:5555/api/register-agent \
  -H "Content-Type: application/json" \
  -d '{
    "name": "obs-agent-1",
    "server": "prod-server-1"
  }' | jq
```

### 4. Get All Agents
```bash
curl http://localhost:5555/api/agents | jq
```

### 5. Get Recent Fixes
```bash
# Default (20 fixes)
curl http://localhost:5555/api/fixes | jq

# Limited to 5 fixes
curl "http://localhost:5555/api/fixes?limit=5" | jq
```

### 6. Get Prometheus Metrics
```bash
curl http://localhost:5555/api/metrics
```

### 7. Get System State
```bash
curl http://localhost:5555/api/state | jq
```

## Running Tests

```bash
# Make sure dashboard is running first
cd dashboard
python app.py

# In another terminal
python dashboard/test_endpoints.py
```

Expected output:
```
============================================================
DASHBOARD API ENDPOINT TESTS
Target: http://localhost:5555
============================================================

✓ Health Check: PASS
✓ Telemetry Report: PASS
✓ Register Agent: PASS
✓ Get Agents: PASS
✓ Get Recent Fixes: PASS
✓ Get Metrics: PASS
✓ API State: PASS
✓ 404 Error Handling: PASS
============================================================
Total: 8/8 tests passed
============================================================
```

## Environment Variables

```bash
# Neo4j connection (required for full functionality)
export NEO4J_PASSWORD="your-password"
export NEO4J_URI="bolt://localhost:7687"

# Dashboard configuration
export DASHBOARD_PORT=5555
export DASHBOARD_HOST=0.0.0.0
```

## Common Response Formats

### Success Response (200/201)
```json
{
  "status": "success",
  "data": { /* ... */ }
}
```

### Error Response (4xx/5xx)
```json
{
  "error": "Error description"
}
```

### Health Response
```json
{
  "status": "healthy|degraded|unhealthy",
  "timestamp": "2025-01-01T00:00:00Z",
  "checks": {
    "disk": {"status": "ok", "usage_percent": 45.2},
    "memory": {"status": "ok", "usage_percent": 62.1},
    "database": {"status": "ok", "connected": true}
  }
}
```

## Integration Examples

### Python (using httpx)
```python
import httpx

# Submit telemetry
response = httpx.post(
    "http://localhost:5555/api/telemetry-report",
    json={
        "service_name": "my-service",
        "langsmith_configured": True,
        "logfire_configured": False,
        "otel_exporter_otlp_endpoint": "http://collector:4318"
    }
)
print(response.json())
```

### Bash Script
```bash
#!/bin/bash
# Monitor dashboard health
while true; do
  status=$(curl -s http://localhost:5555/health | jq -r '.status')
  echo "Dashboard status: $status"
  if [ "$status" != "healthy" ]; then
    echo "WARNING: Dashboard is $status"
  fi
  sleep 60
done
```

### Prometheus Configuration
```yaml
scrape_configs:
  - job_name: 'observability-dashboard'
    static_configs:
      - targets: ['localhost:5555']
    metrics_path: '/api/metrics'
    scrape_interval: 15s
```

## Troubleshooting

### Dashboard Won't Start
```bash
# Check if port is already in use
netstat -an | grep 5555

# Try different port
export DASHBOARD_PORT=8080
python dashboard/app.py
```

### Empty Responses
```bash
# Check Neo4j is running
docker compose ps neo4j

# Check Neo4j password is set
echo $NEO4J_PASSWORD

# Test database connection
python -c "from py2neo import Graph; g = Graph('bolt://localhost:7687', auth=('neo4j', 'password')); print(g.run('RETURN 1').data())"
```

### Import Errors
```bash
# Ensure you're in the right directory
pwd  # Should end in /dashboard

# Or run from project root with PYTHONPATH
export PYTHONPATH=/path/to/observability-implementation-package
python dashboard/app.py
```

## Monitoring Dashboard Logs

```bash
# If running with Docker Compose
docker compose logs -f dashboard

# If running directly
# Logs will appear in the terminal where you ran python app.py
```

## Performance Tips

1. **Use pagination** for large datasets:
   ```bash
   curl "http://localhost:5555/api/fixes?limit=10"
   ```

2. **Cache health checks** in monitoring scripts:
   ```bash
   # Check every 60s, not every second
   watch -n 60 'curl -s http://localhost:5555/health | jq .status'
   ```

3. **Use connection pooling** in production clients

## Security Checklist

- [ ] Neo4j password is set and secure
- [ ] Dashboard is not exposed to public internet (internal use only)
- [ ] Firewall rules restrict access to trusted networks
- [ ] Consider adding authentication for production
- [ ] Enable HTTPS if deploying outside localhost

## See Also

- [API.md](./API.md) - Complete API documentation
- [test_endpoints.py](./test_endpoints.py) - Test suite source code
- [../IMPLEMENTATION_SUMMARY.md](../IMPLEMENTATION_SUMMARY.md) - Implementation details
