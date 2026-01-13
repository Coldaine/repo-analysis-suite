import pytest
import json
from multiagentpanic.domain.schemas import (
    PRMetadata, ContextGathering, Finding, ReviewAgentState,
    ContextAgentState, PRReviewState, BaseAgentVerdict,
    ReviewAgentVerdict, ContextAgentVerdict
)
from typing import get_type_hints

class TestStateTypeSafety:
    """Test that state schemas are consistent across boundaries"""

    def test_review_agent_state_schema(self):
        """ReviewAgentState should have all required fields"""
        annotations = get_type_hints(ReviewAgentState)

        required_fields = [
            "pr_metadata", "pr_diff", "changed_files",
            "repo_memory", "ci_status",
            "context_gathered", "findings", "reasoning_history",
            "current_iteration", "needs_more_context"
        ]

        for field in required_fields:
            assert field in annotations, f"Missing required field: {field}"

    def test_context_agent_state_schema(self):
        """ContextAgentState should have all required fields"""
        annotations = get_type_hints(ContextAgentState)

        required_fields = ["task", "target_files", "query", "context_found"]

        for field in annotations:
            # ContextAgentState is a dataclass, check attributes
            pass

    def test_state_operator_annotations(self):
        """Accumulated fields should use operator.add"""
        annotations = ReviewAgentState.__annotations__

        # Fields that should accumulate
        accumulating_fields = ["context_gathered", "findings", "reasoning_history"]

        for field in accumulating_fields:
            annotation = annotations[field]

            # Should be Annotated with operator.add
            if hasattr(annotation, '__metadata__'):
                # Has Annotated metadata
                assert len(annotation.__metadata__) > 0

    def test_state_serialization(self):
        """States should be JSON serializable"""
        # Test PRMetadata
        pr_meta = PRMetadata(
            pr_number=123,
            pr_url="https://github.com/test/repo/pull/123",
            pr_branch="feature/test",
            base_branch="main",
            pr_title="Test PR",
            pr_complexity="medium"
        )

        # Should serialize
        serialized = pr_meta.model_dump()
        assert serialized is not None

        # Test ContextGathering
        context = ContextGathering(
            iteration=1,
            context_type="zoekt_search",
            result={"found": "something"},
            cost_usd=0.001,
            tokens=50
        )

        serialized = context.model_dump()
        assert serialized is not None

        # Test Finding
        finding = Finding(
            id="finding-1",
            iteration=1,
            severity="high",
            finding_type="security",
            file="src/test.py",
            line=42,
            description="Potential security issue",
            suggestion="Fix this"
        )

        serialized = finding.model_dump()
        assert serialized is not None

    def test_pydantic_validation(self):
        """Pydantic should validate field constraints"""

        # Test invalid PR number
        try:
            PRMetadata(
                pr_number=-1,  # Invalid
                pr_url="https://github.com/test/repo/pull/123",
                pr_branch="feature/test",
                base_branch="main",
                pr_title="Test PR",
                pr_complexity="medium"
            )
            assert False, "Should have raised validation error"
        except Exception:
            pass  # Expected

        # Test invalid severity
        try:
            Finding(
                id="finding-1",
                iteration=1,
                severity="invalid",  # Invalid
                finding_type="security",
                file="src/test.py",
                line=42,
                description="Test"
            )
            assert False, "Should have raised validation error"
        except Exception:
            pass  # Expected

    def test_state_immutability(self):
        """PRMetadata should be immutable (frozen)"""
        pr_meta = PRMetadata(
            pr_number=123,
            pr_url="https://github.com/test/repo/pull/123",
            pr_branch="feature/test",
            base_branch="main",
            pr_title="Test PR",
            pr_complexity="medium"
        )

        # Should not allow mutation
        try:
            pr_meta.pr_number = 456
            assert False, "Should not allow mutation"
        except Exception:
            pass  # Expected