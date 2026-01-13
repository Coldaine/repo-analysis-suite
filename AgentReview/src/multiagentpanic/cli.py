import asyncio
import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Try to import settings, but handle if pydantic validation fails immediately
try:
    from multiagentpanic.config.settings import get_settings
except Exception:
    get_settings = None

app = typer.Typer(
    name="agentreview",
    help="Multi-Agent PR Review System CLI",
    add_completion=False,
    no_args_is_help=True,
)
console = Console()


@app.command()
def check():
    """
    Check the environment configuration and connectivity.
    """
    load_dotenv()
    console.print(Panel.fit("🔍 Checking Environment Configuration", style="bold blue"))

    table = Table(show_header=True, header_style="bold magenta", expand=True)
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Details")

    settings = None
    with console.status(
        "[bold green]Validating configuration...[/bold green]", spinner="dots"
    ):
        try:
            if get_settings:
                settings = get_settings()
                table.add_row("Settings", "[green]✓ OK[/green]", "Loaded successfully")
            else:
                table.add_row(
                    "Settings", "[red]✗ Error[/red]", "Could not import settings module"
                )
                console.print(table)
                return
        except Exception as e:
            table.add_row("Settings", "[red]✗ Error[/red]", f"Validation failed: {e}")
            console.print(table)
            console.print(
                "\n[yellow]Tip: Check your .env file or environment variables.[/yellow]"
            )
            return

        # Check LLM Keys
        providers = []
        if settings.llm.openai_api_key:
            providers.append("OpenAI")
        if settings.llm.anthropic_api_key:
            providers.append("Anthropic")
        if settings.llm.google_api_key:
            providers.append("Google")

        if providers:
            table.add_row(
                "LLM Providers",
                "[green]✓ OK[/green]",
                f"Configured: {', '.join(providers)}",
            )
        else:
            table.add_row(
                "LLM Providers", "[red]✗ Missing[/red]", "At least one API key needed"
            )

        # Check Database
        if settings.database.postgres_url:
            table.add_row("PostgreSQL", "[green]✓ OK[/green]", "URL configured")
        else:
            table.add_row("PostgreSQL", "[red]✗ Missing[/red]", "URL missing")

        # Check Redis
        if settings.database.redis_url:
            table.add_row("Redis", "[green]✓ OK[/green]", "URL configured")
        else:
            table.add_row(
                "Redis", "[yellow]! Warning[/yellow]", "URL missing (using defaults?)"
            )

        # Check MCP
        mcp_status = []
        if settings.mcp.zoekt_enabled:
            mcp_status.append("Zoekt")
        if settings.mcp.lsp_enabled:
            mcp_status.append("LSP")
        if settings.mcp.git_enabled:
            mcp_status.append("Git")

        if mcp_status:
            table.add_row(
                "MCP Servers",
                "[green]✓ OK[/green]",
                f"Enabled: {', '.join(mcp_status)}",
            )
        else:
            table.add_row(
                "MCP Servers", "[yellow]! Warning[/yellow]", "No MCP servers enabled"
            )

    console.print(table)
    console.print("\n[bold green]Configuration check complete.[/bold green]")


@app.command()
def review(
    repo: str = typer.Option(..., help="Repository name (owner/repo)"),
    pr: int = typer.Option(..., help="Pull Request number"),
    local_file: str = typer.Option(
        None, help="Local file to review (for testing without GitHub)"
    ),
):
    """
    Run a multi-agent review on a Pull Request.
    """
    load_dotenv()
    console.print(
        Panel(
            f"🚀 Starting Review for [bold]{repo} PR #{pr}[/bold]", style="bold magenta"
        )
    )

    # Check if we can actually run
    try:
        if get_settings:
            settings = get_settings()
        else:
            raise ImportError("Settings not available")
    except Exception as e:
        console.print(f"[red]Cannot start review:[/red] {e}")
        console.print("Run [bold]python -m multiagentpanic check[/bold] to diagnose.")
        raise typer.Exit(code=1)

    # Import orchestrator
    try:
        from multiagentpanic.agents.orchestrator import create_orchestrator
        from multiagentpanic.domain.schemas import PRMetadata, PRReviewState
    except ImportError as e:
        console.print(f"[red]Import error:[/red] {e}")
        raise typer.Exit(code=1)

    # Create orchestrator
    try:
        orchestrator = create_orchestrator()
    except Exception as e:
        console.print(f"[red]Failed to create orchestrator:[/red] {e}")
        raise typer.Exit(code=1)

    # Prepare PR data
    pr_metadata = PRMetadata(
        pr_number=pr,
        pr_url=f"https://github.com/{repo}/pull/{pr}",
        pr_branch=f"pr-{pr}",
        base_branch="main",
        pr_title=f"PR #{pr} Review",
        pr_complexity="medium",
    )

    # Get diff content
    if local_file:
        console.print(f"[yellow]Using local file:[/yellow] {local_file}")
        try:
            with open(local_file, "r") as f:
                pr_diff = f.read()
                changed_files = [local_file]
        except FileNotFoundError:
            console.print(f"[red]File not found:[/red] {local_file}")
            raise typer.Exit(code=1)
    else:
        # TODO: Implement GitHub fetching
        console.print("[yellow]GitHub fetching not yet implemented.[/yellow]")
        console.print("Use --local-file to review a local file for now.")
        raise typer.Exit(code=1)

    # Create initial state
    initial_state = PRReviewState(
        pr_metadata=pr_metadata,
        pr_diff=pr_diff,
        changed_files=changed_files,
        pr_complexity="medium",
        repo_memory={},
        similar_prs=[],
        repo_conventions=[],
        orchestrator_plan={},
    )

    # Run review
    try:
        with console.status(
            "[bold cyan]Running review agents...[/bold cyan]", spinner="dots"
        ):
            final_state = asyncio.run(orchestrator.run(initial_state))

        # Display results
        console.print("\n[bold green]✓ Review Complete[/bold green]")
        console.print(f"\nAgents run: {len(final_state.review_agent_reports)}")

        # Create results table
        table = Table(
            title="Agent Reports", show_header=True, header_style="bold magenta"
        )
        table.add_column("Specialty", style="cyan")
        table.add_column("Verdict", style="bold")
        table.add_column("Conf.", justify="right")
        table.add_column("Summary", style="dim")
        table.add_column("Findings", justify="right")

        for report in final_state.review_agent_reports:
            verdict_color = (
                "green"
                if report.verdict == "PASS"
                else "red" if report.verdict == "FAIL" else "yellow"
            )
            findings_count = str(len(report.findings)) if report.findings else "0"

            table.add_row(
                report.specialty.upper(),
                f"[{verdict_color}]{report.verdict}[/{verdict_color}]",
                report.summary,
                f"{report.confidence:.2f}",
                findings_count,
            )

        console.print(table)

        console.print(f"\n[dim]Total cost: ${final_state.total_cost_usd:.4f}[/dim]")
        console.print(f"[dim]Tokens used: {final_state.tokens_used}[/dim]")

    except Exception as e:
        console.print(f"\n[red]Review failed:[/red] {e}")
        import traceback

        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(code=1)
