#!/usr/bin/env python3
import os
import sys
import subprocess
import platform
from datetime import datetime

COMMANDS = {
    "health": {
        "desc": "Run periodic health check via Dagger",
        "cmd": "dagger call periodic-health-check"
    },
    "reset": {
        "desc": "Reset all services (DOWN then UP)",
        "cmd": "docker compose down -v && docker compose up -d"
    },
    "backup": {
        "desc": "Backup all data directories",
        "cmd": f"tar czf backup-{datetime.now().strftime('%Y-%m-%d-%H%M%S')}.tgz memory/ pg-data/ neo4j-data/"
    },
    "memory-sync": {
        "desc": "Sync memory to central server via Dagger",
        "cmd": "dagger call sync-memory-to-central"
    },
}


def open_dashboard():
    """Open dashboard in default browser (cross-platform)"""
    url = "http://localhost:5555"
    system = platform.system()

    if system == "Darwin":
        cmd = ["open", url]
    elif system == "Windows":
        cmd = ["cmd", "/c", "start", url]
    else:
        cmd = ["xdg-open", url]

    try:
        subprocess.run(cmd, check=False)
        print(f"Opening dashboard: {url}")
    except Exception as e:
        print(f"Could not open dashboard: {e}")
        print(f"Please open manually: {url}")


def show_help():
    """Display help message"""
    print("Observability Control Plane - Management CLI\n")
    print("Usage: python scripts/manage.py <command>\n")
    print("Available commands:")
    print("  dashboard        Open dashboard in browser")

    for cmd, info in COMMANDS.items():
        print(f"  {cmd:<16} {info['desc']}")

    print("\nEnvironment:")
    print("  Ensure .env file is configured before running commands")
    print("  Run 'docker compose ps' to check service status")


def main():
    if len(sys.argv) < 2:
        show_help()
        sys.exit(1)

    subcmd = sys.argv[1]

    if subcmd == "help" or subcmd == "--help" or subcmd == "-h":
        show_help()
        return

    if subcmd == "dashboard":
        open_dashboard()
        return

    if subcmd not in COMMANDS:
        print(f"ERROR: Unknown command '{subcmd}'")
        show_help()
        sys.exit(1)

    # Change to repo root for all commands
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(repo_root)

    print(f"Running: {COMMANDS[subcmd]['desc']}")
    print(f"Command: {COMMANDS[subcmd]['cmd']}\n")

    result = subprocess.run(
        COMMANDS[subcmd]["cmd"],
        shell=True,
        check=False
    )

    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
