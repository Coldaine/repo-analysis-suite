"""Automated fix library for common observability issues"""

from .docker_fixes import DockerFixes
from .disk_fixes import DiskFixes
from .service_fixes import ServiceFixes
from .memory_fixes import MemoryFixes

# Export all fix classes
__all__ = ['DockerFixes', 'DiskFixes', 'ServiceFixes', 'MemoryFixes']

# Registry of all available fixes
FIX_REGISTRY = {
    "container_down": DockerFixes.restart_container,
    "container_unhealthy": DockerFixes.restart_unhealthy,
    "docker_disk_full": DockerFixes.prune_system,
    "disk_full": DiskFixes.cleanup_logs,
    "log_rotation_failed": DiskFixes.rotate_logs,
    "service_not_responding": ServiceFixes.restart_service,
    "database_connection_failed": ServiceFixes.reset_connection_pool,
    "high_memory_usage": MemoryFixes.clear_caches,
    "zombie_processes": MemoryFixes.kill_zombies,
    "port_conflict": ServiceFixes.resolve_port_conflict
}

def get_fix_for_issue(issue_type: str):
    """Get the appropriate fix function for an issue type"""
    return FIX_REGISTRY.get(issue_type)
