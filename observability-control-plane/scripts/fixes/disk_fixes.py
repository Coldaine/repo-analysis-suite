"""Disk and storage related fixes"""
import os
import subprocess
import glob
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class DiskFixes:
    """Fixes for disk space issues"""

    @staticmethod
    def cleanup_logs(directory: str = "/var/log", days_old: int = 7) -> Dict[str, Any]:
        """Clean up old log files"""
        try:
            if not os.path.exists(directory):
                return {"success": False, "error": f"Directory {directory} not found"}

            # Find old log files
            cutoff = datetime.now() - timedelta(days=days_old)
            deleted_files = []
            freed_space = 0

            for log_file in glob.glob(f"{directory}/**/*.log*", recursive=True):
                try:
                    stat = os.stat(log_file)
                    mtime = datetime.fromtimestamp(stat.st_mtime)

                    if mtime < cutoff:
                        size = stat.st_size
                        os.remove(log_file)
                        deleted_files.append(log_file)
                        freed_space += size
                        logger.info(f"Deleted old log: {log_file}")
                except Exception as e:
                    logger.warning(f"Could not delete {log_file}: {e}")

            return {
                "success": True,
                "action": f"Cleaned up {len(deleted_files)} log files",
                "freed_space_mb": freed_space / (1024 * 1024),
                "deleted_files": deleted_files[:10]  # First 10 for brevity
            }

        except Exception as e:
            logger.error(f"Error cleaning logs: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def rotate_logs(service: Optional[str] = None) -> Dict[str, Any]:
        """Force log rotation using logrotate"""
        try:
            if service:
                # Rotate specific service logs
                cmd = ["logrotate", "-f", f"/etc/logrotate.d/{service}"]
            else:
                # Rotate all logs
                cmd = ["logrotate", "-f", "/etc/logrotate.conf"]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                return {
                    "success": True,
                    "action": f"Rotated logs for {service or 'all services'}",
                    "output": result.stdout
                }
            else:
                return {
                    "success": False,
                    "error": f"Log rotation failed: {result.stderr}"
                }

        except FileNotFoundError:
            # Logrotate not installed, try manual rotation
            return DiskFixes._manual_rotate_logs(service)
        except Exception as e:
            logger.error(f"Error rotating logs: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def _manual_rotate_logs(service: Optional[str] = None) -> Dict[str, Any]:
        """Manual log rotation when logrotate is not available"""
        try:
            log_dir = "/var/log"
            pattern = f"{service}*.log" if service else "*.log"
            rotated = []

            for log_file in glob.glob(f"{log_dir}/{pattern}"):
                if os.path.getsize(log_file) > 100 * 1024 * 1024:  # > 100MB
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    new_name = f"{log_file}.{timestamp}"
                    os.rename(log_file, new_name)

                    # Create new empty log file
                    open(log_file, 'a').close()

                    # Compress old log
                    subprocess.run(["gzip", new_name], check=False)
                    rotated.append(log_file)

            return {
                "success": True,
                "action": "Manually rotated large logs",
                "rotated": rotated
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def cleanup_temp_files() -> Dict[str, Any]:
        """Clean up temporary files"""
        try:
            temp_dirs = ["/tmp", "/var/tmp"]
            deleted_count = 0
            freed_space = 0

            for temp_dir in temp_dirs:
                if not os.path.exists(temp_dir):
                    continue

                # Find files older than 7 days
                result = subprocess.run(
                    ["find", temp_dir, "-type", "f", "-mtime", "+7", "-delete"],
                    capture_output=True,
                    text=True
                )

                # Count deleted files (approximate)
                deleted_count += len(result.stdout.split('\n')) if result.stdout else 0

            return {
                "success": True,
                "action": "Cleaned temporary files",
                "deleted_count": deleted_count
            }

        except Exception as e:
            logger.error(f"Error cleaning temp files: {e}")
            return {"success": False, "error": str(e)}
