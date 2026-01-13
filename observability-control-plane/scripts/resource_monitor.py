#!/usr/bin/env python3
import psutil
from typing import Dict, Any

try:
    import docker
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False


def get_disk_usage() -> str:
    """
    Get cross-platform disk usage using psutil.
    """
    try:
        disk = psutil.disk_usage('/')
        total_gb = disk.total / (1024**3)
        used_gb = disk.used / (1024**3)
        free_gb = disk.free / (1024**3)

        return (
            f"Total: {total_gb:.2f} GB | "
            f"Used: {used_gb:.2f} GB ({disk.percent}%) | "
            f"Free: {free_gb:.2f} GB"
        )
    except Exception as e:
        return f"ERROR: {e}"


def get_docker_status() -> str:
    """
    Get Docker container status using Docker SDK.
    Falls back to error message if Docker is unavailable.
    """
    if not DOCKER_AVAILABLE:
        return "Docker SDK not installed (pip install docker)"

    try:
        client = docker.from_env()
        containers = client.containers.list(all=True)

        if not containers:
            return "No containers found"

        status_lines = ["Name | Status | State"]
        status_lines.append("-" * 50)

        for container in containers:
            name = container.name
            status = container.status
            state = container.attrs.get('State', {}).get('Status', 'unknown')
            status_lines.append(f"{name} | {status} | {state}")

        return "\n".join(status_lines)

    except docker.errors.DockerException as e:
        return f"Docker unavailable: {e}"
    except Exception as e:
        return f"ERROR: {e}"


def system_state() -> Dict[str, Any]:
    """
    Return a coarse view of system & container health.
    """
    return {
        "disk_usage": get_disk_usage(),
        "docker_status": get_docker_status(),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(system_state(), indent=2))
