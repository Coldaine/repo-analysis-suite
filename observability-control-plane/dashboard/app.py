import sys
import os
# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, jsonify, request
from flask_htmx import HTMX
from memori import recall
from scripts.agent_memory import (
    get_recent_fixes,
    get_all_agents,
    register_agent,
    remember
)
from datetime import datetime
import psutil
import logging

app = Flask(__name__)
htmx = HTMX(app)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ===== ERROR HANDLERS =====

@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors with JSON response"""
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(e):
    """Handle 500 errors with JSON response"""
    logger.error(f"Internal server error: {e}")
    return jsonify({"error": "Internal server error"}), 500


@app.before_request
def log_request():
    """Log all incoming requests"""
    logger.info(f"{request.method} {request.path} from {request.remote_addr}")


# ===== HELPER FUNCTIONS =====

def _system_disk_usage() -> str:
    """
    Get cross-platform disk usage using psutil.
    """
    try:
        # Get disk usage for root/C: drive
        disk = psutil.disk_usage('/')
        total_gb = disk.total / (1024**3)
        used_gb = disk.used / (1024**3)
        free_gb = disk.free / (1024**3)

        return (
            f"Disk Usage:\n"
            f"  Total: {total_gb:.2f} GB\n"
            f"  Used:  {used_gb:.2f} GB ({disk.percent}%)\n"
            f"  Free:  {free_gb:.2f} GB"
        )
    except Exception as e:
        return f"ERROR: {e}"


@app.route("/")
def index():
    """
    Render single-pane dashboard.
    """
    state_resp = api_state()
    state = state_resp.get_json()
    return render_template("index.html", **state)


@app.route("/api/state")
def api_state():
    """
    Return current observability-control plane state as JSON.
    Queries Neo4j for agents and recent fixes.
    """
    disk_usage = _system_disk_usage()

    # Query agents from Neo4j
    try:
        agents = get_all_agents()
        # Format timestamps
        for agent in agents:
            if 'last_seen' in agent and agent['last_seen']:
                try:
                    agent['last_seen'] = datetime.fromtimestamp(
                        agent['last_seen'] / 1000
                    ).isoformat() + "Z"
                except:
                    agent['last_seen'] = "unknown"
    except Exception as e:
        logger.error(f"Failed to get agents: {e}")
        agents = []

    # Get recent fixes from Neo4j
    try:
        recent_fixes_data = get_recent_fixes(limit=20)
        # Format for display
        recent_fixes = []
        for fix in recent_fixes_data:
            timestamp = fix.get('timestamp', 0)
            try:
                ts_str = datetime.fromtimestamp(timestamp / 1000).strftime("%Y-%m-%d %H:%M:%S")
            except:
                ts_str = "unknown"

            fix_str = f"{fix.get('issue', 'Unknown')} -> {fix.get('solution', 'Unknown')} ({ts_str})"
            recent_fixes.append(fix_str)

    except Exception as e:
        logger.error(f"Failed to get recent fixes: {e}")
        recent_fixes = [f"ERROR: Unable to fetch recent fixes: {e}"]

    last_check = datetime.utcnow().isoformat() + "Z"

    payload = {
        "agents": agents,
        "recent_fixes": recent_fixes,
        "disk_usage": disk_usage,
        "last_check": last_check,
    }
    return jsonify(payload)


# ===== NEW API ENDPOINTS =====

@app.route("/api/telemetry-report", methods=["POST"])
def telemetry_report():
    """
    Receive telemetry reports from per-app agents.
    Expected payload:
    {
        "service_name": "my-service",
        "timestamp": "2025-01-01T00:00:00Z",
        "langsmith_configured": true,
        "logfire_configured": false,
        "otel_exporter_otlp_endpoint": "http://collector:4318",
        "deployment_environment": "production"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        service_name = data.get("service_name", "unknown")
        timestamp = data.get("timestamp", datetime.utcnow().isoformat() + "Z")

        # Validate telemetry configuration
        issues = []
        if not data.get("langsmith_configured"):
            issues.append("LangSmith not configured")
        if not data.get("logfire_configured"):
            issues.append("Logfire not configured")
        if data.get("otel_exporter_otlp_endpoint") == "NOT_SET":
            issues.append("OTLP endpoint not configured")

        # Store telemetry report
        report_content = f"""
        Service: {service_name}
        Timestamp: {timestamp}
        Environment: {data.get('deployment_environment', 'unknown')}
        LangSmith: {data.get('langsmith_configured', False)}
        Logfire: {data.get('logfire_configured', False)}
        OTLP: {data.get('otel_exporter_otlp_endpoint', 'NOT_SET')}
        Issues: {', '.join(issues) if issues else 'None'}
        """

        # Store in memory system
        remember(
            f"telemetry:{service_name}",
            report_content,
            metadata={
                "type": "telemetry",
                "service": service_name,
                "has_issues": len(issues) > 0
            }
        )

        logger.info(f"Telemetry report received from {service_name}")

        # Return validation result
        response = {
            "status": "received",
            "service": service_name,
            "issues": issues,
            "recommendation": "Fix configuration issues" if issues else "Configuration OK"
        }

        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Error processing telemetry report: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/agents", methods=["GET"])
def api_agents():
    """
    Get all registered agents.
    Returns:
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
    """
    try:
        agents = get_all_agents()

        # Format timestamps
        for agent in agents:
            if 'last_seen' in agent and agent['last_seen']:
                # Convert timestamp to ISO format
                agent['last_seen'] = datetime.fromtimestamp(
                    agent['last_seen'] / 1000
                ).isoformat() + "Z"

        return jsonify({"agents": agents}), 200

    except Exception as e:
        logger.error(f"Error fetching agents: {e}")
        return jsonify({"error": str(e), "agents": []}), 500


@app.route("/api/register-agent", methods=["POST"])
def api_register_agent():
    """
    Register a new agent or update existing one.
    Expected payload:
    {
        "name": "obs-agent-1",
        "server": "prod-server-1"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        name = data.get("name")
        server = data.get("server", "unknown")

        if not name:
            return jsonify({"error": "Agent name is required"}), 400

        # Register agent in Neo4j
        success = register_agent(name, server)

        if success:
            logger.info(f"Agent registered: {name} on {server}")
            return jsonify({
                "status": "registered",
                "name": name,
                "server": server
            }), 201
        else:
            return jsonify({"error": "Failed to register agent"}), 500

    except Exception as e:
        logger.error(f"Error registering agent: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    """
    Health check endpoint for monitoring.
    Returns system health status.
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "checks": {}
    }

    # Check disk usage
    try:
        disk = psutil.disk_usage('/')
        health_status["checks"]["disk"] = {
            "status": "ok" if disk.percent < 90 else "warning",
            "usage_percent": disk.percent
        }
    except Exception as e:
        health_status["checks"]["disk"] = {
            "status": "error",
            "error": str(e)
        }

    # Check memory
    try:
        memory = psutil.virtual_memory()
        health_status["checks"]["memory"] = {
            "status": "ok" if memory.percent < 90 else "warning",
            "usage_percent": memory.percent
        }
    except Exception as e:
        health_status["checks"]["memory"] = {
            "status": "error",
            "error": str(e)
        }

    # Check database connectivity (simplified check)
    try:
        # Try to get recent fixes (tests database connection)
        fixes = get_recent_fixes(1)
        health_status["checks"]["database"] = {
            "status": "ok",
            "connected": True
        }
    except Exception as e:
        health_status["checks"]["database"] = {
            "status": "error",
            "connected": False,
            "error": str(e)
        }
        health_status["status"] = "degraded"

    # Determine overall health
    if any(check.get("status") == "error"
           for check in health_status["checks"].values()):
        health_status["status"] = "unhealthy"
        status_code = 503
    elif any(check.get("status") == "warning"
             for check in health_status["checks"].values()):
        health_status["status"] = "degraded"
        status_code = 200
    else:
        status_code = 200

    return jsonify(health_status), status_code


