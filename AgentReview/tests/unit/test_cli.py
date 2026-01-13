from typer.testing import CliRunner
from multiagentpanic.cli import app
from unittest.mock import patch, MagicMock

runner = CliRunner()


def test_check_command():
    # Mock load_dotenv and get_settings
    with (
        patch("multiagentpanic.cli.load_dotenv") as mock_load_dotenv,
        patch("multiagentpanic.cli.get_settings") as mock_get_settings,
    ):

        # Configure mock settings
        mock_settings = MagicMock()
        mock_settings.llm.openai_api_key = "sk-test"
        mock_settings.llm.anthropic_api_key = None
        mock_settings.llm.google_api_key = None
        mock_settings.database.postgres_url = "postgresql://..."
        mock_settings.database.redis_url = "redis://..."
        mock_settings.mcp.zoekt_enabled = True
        mock_settings.mcp.lsp_enabled = False
        mock_settings.mcp.git_enabled = True

        mock_get_settings.return_value = mock_settings

        result = runner.invoke(app, ["check"])

        # Check successful execution
        assert result.exit_code == 0

        # Check output contains key elements
        assert "Checking Environment Configuration" in result.stdout
        assert "Settings" in result.stdout
        assert "LLM Providers" in result.stdout
        assert "Configured: OpenAI" in result.stdout
        assert "Zoekt, Git" in result.stdout
