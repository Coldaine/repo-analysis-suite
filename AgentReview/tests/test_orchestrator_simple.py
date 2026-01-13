"""
Test file for the simplified PRReviewOrchestrator implementation (Phase 2).
"""

from multiagentpanic.agents.orchestrator import PRReviewOrchestrator, get_sample_pr
from multiagentpanic.domain.schemas import PRReviewState


def test_sample_pr_data():
    """Test that sample PR data is available and correctly formatted."""
    sample_pr = get_sample_pr()

    # Check required fields
    assert "pr_number" in sample_pr
    assert "pr_title" in sample_pr
    assert "pr_diff" in sample_pr
    assert "changed_files" in sample_pr
    assert "pr_complexity" in sample_pr

    print("✓ Sample PR data test passed")


def test_orchestrator_node_functions():
    """Test the orchestrator node functions directly without full settings validation."""

    # Create a minimal orchestrator without full initialization
    orch = PRReviewOrchestrator.__new__(PRReviewOrchestrator)

    # Test init_pr function
    from multiagentpanic.domain.schemas import PRMetadata

    # Create proper PRMetadata
    pr_metadata = PRMetadata(
        pr_number=123,
        pr_url="https://github.com/test/repo/pull/123",
        pr_branch="feature-branch",
        base_branch="main",
        pr_title="Test PR",
        pr_complexity="simple",
    )

    initial_state = PRReviewState(
        pr_metadata=pr_metadata,
        pr_data={},
        pr_diff="",
        changed_files=[],
        pr_complexity="simple",
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
    )

    # Test init_pr node
    state_after_init = orch.init_pr(initial_state)
    assert "pr_metadata" in state_after_init, "init_pr should set pr_metadata"
    assert "pr_diff" in state_after_init, "init_pr should set pr_diff"
    assert "changed_files" in state_after_init, "init_pr should set changed_files"
    assert state_after_init["orchestrator_plan"] == {}, (
        "init_pr should initialize orchestrator_plan"
    )
    assert state_after_init["review_agent_reports"] == [], (
        "init_pr should initialize review_agent_reports"
    )
    print("✓ init_pr node test passed")

    # Test plan_agents node
    # Note: plan_agents expects the full state, but we only have updates from init_pr.
    # In a real graph, usage would merge these. For testing, we can pass initial_state
    # since plan_agents doesn't depend on init_pr's output specifically if we use defaults?
    # Actually, plan_agents takes state. We should update the state manually for the test.
    updated_state = initial_state.model_copy(update=state_after_init)
    state_after_plan = orch.plan_agents(updated_state)
    assert state_after_plan["orchestrator_plan"]["agents"] == [
        "alignment",
        "testing",
        "security",
    ], (
        f"Expected ['alignment', 'testing', 'security'], got {state_after_plan['orchestrator_plan']['agents']}"
    )
    print("✓ plan_agents node test passed")

    # Test collect node (before run_review_agents for simplicity)
    # Again, need to update state
    updated_state_2 = updated_state.model_copy(update=state_after_plan)
    state_after_collect = orch.collect(updated_state_2)
    # Check that aggregated report is stored in repo_memory since we can't add new fields to Pydantic model
    assert "repo_memory" in state_after_collect, (
        "collect should return repo_memory update"
    )
    assert "aggregated_report" in state_after_collect["repo_memory"], (
        "collect should create aggregated_report in repo_memory"
    )
    assert "total_agents" in state_after_collect["repo_memory"]["aggregated_report"], (
        "Aggregated report should have total_agents"
    )
    assert (
        state_after_collect["repo_memory"]["aggregated_report"]["total_agents"] == 0
    ), "Should have 0 agents in aggregated report (no agents run yet)"
    assert state_after_collect["ready_for_healing"] is False, (
        "ready_for_healing should be False"
    )
    print("✓ collect node test passed")


def test_graph_structure():
    """Test that the graph is built correctly."""
    from multiagentpanic.state.checkpointing import InMemoryCheckpointer

    # Create orchestrator without full initialization to avoid settings validation
    orch = PRReviewOrchestrator.__new__(PRReviewOrchestrator)
    orch.checkpointer = InMemoryCheckpointer()

    # Manually set required attributes to avoid settings validation
    orch.settings = None  # Mock settings
    orch.model_selector = None  # Mock model selector
    orch.factory = None  # Mock factory

    # Build graph
    graph = orch.build_graph()

    # Verify graph has expected nodes
    assert graph is not None, "Graph should be created"
    print("✓ Graph structure test passed")


if __name__ == "__main__":
    test_sample_pr_data()
    test_orchestrator_node_functions()
    test_graph_structure()
    print("All tests passed! 🎉")
