import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from pathlib import Path
from dotenv import load_dotenv
import os

from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel

from multiagentpanic.graph import ReviewOrchestrator
from multiagentpanic.domain.state import ReviewState
from multiagentpanic.tools import get_repo_context

app = typer.Typer()
console = Console()

@app.command()
def review(
    repo_path: Path = typer.Argument(..., exists=True, file_okay=False, dir_okay=True, readable=True, resolve_path=True, help="Path to the repository to review."),
    model_name: str = typer.Option("gpt-4-turbo", help="The LLM model name to use for agents."),
    model_base_url: Optional[str] = typer.Option(None, help="Optional base URL for the LLM API (e.g., for Grok, ZAI, Kimi)."),
    api_key_env: str = typer.Option("OPENAI_API_KEY", help="Environment variable name for the LLM API key."),
    max_depth: int = typer.Option(2, help="Maximum directory depth to gather context for agents."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output.")
):
    """
    Initiates a multi-agent review of the specified repository.
    """
    console.print(Panel.fit("[bold blue]Starting MultiagentPanic Code Review[/bold blue]", style="blue"))

    load_dotenv() # Load .env file for API keys

    api_key = os.getenv(api_key_env)
    if not api_key:
        console.print(Panel.fit(f"[bold red]Error: API key not found in environment variable '{api_key_env}'[/bold red]", style="red"))
        raise typer.Exit(code=1)

    console.print(f"Using LLM: [bold green]{model_name}[/bold green]")
    if model_base_url:
        console.print(f"  Base URL: [bold green]{model_base_url}[/bold green]")
    console.print(f"Target Repository: [bold yellow]{repo_path}[/bold yellow]")

    # Initialize LLM
    llm: BaseChatModel = ChatOpenAI(
        model=model_name,
        openai_api_key=api_key,
        openai_api_base=model_base_url, # Pass custom base URL if provided
        temperature=0.0, # Deterministic outputs
        streaming=False
    )

    console.print("\n[bold cyan]Gathering initial repository context...[/bold cyan]")
    # Placeholder for a more sophisticated context gathering mechanism
    # For now, it's a simple recursive read up to max_depth
    repo_context = get_repo_context(repo_path, max_depth=max_depth)
    
    if verbose:
        console.print(Panel(f"[bold white]Repository Context (first 1000 chars):[/bold white]\n{str(repo_context)[:1000]}...", title="Context Debug", style="dim"))

    # Prepare initial state for LangGraph
    initial_state: ReviewState = ReviewState(
        repo_path=str(repo_path),
        pr_diff=None, # Will be added later if applicable
        issue_description=None, # Will be added later
        test_agent_review=None,
        docs_agent_review=None,
        code_agent_review=None,
        scope_agent_review=None,
        final_report=None,
        errors=[]
    )

    # Initialize and run the orchestrator
    orchestrator = ReviewOrchestrator(llm=llm)
    app_runnable = orchestrator.get_app()

    console.print("\n[bold cyan]Invoking multi-agent review...[/bold cyan]")
    with console.status("[bold green]Agents are reviewing the code...[/bold green]", spinner="dots"):
        # The agent_fn in core.py will receive this context.
        # We need to refine how context is passed and used by individual agents.
        # For now, we're passing the stringified repo_context.
        final_state = app_runnable.invoke(initial_state)

    console.print(Panel.fit("[bold blue]Review Complete![/bold blue]", style="blue"))

    if final_state.get("errors"):
        console.print(Panel(Text("\n".join(final_state["errors"])), style="bold red"), title="Errors During Review", style="red")
    
    if final_state.get("final_report"):
        console.print(Panel(Syntax(final_state["final_report"], "markdown", theme="ansi_light", line_numbers=False), title="MultiagentPanic Report", style="green"))
    else:
        console.print(Panel("[bold red]No final report generated.[/bold red]", style="red"))

if __name__ == "__main__":
    app()
