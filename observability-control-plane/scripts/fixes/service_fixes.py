"""Service and application level fixes"""
import os
import subprocess
import psutil
import time
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class ServiceFixes:
    """Fixes for service-level issues"""

    @staticmethod
    def restart_service(service_name: str) -> Dict[str, Any]:
        """Restart a system service using systemctl or service command"""
        try:
            # Try systemctl first (systemd)
            result = subprocess.run(
                ["systemctl", "restart", service_name],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                # Check if service is active
                status = subprocess.run(
                    ["systemctl", "is-active", service_name],
                    capture_output=True,
                    text=True
                )

                return {
                    "success": status.stdout.strip() == "active",
                    "action": f"Restarted service {service_name}",
                    "status": status.stdout.strip()
                }
            else:
                # Try service command (SysV init)
                result = subprocess.run(
                    ["service", service_name, "restart"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                return {
                    "success": result.returncode == 0,
                    "action": f"Restarted service {service_name}",
                    "output": result.stdout
                }

        except FileNotFoundError:
            # Neither systemctl nor service available
            return {"success": False, "error": "Service management not available"}
        except Exception as e:
            logger.error(f"Error restarting service: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def reset_connection_pool(service: str = "postgres") -> Dict[str, Any]:
        """Reset database connection pool"""
        try:
            if service == "postgres":
                # Kill idle connections
                cmd = [
                    "psql", "-U", "postgres", "-c",
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle' AND pid <> pg_backend_pid();"
                ]

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    env={"PGPASSWORD": os.getenv("POSTGRES_PASSWORD", "postgres")}
                )

                return {
                    "success": result.returncode == 0,
                    "action": "Reset Postgres connection pool",
                    "output": result.stdout
                }

            elif service == "neo4j":
                # Restart Neo4j to reset connections
                return ServiceFixes.restart_service("neo4j")

            else:
                return {"success": False, "error": f"Unknown service: {service}"}

        except Exception as e:
            logger.error(f"Error resetting connection pool: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def resolve_port_conflict(port: int) -> Dict[str, Any]:
        """Find and kill process using a specific port"""
        try:
            # Find process using the port
            for conn in psutil.net_connections():
                if conn.laddr.port == port and conn.status == 'LISTEN':
                    try:
                        process = psutil.Process(conn.pid)
                        process_info = {
                            "pid": conn.pid,
                            "name": process.name(),
                            "cmdline": ' '.join(process.cmdline())
                        }

                        # Kill the process
                        process.terminate()
                        time.sleep(2)

                        if process.is_running():
                            process.kill()

                        logger.info(f"Killed process {conn.pid} using port {port}")

                        return {
                            "success": True,
                            "action": f"Resolved port {port} conflict",
                            "killed_process": process_info
                        }

                    except Exception as e:
                        return {
                            "success": False,
                            "error": f"Could not kill process: {e}"
                        }

            return {
                "success": True,
                "action": f"Port {port} is not in use",
                "status": "available"
            }

        except Exception as e:
            logger.error(f"Error resolving port conflict: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def check_service_health(service_name: str) -> Dict[str, Any]:
        """Check if a service is healthy"""
        try:
            # Check systemd service
            result = subprocess.run(
                ["systemctl", "status", service_name],
                capture_output=True,
                text=True
            )

            is_active = "active (running)" in result.stdout

            return {
                "success": True,
                "service": service_name,
                "healthy": is_active,
                "status": "running" if is_active else "stopped",
                "details": result.stdout[:500]  # First 500 chars
            }

        except Exception as e:
            return {"success": False, "error": str(e)}