@app.route("/api/fixes", methods=["GET"])
def api_fixes():
    """
    Get recent fixes with pagination support.
    Query params:
    - limit: number of fixes to return (default 20)
    - offset: pagination offset (default 0)
    """
    try:
        limit = request.args.get('limit', 20, type=int)
        # Note: offset would need to be implemented in database_helpers

        fixes = get_recent_fixes(limit)

        # Format fixes for API response
        formatted_fixes = []
        for fix in fixes:
            formatted_fixes.append({
                "issue": fix.get('issue', 'Unknown'),
                "solution": fix.get('solution', 'Unknown'),
                "timestamp": fix.get('timestamp', 0),
                "success": fix.get('success', False)
            })

        return jsonify({
            "fixes": formatted_fixes,
            "count": len(formatted_fixes),
            "limit": limit
        }), 200

    except Exception as e:
        logger.error(f"Error fetching fixes: {e}")
        return jsonify({"error": str(e), "fixes": []}), 500


@app.route("/api/metrics", methods=["GET"])
def api_metrics():
    """
    Get system metrics for monitoring.
    Returns Prometheus-style metrics.
    """
    try:
        # Gather metrics
        disk = psutil.disk_usage('/')
        memory = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=1)

        # Format as Prometheus metrics
        metrics = []
        metrics.append(f"# HELP dashboard_disk_usage_bytes Disk usage in bytes")
        metrics.append(f"# TYPE dashboard_disk_usage_bytes gauge")
        metrics.append(f"dashboard_disk_usage_bytes {disk.used}")

        metrics.append(f"# HELP dashboard_disk_total_bytes Total disk space in bytes")
        metrics.append(f"# TYPE dashboard_disk_total_bytes gauge")
        metrics.append(f"dashboard_disk_total_bytes {disk.total}")

        metrics.append(f"# HELP dashboard_memory_usage_bytes Memory usage in bytes")
        metrics.append(f"# TYPE dashboard_memory_usage_bytes gauge")
        metrics.append(f"dashboard_memory_usage_bytes {memory.used}")

        metrics.append(f"# HELP dashboard_cpu_usage_percent CPU usage percentage")
        metrics.append(f"# TYPE dashboard_cpu_usage_percent gauge")
        metrics.append(f"dashboard_cpu_usage_percent {cpu}")

        # Add application-specific metrics
        try:
            agent_count = len(get_all_agents())
            metrics.append(f"# HELP dashboard_agents_total Number of registered agents")
            metrics.append(f"# TYPE dashboard_agents_total gauge")
            metrics.append(f"dashboard_agents_total {agent_count}")
        except:
            pass

        return "\n".join(metrics) + "\n", 200, {'Content-Type': 'text/plain'}

    except Exception as e:
        logger.error(f"Error generating metrics: {e}")
        return f"# Error generating metrics: {e}\n", 500, {'Content-Type': 'text/plain'}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5555)
