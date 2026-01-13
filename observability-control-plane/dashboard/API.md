# Dashboard API Documentation

## Base URL
`http://localhost:5555`

## Endpoints

### GET /health
Health check endpoint for monitoring.

**Response (200 OK)**:
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

**Status Codes**:
- `200`: Service is healthy or degraded (warning state)
- `503`: Service is unhealthy (one or more critical checks failed)

---

### POST /api/telemetry-report
Receive telemetry reports from per-app agents.

**Request Body**:
```json
{
  "service_name": "my-service",
  "timestamp": "2025-01-01T00:00:00Z",
  "langsmith_configured": true,
  "logfire_configured": false,
  "otel_exporter_otlp_endpoint": "http://collector:4318",
  "deployment_environment": "production"
}
```

**Response (200 OK)**:
```json
{
  "status": "received",
  "service": "my-service",
  "issues": ["Logfire not configured"],
  "recommendation": "Fix configuration issues"
}
```

**Error Response (400 Bad Request)**:
```json
{
  "error": "No data provided"
}
```

**Notes**:
- The endpoint validates telemetry configuration and identifies missing components
- Reports are stored in the memory system for historical analysis
- Issues are automatically detected based on configuration state

---

### GET /api/agents
Get all registered agents.

**Response (200 OK)**:
```json
{
  "agents": [
    {
      "name": "obs-agent-1",
      "status": "active",
      "server": "prod-server-1",
      "last_seen": "2025-01-01T00:00:00Z"
    }
  ]
}
```

**Error Response (500 Internal Server Error)**:
```json
{
  "error": "Error message",
  "agents": []
}
```

**Notes**:
- Returns empty array if no agents are registered
- Timestamps are converted to ISO 8601 format
- Agents are sorted by last_seen (most recent first)

---

### POST /api/register-agent
Register a new agent or update an existing one.

**Request Body**:
```json
{
  "name": "obs-agent-1",
  "server": "prod-server-1"
}
```

**Response (201 Created)**:
```json
{
  "status": "registered",
  "name": "obs-agent-1",
  "server": "prod-server-1"
}
```

**Error Response (400 Bad Request)**:
```json
{
  "error": "Agent name is required"
}
```

**Error Response (500 Internal Server Error)**:
```json
{
  "error": "Failed to register agent"
}
```

**Notes**:
- If an agent with the same name exists, it will be updated
- The `last_seen` timestamp is automatically set to current time
- Agent status is set to "active" by default

---

### GET /api/fixes
Get recent fixes with optional pagination.

**Query Parameters**:
- `limit` (int, optional): Number of fixes to return (default: 20, max: 100)

**Example**: `GET /api/fixes?limit=5`

**Response (200 OK)**:
```json
{
  "fixes": [
    {
      "issue": "Container down",
      "solution": "Restarted container",
      "timestamp": 1704067200000,
      "success": true
    }
  ],
  "count": 1,
  "limit": 20
}
```

**Error Response (500 Internal Server Error)**:
```json
{
  "error": "Error message",
  "fixes": []
}
```

**Notes**:
- Fixes are ordered by timestamp (most recent first)
- Returns empty array if no fixes are found
- Timestamp is in milliseconds since epoch

---

### GET /api/metrics
Get Prometheus-compatible metrics for monitoring.

**Response (200 OK)**:
```
# HELP dashboard_disk_usage_bytes Disk usage in bytes
# TYPE dashboard_disk_usage_bytes gauge
dashboard_disk_usage_bytes 54321000000

# HELP dashboard_disk_total_bytes Total disk space in bytes
# TYPE dashboard_disk_total_bytes gauge
dashboard_disk_total_bytes 100000000000

# HELP dashboard_memory_usage_bytes Memory usage in bytes
# TYPE dashboard_memory_usage_bytes gauge
dashboard_memory_usage_bytes 8589934592

# HELP dashboard_cpu_usage_percent CPU usage percentage
# TYPE dashboard_cpu_usage_percent gauge
dashboard_cpu_usage_percent 45.2

# HELP dashboard_agents_total Number of registered agents
# TYPE dashboard_agents_total gauge
dashboard_agents_total 3
```

**Content-Type**: `text/plain`

**Notes**:
- Metrics are in Prometheus exposition format
- Can be scraped by Prometheus or compatible monitoring systems
- System metrics (CPU, memory, disk) are collected in real-time
- Agent count metric may be omitted if database is unavailable

---

### GET /api/state
Get current observability control plane state.

**Response (200 OK)**:
```json
{
  "agents": [],
  "recent_fixes": ["fix1", "fix2"],
  "disk_usage": "Disk Usage:\n  Total: 100.00 GB\n  Used:  45.00 GB (45%)\n  Free:  55.00 GB",
  "last_check": "2025-01-01T00:00:00Z"
}
```

**Notes**:
- This is the original endpoint used by the dashboard UI
- Returns comprehensive state information
- Used by obs_agent.py to build prompts

---

## Error Handling

All endpoints follow consistent error handling:

### 404 Not Found
```json
{
  "error": "Endpoint not found"
}
```

### 500 Internal Server Error
```json
{
  "error": "Internal server error"
}
```

### General Error Response Format
All error responses include an `error` field with a descriptive message.

---

## Request Logging

All requests are logged with the following format:
```
2025-01-01 00:00:00,000 - INFO - POST /api/telemetry-report from 192.168.1.100
```

Includes:
- HTTP method
- Request path
- Client IP address

---

## Authentication

Currently, no authentication is required for any endpoints. This is suitable for internal lab/development environments only.

**Security Recommendations**:
- Add API key authentication for production use
- Implement rate limiting for public-facing deployments
- Use HTTPS/TLS for production traffic
- Restrict network access via firewall rules

---

## Rate Limiting

Currently, no rate limiting is implemented. Consider adding rate limiting for production deployments.

---

## CORS

CORS is not configured by default. Add Flask-CORS if you need to access these endpoints from browser-based applications on different origins.

---

## Testing

See `test_endpoints.py` for example usage of all endpoints.

Run tests with:
```bash
python dashboard/test_endpoints.py
```

Ensure the dashboard is running on `localhost:5555` before running tests.
