import pytest
from unittest.mock import patch, AsyncMock

from multiagentpanic.agents.orchestrator import create_orchestrator
from multiagentpanic.config.settings import get_settings
from multiagentpanic.domain.schemas import PRMetadata, PRReviewState

# Secrets are injected via Bitwarden/environment - no .env loading needed


@pytest.mark.asyncio
@patch("multiagentpanic.factory.agent_factory.AgentFactory.create_review_agent_subgraph")
async def test_live_pr_review_e2e(mock_create_subgraph):
    """
    Execute a PR review, mocking the agent execution layer.
    This avoids live LLM calls but tests the orchestrator flow.
    """
    # 1. Setup Mock
    # Mock the behavior of the agent executor
    mock_final_report = {
        "verdict": "WARN",
        "confidence": 0.8,
        "summary": "Mock report summary",
        "specialty": "alignment",
        "findings": [
            {
                "id": "mock1",
                "iteration": 1,
                "severity": "medium",
                "finding_type": "style",
                "description": "Mock finding description",
                "file": "src/vulnerable.py",
                "line": 4,
                "suggestion": "Mock suggestion",
                "confidence": 0.95,
            }
        ],
        "context_gathered": [],
        "iterations_used": 1,
    }
    mock_subgraph = mock_create_subgraph.return_value
    mock_subgraph.ainvoke = AsyncMock(return_value={"final_report": mock_final_report})

    # 2. Setup Orchestrator (REAL, not mocked)
    orchestrator = create_orchestrator()

    # 3. Create Real PR Data (Simulated)
    bad_code = """
import os
def process_data(data):
    os.system(f"echo {data}")
    """

    pr_metadata = PRMetadata(
        pr_number=999,
        pr_url="https://github.com/test/repo/pull/999",
        pr_branch="test-branch",
        base_branch="main",
        pr_title="Test PR with Security Issues",
        pr_complexity="simple",
    )

    initial_state = PRReviewState(
        pr_metadata=pr_metadata,
        pr_diff=bad_code,
        changed_files=["src/vulnerable.py"],
        pr_complexity="simple",
        repo_memory={},
        similar_prs=[],
        repo_conventions=[],
        orchestrator_plan={},
    )

    # 4. Run Execution
    final_state = await orchestrator.run(initial_state)

    # 5. Assertions
    assert len(final_state.review_agent_reports) > 0
    assert final_state.review_agent_reports[0].specialty == "alignment"
