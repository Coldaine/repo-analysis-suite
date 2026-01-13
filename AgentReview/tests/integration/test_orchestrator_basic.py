"""
Basic integration test for PRReviewOrchestrator.

Tests the end-to-end workflow with a mock PR to ensure all components work together.
"""

import asyncio
import logging
from datetime import datetime

import pytest

from multiagentpanic.agents.orchestrator import create_orchestrator_for_testing
from multiagentpanic.domain.schemas import PRMetadata

# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.fixture
def mock_pr_metadata():
    """Create mock PR metadata for testing"""
    return PRMetadata(
        pr_number=123,
        pr_url="https://github.com/example/repo/pull/123",
        pr_branch="feature/add-new-endpoint",
        base_branch="main",
        pr_title="Add new authentication endpoint",
        pr_body="This PR adds a new authentication endpoint with proper validation.",
        pr_complexity="medium",
        pr_diff="""diff --git a/src/auth/endpoint.py b/src/auth/endpoint.py
index 1234567..abcdefg 100644
--- a/src/auth/endpoint.py
+++ b/src/auth/endpoint.py
@@ -10,7 +10,7 @@ class AuthenticationEndpoint:
         self.validate_input(user_data)
         
     def validate_input(self, data):
-        if not data.get('username') or not data.get('password'):
+        if not data.get('username') or not data.get('password') or len(data.get('password', '')) < 8:
             raise ValueError("Invalid credentials")
         
     def authenticate(self, username: str, password: str) -> bool:
""",
    )


@pytest.fixture
def mock_changed_files():
    """Create list of changed files for testing"""
    return [
        "src/auth/endpoint.py",
        "src/auth/__init__.py",
        "tests/test_auth_endpoint.py",
        "docs/authentication.md",
    ]


@pytest.mark.asyncio
async def test_orchestrator_basic_functionality():
    """Test that orchestrator can be created and initialized"""

    orchestrator = create_orchestrator_for_testing()

    # Verify orchestrator components are initialized
    assert orchestrator.settings is not None
    assert orchestrator.model_selector is not None
    assert hasattr(orchestrator, "factory")
    assert orchestrator.graph is not None

    logger.info("✅ Orchestrator initialized successfully")


@pytest.mark.asyncio
async def test_orchestrator_run_review(mock_pr_metadata, mock_changed_files):
    """Test running a complete PR review workflow"""

    orchestrator = create_orchestrator_for_testing()

    # Run the review
    pr_diff = mock_pr_metadata.pr_diff or ""

    # Run the orchestrator graph
    initial_state = await orchestrator.run(initial_state=None)
    # run() returns PRReviewState synchronously; wrap to keep async test shape
    final_state = initial_state

    # Verify state transitions occurred
    assert final_state.pr_complexity is not None  # Should be set by init node
    assert final_state.repo_memory is not None  # Should be loaded by memory node
    assert final_state.orchestrator_plan is not None  # Should be set by plan node
    assert final_state.ci_status is not None  # Should be set by workflow node
    assert (
        final_state.review_agent_reports is not None
    )  # Should be populated by collect node
    assert final_state.completed_at is not None  # Should be set by write_to_db node

    # Verify some basic properties
    assert final_state.pr_metadata.pr_number == 123
    assert final_state.changed_files is not None
    assert final_state.pr_diff is not None

    logger.info(
        f"✅ Review completed: {len(final_state.review_agent_reports)} agent reports"
    )
    logger.info(f"✅ A/B variant: {final_state.ab_test_variant}")
    logger.info(f"✅ Complexity assessed: {final_state.pr_complexity}")


