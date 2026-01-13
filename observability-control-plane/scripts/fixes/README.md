# Automated Fix Library

This library provides automated remediation for common observability infrastructure issues.

## Overview

The fix library contains 4 main modules with 15+ automated fixes:

- **docker_fixes.py**: Docker container and resource management
- **disk_fixes.py**: Disk space and log management
- **service_fixes.py**: System service and application fixes
- **memory_fixes.py**: Memory and process management

## Quick Start

```python
from fixes import get_fix_for_issue, FIX_REGISTRY

# Get a specific fix
fix_func = get_fix_for_issue("container_down")
result = fix_func("my-container")

# List all available fixes
print(FIX_REGISTRY.keys())
```

## Available Fixes

### Docker Fixes (docker_fixes.py)

| Fix Function | Description | Parameters | Use Case |
|--------------|-------------|------------|----------|
| `restart_container(container_name)` | Restart a specific container | container name | Container crashed or stuck |
| `restart_unhealthy()` | Find and restart all unhealthy containers | none | Multiple containers failing health checks |
| `prune_system(force=True)` | Remove unused Docker resources | force flag | Disk space running low |
| `check_container_logs(container_name, lines=100)` | Get recent container logs | container name, line count | Diagnose container issues |

### Disk Fixes (disk_fixes.py)

| Fix Function | Description | Parameters | Use Case |
|--------------|-------------|------------|----------|
| `cleanup_logs(directory="/var/log", days_old=7)` | Delete old log files | directory path, age threshold | Free disk space |
| `rotate_logs(service=None)` | Force log rotation | service name (optional) | Large log files |
| `cleanup_temp_files()` | Clean temporary directories | none | Disk cleanup |

### Service Fixes (service_fixes.py)

| Fix Function | Description | Parameters | Use Case |
|--------------|-------------|------------|----------|
| `restart_service(service_name)` | Restart systemd/init service | service name | Service not responding |
| `reset_connection_pool(service="postgres")` | Reset database connection pool | service type | Connection leaks |
| `resolve_port_conflict(port)` | Kill process using a port | port number | Port already in use |
| `check_service_health(service_name)` | Check service status | service name | Health validation |

### Memory Fixes (memory_fixes.py)

| Fix Function | Description | Parameters | Use Case |
|--------------|-------------|------------|----------|
| `clear_caches()` | Clear system caches | none | Free memory |
| `kill_zombies()` | Clean up zombie processes | none | Process cleanup |
| `kill_high_memory_processes(threshold_mb=1000)` | Kill memory-intensive processes | memory threshold | OOM prevention |
| `restart_memory_intensive_services()` | Restart known memory-leaking services | none | Memory leak mitigation |

## Fix Registry

All fixes are registered in `FIX_REGISTRY` for easy lookup:

```python
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
```

## Response Format

All fix functions return a structured dictionary:

```python
{
    "success": bool,           # True if fix succeeded
    "action": str,             # Description of action taken
    "error": str,              # Error message (if failed)
    # Additional context-specific fields
}
```

### Success Example
```python
{
    "success": True,
    "action": "Restarted container nginx",
    "output": "nginx\n"
}
```

### Failure Example
```python
{
    "success": False,
    "error": "Failed to stop container: No such container"
}
```

## Testing

Run the test suite (safe, no actual fixes):

```bash
python scripts/test_fixes.py
```

WARNING: The `--run` flag executes actual fixes and can modify your system!

```bash
python scripts/test_fixes.py --run  # USE WITH CAUTION!
```

## Integration Example

```python
import logging
from fixes import get_fix_for_issue

logging.basicConfig(level=logging.INFO)

# Detect issue type
issue_type = "container_down"
container_name = "prometheus"

# Get and execute fix
fix_func = get_fix_for_issue(issue_type)
if fix_func:
    result = fix_func(container_name)

    if result["success"]:
        print(f"✓ Fixed: {result['action']}")
    else:
        print(f"✗ Failed: {result['error']}")
else:
    print(f"No fix available for {issue_type}")
```

## Safety Considerations

1. **Idempotent**: All fixes can be run multiple times safely
2. **Logging**: All actions are logged for audit trail
3. **Error Handling**: Graceful failure with detailed error messages
4. **Permissions**: Some fixes require root/sudo access
5. **Testing**: Always test in non-production first

## Dependencies

Required Python packages:
- `psutil` - Process and system utilities
- Standard library: `subprocess`, `logging`, `glob`, `datetime`, `os`, `time`

## Platform Support

- **Linux**: Full support (systemd, Docker, /proc filesystem)
- **macOS**: Partial support (Docker, disk operations)
- **Windows**: Limited support (Docker Desktop only)

## Adding New Fixes

1. Create method in appropriate fix class
2. Add to `FIX_REGISTRY` in `__init__.py`
3. Document in this README
4. Test thoroughly before production use

## License

Part of the Observability Implementation Package
