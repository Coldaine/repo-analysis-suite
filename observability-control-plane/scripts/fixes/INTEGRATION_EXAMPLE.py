#!/usr/bin/env python3
"""
Integration example showing how to use the fix library with the observability agent.
This demonstrates the workflow for automated remediation.
"""

import sys
import os
import logging
from typing import Dict, Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from fixes import get_fix_for_issue, FIX_REGISTRY

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AutomatedRemediationEngine:
    """
    Integration layer between issue detection and automated fixes.
    This would be called by the observability agent when issues are detected.
    """

    def __init__(self, dry_run: bool = True):
        """
        Initialize the remediation engine.

        Args:
            dry_run: If True, only simulate fixes without executing them
        """
        self.dry_run = dry_run
        self.fix_history = []

    def remediate_issue(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        """
        Attempt to automatically fix a detected issue.

        Args:
            issue: Issue dictionary with 'type', 'severity', and context

        Returns:
            Remediation result with success status and details
        """
        issue_type = issue.get('type')
        severity = issue.get('severity', 'unknown')
        context = issue.get('context', {})

        logger.info(f"Attempting to remediate issue: {issue_type} (severity: {severity})")

        # Get the appropriate fix
        fix_func = get_fix_for_issue(issue_type)

        if not fix_func:
            logger.warning(f"No automated fix available for issue type: {issue_type}")
            return {
                "success": False,
                "issue_type": issue_type,
                "error": "No fix available",
                "action_taken": "none"
            }

        # Determine if we should execute based on severity and dry_run
        if self.dry_run:
            logger.info(f"DRY RUN: Would execute fix: {fix_func.__name__}")
            return {
                "success": True,
                "issue_type": issue_type,
                "action_taken": f"dry_run: {fix_func.__name__}",
                "would_execute": True
            }

        # Execute the fix
        try:
            # Extract parameters from context
            params = self._extract_fix_parameters(issue_type, context)

            logger.info(f"Executing fix: {fix_func.__name__} with params: {params}")
            result = fix_func(**params) if params else fix_func()

            # Record in history
            self.fix_history.append({
                "issue_type": issue_type,
                "fix_function": fix_func.__name__,
                "result": result,
                "timestamp": logging.Formatter().formatTime(logging.LogRecord(
                    "", 0, "", 0, "", (), None
                ))
            })

            logger.info(f"Fix result: {result}")
            return result

        except Exception as e:
            logger.error(f"Error executing fix: {e}", exc_info=True)
            return {
                "success": False,
                "issue_type": issue_type,
                "error": str(e),
                "action_taken": "failed"
            }

    def _extract_fix_parameters(self, issue_type: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract appropriate parameters for the fix function from issue context.

        Args:
            issue_type: Type of issue being fixed
            context: Issue context dictionary

        Returns:
            Dictionary of parameters for the fix function
        """
        param_map = {
            "container_down": {"container_name": context.get("container_name")},
            "port_conflict": {"port": context.get("port")},
            "disk_full": {
                "directory": context.get("directory", "/var/log"),
                "days_old": context.get("days_old", 7)
            },
            "log_rotation_failed": {"service": context.get("service")},
            "service_not_responding": {"service_name": context.get("service_name")},
            "database_connection_failed": {"service": context.get("service", "postgres")},
            "high_memory_usage": {},
            "zombie_processes": {},
            "container_unhealthy": {},
            "docker_disk_full": {"force": context.get("force", True)}
        }

        return param_map.get(issue_type, {})

    def list_available_fixes(self):
        """List all available fixes in the registry"""
        print("\nAvailable Automated Fixes:")
        print("=" * 60)
        for issue_type, fix_func in FIX_REGISTRY.items():
            print(f"  {issue_type:30} -> {fix_func.__name__}")
        print("=" * 60)
        print(f"Total fixes available: {len(FIX_REGISTRY)}")

    def get_fix_history(self):
        """Return the history of executed fixes"""
        return self.fix_history


# Example usage scenarios
def example_container_down():
    """Example: Handle a container that's down"""
    engine = AutomatedRemediationEngine(dry_run=False)

    issue = {
        "type": "container_down",
        "severity": "high",
        "context": {
            "container_name": "prometheus"
        }
    }

    result = engine.remediate_issue(issue)
    print(f"\nContainer down remediation result: {result}")


def example_disk_full():
    """Example: Handle disk full situation"""
    engine = AutomatedRemediationEngine(dry_run=False)

    issue = {
        "type": "disk_full",
        "severity": "critical",
        "context": {
            "directory": "/var/log",
            "days_old": 7
        }
    }

    result = engine.remediate_issue(issue)
    print(f"\nDisk full remediation result: {result}")


def example_multiple_issues():
    """Example: Handle multiple issues in sequence"""
    engine = AutomatedRemediationEngine(dry_run=True)  # Safe dry-run mode

    issues = [
        {
            "type": "container_unhealthy",
            "severity": "medium",
            "context": {}
        },
        {
            "type": "high_memory_usage",
            "severity": "high",
            "context": {}
        },
        {
            "type": "zombie_processes",
            "severity": "low",
            "context": {}
        }
    ]

    print("\nRemediating multiple issues:")
    print("=" * 60)

    for issue in issues:
        result = engine.remediate_issue(issue)
        print(f"{issue['type']:30} -> {result.get('action_taken', 'unknown')}")

    print("=" * 60)


def integration_with_obs_agent():
    """
    Example showing how this would integrate with obs_agent.py

    In obs_agent.py, you would add something like:

    from fixes import get_fix_for_issue

    def handle_container_issue(self, container_name, issue_type):
        # Existing detection code...

        # NEW: Attempt automated remediation
        if self.auto_remediate:
            fix_func = get_fix_for_issue(issue_type)
            if fix_func:
                result = fix_func(container_name)
                if result["success"]:
                    self.log_event("automated_fix", {
                        "issue": issue_type,
                        "action": result["action"],
                        "container": container_name
                    })
                    return True

        # Existing alert code...
        self.send_alert(...)
    """
    print("\nIntegration pattern with obs_agent.py:")
    print("=" * 60)
    print(__doc__)


if __name__ == "__main__":
    print("Automated Remediation Engine - Examples")
    print("=" * 60)

    # List available fixes
    engine = AutomatedRemediationEngine()
    engine.list_available_fixes()

    # Show integration pattern
    integration_with_obs_agent()

    print("\n" + "=" * 60)
    print("Example scenarios (commented out for safety):")
    print("  - example_container_down()")
    print("  - example_disk_full()")
    print("  - example_multiple_issues()")
    print("\nUncomment these to run actual examples.")
    print("=" * 60)

    # Uncomment to run examples:
    # example_container_down()
    # example_disk_full()
    example_multiple_issues()  # Safe - runs in dry-run mode
