"""Docker-related automated fixes"""
import subprocess
import logging
import time
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class DockerFixes:
    """Fixes for Docker container issues"""

    @staticmethod
    def restart_container(container_name: str) -> Dict[str, Any]:
        """Restart a specific Docker container"""
        try:
            # Stop container
            result = subprocess.run(
                ["docker", "stop", container_name],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0 and "No such container" not in result.stderr:
                return {
                    "success": False,
                    "error": f"Failed to stop container: {result.stderr}"
                }

            # Wait a moment
            time.sleep(2)

            # Start container
            result = subprocess.run(
                ["docker", "start", container_name],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                logger.info(f"Successfully restarted container {container_name}")
                return {
                    "success": True,
                    "action": f"Restarted container {container_name}",
                    "output": result.stdout
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to start container: {result.stderr}"
                }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Docker command timed out"}
        except Exception as e:
            logger.error(f"Error restarting container: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def restart_unhealthy() -> Dict[str, Any]:
        """Find and restart all unhealthy containers"""
        try:
            # Find unhealthy containers
            result = subprocess.run(
                ["docker", "ps", "--filter", "health=unhealthy", "--format", "{{.Names}}"],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                return {"success": False, "error": "Failed to list unhealthy containers"}

            unhealthy = result.stdout.strip().split('\n')
            unhealthy = [c for c in unhealthy if c]  # Remove empty strings

            if not unhealthy:
                return {
                    "success": True,
                    "action": "No unhealthy containers found",
                    "containers": []
                }

            restarted = []
            failed = []

            for container in unhealthy:
                result = DockerFixes.restart_container(container)
                if result["success"]:
                    restarted.append(container)
                else:
                    failed.append(container)

            return {
                "success": len(failed) == 0,
                "action": f"Restarted {len(restarted)} unhealthy containers",
                "restarted": restarted,
                "failed": failed
            }

        except Exception as e:
            logger.error(f"Error restarting unhealthy containers: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def prune_system(force: bool = True) -> Dict[str, Any]:
        """Prune unused Docker resources to free disk space"""
        try:
            # Get disk usage before
            df_before = subprocess.run(
                ["df", "-h", "/var/lib/docker"],
                capture_output=True,
                text=True
            )

            # Prune containers
            cmd = ["docker", "container", "prune"]
            if force:
                cmd.append("-f")

            result = subprocess.run(cmd, capture_output=True, text=True)
            containers_output = result.stdout

            # Prune images
            cmd = ["docker", "image", "prune"]
            if force:
                cmd.append("-f")

            result = subprocess.run(cmd, capture_output=True, text=True)
            images_output = result.stdout

            # Prune volumes (be careful!)
            cmd = ["docker", "volume", "prune"]
            if force:
                cmd.append("-f")

            result = subprocess.run(cmd, capture_output=True, text=True)
            volumes_output = result.stdout

            # Prune networks
            cmd = ["docker", "network", "prune"]
            if force:
                cmd.append("-f")

            result = subprocess.run(cmd, capture_output=True, text=True)
            networks_output = result.stdout

            # Get disk usage after
            df_after = subprocess.run(
                ["df", "-h", "/var/lib/docker"],
                capture_output=True,
                text=True
            )

            logger.info("Docker system pruned successfully")

            return {
                "success": True,
                "action": "Pruned Docker system",
                "containers": containers_output,
                "images": images_output,
                "volumes": volumes_output,
                "networks": networks_output,
                "disk_before": df_before.stdout if df_before else "unknown",
                "disk_after": df_after.stdout if df_after else "unknown"
            }

        except Exception as e:
            logger.error(f"Error pruning Docker system: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def check_container_logs(container_name: str, lines: int = 100) -> Dict[str, Any]:
        """Get recent logs from a container for diagnostics"""
        try:
            result = subprocess.run(
                ["docker", "logs", "--tail", str(lines), container_name],
                capture_output=True,
                text=True,
                timeout=10
            )

            return {
                "success": True,
                "container": container_name,
                "logs": result.stdout,
                "errors": result.stderr
            }

        except Exception as e:
            return {"success": False, "error": str(e)}
