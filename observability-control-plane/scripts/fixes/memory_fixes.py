"""Memory and process related fixes"""
import os
import psutil
import subprocess
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class MemoryFixes:
    """Fixes for memory-related issues"""

    @staticmethod
    def clear_caches() -> Dict[str, Any]:
        """Clear system caches to free memory"""
        try:
            cleared = []

            # Clear PageCache only
            result = subprocess.run(
                ["sh", "-c", "echo 1 > /proc/sys/vm/drop_caches"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                cleared.append("PageCache")

            # Clear dentries and inodes
            result = subprocess.run(
                ["sh", "-c", "echo 2 > /proc/sys/vm/drop_caches"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                cleared.append("dentries and inodes")

            # Get memory info after clearing
            memory = psutil.virtual_memory()

            return {
                "success": len(cleared) > 0,
                "action": "Cleared system caches",
                "cleared": cleared,
                "memory_available_gb": memory.available / (1024**3),
                "memory_percent": memory.percent
            }

        except Exception as e:
            logger.error(f"Error clearing caches: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def kill_zombies() -> Dict[str, Any]:
        """Find and kill zombie processes"""
        try:
            zombies = []
            killed = []

            for proc in psutil.process_iter(['pid', 'name', 'status']):
                try:
                    if proc.info['status'] == psutil.STATUS_ZOMBIE:
                        zombies.append({
                            "pid": proc.info['pid'],
                            "name": proc.info['name']
                        })

                        # Try to kill the zombie's parent
                        parent = proc.parent()
                        if parent:
                            parent.terminate()
                            killed.append(proc.info['pid'])

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            return {
                "success": True,
                "action": f"Cleaned up {len(killed)} zombie processes",
                "zombies_found": len(zombies),
                "killed": killed
            }

        except Exception as e:
            logger.error(f"Error killing zombies: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def kill_high_memory_processes(threshold_mb: int = 1000) -> Dict[str, Any]:
        """Kill processes using excessive memory"""
        try:
            killed_processes = []

            for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
                try:
                    mem_mb = proc.info['memory_info'].rss / (1024 * 1024)

                    if mem_mb > threshold_mb:
                        # Skip critical system processes
                        if proc.info['name'] in ['systemd', 'kernel', 'init']:
                            continue

                        proc.terminate()
                        killed_processes.append({
                            "pid": proc.info['pid'],
                            "name": proc.info['name'],
                            "memory_mb": mem_mb
                        })

                        logger.info(f"Killed high-memory process {proc.info['name']} ({mem_mb:.1f} MB)")

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            return {
                "success": True,
                "action": f"Killed {len(killed_processes)} high-memory processes",
                "killed": killed_processes
            }

        except Exception as e:
            logger.error(f"Error killing high-memory processes: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def restart_memory_intensive_services() -> Dict[str, Any]:
        """Restart services known to have memory leaks"""
        # Import here to avoid circular dependency
        from .service_fixes import ServiceFixes

        services_to_restart = [
            "grafana-agent",
            "prometheus",
            "elasticsearch",
            "logstash"
        ]

        restarted = []
        failed = []

        for service in services_to_restart:
            result = ServiceFixes.restart_service(service)
            if result["success"]:
                restarted.append(service)
            else:
                failed.append(service)

        return {
            "success": len(failed) == 0,
            "action": f"Restarted {len(restarted)} memory-intensive services",
            "restarted": restarted,
            "failed": failed
        }