@pytest.mark.asyncio
async def test_orchestrator_plan_parsing():
    """Test that orchestrator plan is properly parsed and executed"""

    orchestrator = create_orchestrator_for_testing()

    # Create a test state with minimal context
    from multiagentpanic.domain.schemas import PRReviewState

    test_state = PRReviewState(
        pr_metadata=PRMetadata(
            pr_number=456,
            pr_url="https://github.com/example/repo/pull/456",
            pr_branch="fix/security-issue",
            base_branch="main",
            pr_title="Fix potential security vulnerability",
            pr_complexity="simple",
        ),
        pr_diff="""diff --git a/src/security/validate.py b/src/security/validate.py
index 1234567..abcdefg 100644
--- a/src/security/validate.py
+++ b/src/security/validate.py
@@ -5,7 +5,7 @@ def validate_input(user_input):
-    if user_input.startswith('script'):
+    if 'script' in user_input.lower():
         raise ValueError("Potential XSS detected")
""",
        changed_files=["src/security/validate.py"],
        pr_complexity="simple",
        repo_memory={"conventions": "Always validate user input"},
        similar_prs=[],
        repo_conventions=[],
        orchestrator_plan={},
        ab_test_variant="default",
        ci_status=None,
        ci_triggered_by=None,
        review_agent_reports=[],
        context_cache={},
        ready_for_healing=False,
        healing_approved_tasks=[],
        tokens_used=0,
        agents_spawned=[],
        total_cost_usd=0.0,
        started_at=datetime.now(),
        completed_at=None,
    )

    # Test the orchestrator plan node directly
    # Use plan_agents to populate the plan
    planned_updates = orchestrator.plan_agents(test_state)
    assert "alignment" in planned_updates["orchestrator_plan"]["agents"]
    assert "testing" in planned_updates["orchestrator_plan"]["agents"]
    assert "security" in planned_updates["orchestrator_plan"]["agents"]

    logger.info(f"✅ Plan created: {planned_updates['orchestrator_plan']['agents']}")


@pytest.mark.asyncio
async def test_orchestrator_memory_loading():
    """Test memory loading functionality"""

    orchestrator = create_orchestrator_for_testing()

    # Create test state
    from multiagentpanic.domain.schemas import PRReviewState

    test_state = PRReviewState(
        pr_metadata=PRMetadata(
            pr_number=789,
            pr_url="https://github.com/example/repo/pull/789",
            pr_branch="feature/add-tests",
            base_branch="main",
            pr_title="Add comprehensive test coverage",
            pr_complexity="medium",
        ),
        pr_diff="Added new tests for authentication module",
        changed_files=["tests/test_auth.py", "tests/test_user.py"],
        pr_complexity="medium",
        repo_memory={},
        similar_prs=[],
        repo_conventions=[],
        orchestrator_plan={},
        ab_test_variant="default",
        ci_status=None,
        ci_triggered_by=None,
        review_agent_reports=[],
        context_cache={},
        ready_for_healing=False,
        healing_approved_tasks=[],
        tokens_used=0,
        agents_spawned=[],
        total_cost_usd=0.0,
        started_at=datetime.now(),
        completed_at=None,
    )

    # Test memory loading
    loaded_updates = await orchestrator.load_memory(test_state)
    assert loaded_updates["repo_memory"] is not None
    assert loaded_updates["similar_prs"] is not None

    logger.info(f"✅ Loaded {len(loaded_updates['repo_memory'])} memory items")
    logger.info(f"✅ Found {len(loaded_updates['similar_prs'])} similar PRs")


if __name__ == "__main__":
    # Run basic test without pytest
    async def run_basic_test():
        print("🧪 Testing PRReviewOrchestrator basic functionality...")

        # Test 1: Basic initialization
        orchestrator = create_orchestrator_for_testing()
        print("✅ Orchestrator initialized successfully")

        # Test 2: Mock PR data
        mock_pr = PRMetadata(
            pr_number=123,
            pr_url="https://github.com/example/repo/pull/123",
            pr_branch="feature/add-new-endpoint",
            base_branch="main",
            pr_title="Add new authentication endpoint",
            pr_complexity="medium",
        )

        mock_diff = "Added new authentication endpoint with validation"
        mock_files = ["src/auth/endpoint.py", "tests/test_auth.py"]

        # Test 3: Run complete review
        try:
            final_state = await orchestrator.run_review(
                pr_metadata=mock_pr, pr_diff=mock_diff, changed_files=mock_files
            )

            print("✅ Review completed successfully")
            print(f"   - Complexity: {final_state.pr_complexity}")
            print(f"   - Agents spawned: {len(final_state.agents_spawned)}")
            print(f"   - A/B variant: {final_state.ab_test_variant}")
            print(f"   - Review reports: {len(final_state.review_agent_reports)}")
            print(f"   - Ready for healing: {final_state.ready_for_healing}")

        except Exception as e:
            print(f"❌ Review failed: {e}")
            raise

        print("\n🎉 All tests passed! Orchestrator is working correctly.")

    # Run the basic test
    asyncio.run(run_basic_test())
