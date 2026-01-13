import dagger
from dagger import dag

@dag.function
async def periodic_health_check(issue: str = "periodic-health-check"):
    """
    Runs the central obs_agent in an isolated Python container.
    """
    return await (
        dag.container()
        .from_("python:3.12-slim")
        .with_mounted_directory("/src", dag.host().directory("."))
        .with_workdir("/src")
        .with_exec(["pip", "install", "-r", "requirements.txt"])
        .with_env_variable("MCP_URL", "http://host.docker.internal:8433")
        .with_exec(["python", "scripts/obs_agent.py", issue])
    )

@dag.function
async def sync_memory_to_central():
    """
    Syncs ./memory to a central server via rsync over SSH.
    """
    return await (
        dag.container()
        .from_("alpine:latest")
        .with_exec(["apk", "add", "--no-cache", "rsync", "openssh-client"])
        .with_mounted_directory("/src", dag.host().directory("."))
        .with_workdir("/src")
        .with_env_variable("CENTRAL_SSH", "user@central-server")
        .with_exec([
            "sh",
            "-c",
            "rsync -avz memory/ \"$CENTRAL_SSH\":~/observability-control/memory/"
        ])
    )
