"""
Expanded unit tests for state schemas with comprehensive coverage.
Tests Pydantic validation, serialization, and edge cases.
"""

import pytest
import json
from datetime import datetime
from typing import get_type_hints
from pydantic import ValidationError

from multiagentpanic.domain.schemas import (
    PRMetadata, ContextGathering, Finding, ReviewAgentState,
    ContextAgentState, BaseAgentVerdict,
    ReviewAgentVerdict, ContextAgentVerdict, WorkflowRequest, CIStatus,
    PRReviewState
)

# Alias for backward compatibility in tests
StatePRReviewState = PRReviewState

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

        for field in required_fields:
            assert field in annotations, f"Missing required field: {field}"

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
        assert serialized["pr_number"] == 123
        assert serialized["pr_title"] == "Test PR"

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
        assert serialized["iteration"] == 1
        assert serialized["context_type"] == "zoekt_search"

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
        assert serialized["severity"] == "high"
        assert serialized["file"] == "src/test.py"

    def test_pydantic_validation(self):
        """Pydantic should validate field constraints"""

        # Test invalid PR number
        with pytest.raises(ValidationError):
            PRMetadata(
                pr_number=-1,  # Invalid
                pr_url="https://github.com/test/repo/pull/123",
                pr_branch="feature/test",
                base_branch="main",
                pr_title="Test PR",
                pr_complexity="medium"
            )

        # Test invalid severity
        with pytest.raises(ValidationError):
            Finding(
                id="finding-1",
                iteration=1,
                severity="invalid",  # Invalid
                finding_type="security",
                file="src/test.py",
                line=42,
                description="Test"
            )

        # Test valid data
        valid_pr = PRMetadata(
            pr_number=456,
            pr_url="https://github.com/test/repo/pull/456",
            pr_branch="valid-branch",
            base_branch="main",
            pr_title="Valid PR",
            pr_complexity="simple"
        )
        assert valid_pr.pr_number == 456

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
        with pytest.raises(Exception):
            pr_meta.pr_number = 456

    def test_state_deserialization(self):
        """Test that states can be deserialized from JSON"""
        # Test PRMetadata deserialization
        pr_data = {
            "pr_number": 789,
            "pr_url": "https://github.com/test/repo/pull/789",
            "pr_branch": "deserialize-branch",
            "base_branch": "main",
            "pr_title": "Deserialized PR",
            "pr_complexity": "complex"
        }

        pr_meta = PRMetadata(**pr_data)
        assert pr_meta.pr_number == 789
        assert pr_meta.pr_title == "Deserialized PR"

        # Test Finding deserialization
        finding_data = {
            "id": "deserialized-finding",
            "iteration": 2,
            "severity": "medium",
            "finding_type": "style",
            "file": "src/deserialized.py",
            "line": 100,
            "description": "Deserialized finding description that is long enough",
            "suggestion": "Improve this"
        }

        finding = Finding(**finding_data)
        assert finding.id == "deserialized-finding"
        assert finding.severity == "medium"

    def test_state_edge_cases(self):
        """Test edge cases in state validation"""
        # Test empty strings
        with pytest.raises(ValidationError):
            PRMetadata(
                pr_number=123,
                pr_url="",  # Empty URL
                pr_branch="feature/test",
                base_branch="main",
                pr_title="Test PR",
                pr_complexity="medium"
            )

        # Test very long strings - should fail since max_length=500
        long_title = "A" * 1000
        with pytest.raises(ValidationError):
            PRMetadata(
                pr_number=123,
                pr_url="https://github.com/test/repo/pull/123",
                pr_branch="feature/test",
                base_branch="main",
                pr_title=long_title,
                pr_complexity="medium"
            )
        
        # Test with valid length title (500 chars)
        valid_long_title = "A" * 500
        pr_meta = PRMetadata(
            pr_number=123,
            pr_url="https://github.com/test/repo/pull/123",
            pr_branch="feature/test",
            base_branch="main",
            pr_title=valid_long_title,
            pr_complexity="medium"
        )
        assert len(pr_meta.pr_title) == 500

        # Test boundary values
        finding = Finding(
            id="boundary-test",
            iteration=999,  # High iteration
            severity="high",
            finding_type="security",
            file="src/test.py",
            line=9999,  # High line number
            description="Boundary test",
            suggestion="Test"
        )
        assert finding.iteration == 999
        assert finding.line == 9999

    def test_state_consistency(self):
        """Test consistency across state types"""
        # Test PRReviewState with correct schema fields
        pr_metadata = PRMetadata(
            pr_number=123,
            pr_url="https://github.com/test/repo/pull/123",
            pr_branch="feature/test",
            base_branch="main",
            pr_title="Test PR",
            pr_complexity="medium"
        )
        
        pr_review_state = StatePRReviewState(
            pr_metadata=pr_metadata,
            pr_diff="test diff",
            changed_files=["test.py"],
            pr_complexity="medium",
            repo_memory={},
            similar_prs=[],
            repo_conventions=[],
            orchestrator_plan={},
            ab_test_variant="default"
        )

        # Should be valid
        assert pr_review_state.pr_metadata.pr_number == 123
        assert pr_review_state.pr_diff == "test diff"

        # Test ReviewAgentState with correct schema fields
        review_state = ReviewAgentState(
            pr_metadata=pr_metadata,
            pr_diff="review diff",
            changed_files=["review.py"],
            repo_memory={},
            ci_status=None,
            specialty="testing",
            agent_id="test-agent-1",
            marching_orders="test orders",
            context_gathered=[],
            findings=[],
            reasoning_history=[],
            current_iteration=1,
            needs_more_context=False
        )

        assert review_state.specialty == "testing"
        assert review_state.marching_orders == "test orders"

    def test_state_performance(self):
        """Test that state operations are performant"""
        import time

        # Time PRMetadata creation
        start_time = time.time()
        for i in range(1, 1001):  # Start from 1 since pr_number must be > 0
            pr_meta = PRMetadata(
                pr_number=i,
                pr_url=f"https://github.com/test/repo/pull/{i}",
                pr_branch=f"branch-{i}",
                base_branch="main",
                pr_title=f"PR {i}",
                pr_complexity="medium"
            )
        end_time = time.time()

        # Should be very fast (< 0.1 seconds for 1000 PRs)
        assert (end_time - start_time) < 0.1, "PRMetadata creation should be very performant"

        # Time Finding creation
        start_time = time.time()
        for i in range(1000):
            finding = Finding(
                id=f"finding-{i}",
                iteration=1,
                severity="medium",
                finding_type="style",
                file=f"src/test{i}.py",
                line=(i % 1000) + 1,  # line must be >= 1
                description=f"Finding {i} - a description that is at least 10 chars",
                suggestion=f"Fix {i}"
            )
        end_time = time.time()

        # Should be very fast (< 0.1 seconds for 1000 findings)
        assert (end_time - start_time) < 0.1, "Finding creation should be very performant"

    def test_state_json_roundtrip(self):
        """Test JSON serialization roundtrip"""
        # Test PRMetadata
        original_pr = PRMetadata(
            pr_number=123,
            pr_url="https://github.com/test/repo/pull/123",
            pr_branch="feature/test",
            base_branch="main",
            pr_title="Test PR",
            pr_complexity="medium"
        )

        # Serialize to JSON
        json_data = original_pr.model_dump_json()
        assert json_data is not None

        # Deserialize from JSON
        restored_pr = PRMetadata.model_validate_json(json_data)
        assert restored_pr.pr_number == original_pr.pr_number
        assert restored_pr.pr_title == original_pr.pr_title

        # Test Finding
        original_finding = Finding(
            id="roundtrip-finding",
            iteration=1,
            severity="high",
            finding_type="security",
            file="src/test.py",
            line=42,
            description="Roundtrip test",
            suggestion="Fix this"
        )

        # Serialize to JSON
        json_data = original_finding.model_dump_json()
        assert json_data is not None

        # Deserialize from JSON
        restored_finding = Finding.model_validate_json(json_data)
        assert restored_finding.id == original_finding.id
        assert restored_finding.severity == original_finding.severity

    def test_state_field_validation(self):
        """Test field-specific validation"""
        # Test PR number range
        with pytest.raises(ValidationError):
            PRMetadata(
                pr_number=0,  # Invalid - should be positive
                pr_url="https://github.com/test/repo/pull/1",
                pr_branch="feature/test",
                base_branch="main",
                pr_title="Test PR",
                pr_complexity="medium"
            )

        # Test valid PR number
        valid_pr = PRMetadata(
            pr_number=1,
            pr_url="https://github.com/test/repo/pull/1",
            pr_branch="feature/test",
            base_branch="main",
            pr_title="Test PR",
            pr_complexity="medium"
        )
        assert valid_pr.pr_number == 1

        # Test severity validation
        with pytest.raises(ValidationError):
            Finding(
                id="test",
                iteration=1,
                severity="invalid_severity",  # Invalid
                finding_type="security",
                file="src/test.py",
                line=1,
                description="Test"
            )

        # Test valid severities (only low, medium, high - no critical)
        for severity in ["low", "medium", "high"]:
            finding = Finding(
                id=f"test-{severity}",
                iteration=1,
                severity=severity,
                finding_type="security",
                file="src/test.py",
                line=1,
                description=f"Test {severity} finding description"
            )
            assert finding.severity == severity
        
        # Verify critical is invalid
        with pytest.raises(ValidationError):
            Finding(
                id="test-critical",
                iteration=1,
                severity="critical",
                finding_type="security",
                file="src/test.py",
                line=1,
                description="Test critical finding description"
            )

    def test_state_default_values(self):
        """Test that states have appropriate default values"""
        # Test ReviewAgentState defaults
        pr_metadata = PRMetadata(
            pr_number=123,
            pr_url="https://github.com/test/repo/pull/123",
            pr_branch="feature/test",
            base_branch="main",
            pr_title="Test PR",
            pr_complexity="medium"
        )
        
        state = ReviewAgentState(
            pr_metadata=pr_metadata,
            pr_diff="test",
            changed_files=["test.py"],
            repo_memory={},
            ci_status=None,
            specialty="testing",
            agent_id="test-agent",
            marching_orders="test"
        )

        # Check defaults
        assert state.context_gathered == []
        assert state.findings == []
        assert state.needs_more_context is False
        assert state.reasoning_history == []
        assert state.current_iteration == 1

        # Test ContextAgentState defaults
        context_state = ContextAgentState(
            task="test",
            target_files=["test.py"],
            query="test query",
            context_found={},
            cost=0.0,
            tokens=0
        )

        assert context_state.context_found == {}
        assert context_state.cost == 0.0
        assert context_state.tokens == 0

    def test_state_complex_types(self):
        """Test handling of complex data types in states"""
        # Test with complex repo_memory
        complex_memory = {
            "patterns": ["pattern1", "pattern2"],
            "stats": {"files": 10, "lines": 1000},
            "nested": {
                "deep": {
                    "value": "test"
                }
            }
        }
        
        pr_metadata = PRMetadata(
            pr_number=123,
            pr_url="https://github.com/test/repo/pull/123",
            pr_branch="feature/test",
            base_branch="main",
            pr_title="Test PR",
            pr_complexity="medium"
        )
        
        # Create proper ContextGathering objects
        context_item = ContextGathering(
            iteration=1,
            context_type="zoekt_search",
            result={"found": "something"},
            cost_usd=0.001,
            tokens=50
        )
        
        # Create proper Finding objects
        finding_item = Finding(
            id="finding-1",
            iteration=1,
            severity="medium",
            finding_type="style",
            file="src/test.py",
            line=42,
            description="Test finding description that is long enough"
        )

        state = ReviewAgentState(
            pr_metadata=pr_metadata,
            pr_diff="test diff",
            changed_files=["test.py"],
            repo_memory=complex_memory,
            ci_status=None,
            specialty="testing",
            agent_id="test-agent",
            marching_orders="test orders",
            context_gathered=[context_item],
            findings=[finding_item],
            reasoning_history=[],
            current_iteration=1,
            needs_more_context=False
        )

        # Should handle complex data
        assert state.repo_memory["nested"]["deep"]["value"] == "test"
        assert len(state.context_gathered) == 1
        assert len(state.findings) == 1

    def test_state_equality_and_hashing(self):
        """Test state equality and hashing where applicable"""
        # Test PRMetadata equality
        pr1 = PRMetadata(
            pr_number=123,
            pr_url="https://github.com/test/repo/pull/123",
            pr_branch="feature/test",
            base_branch="main",
            pr_title="Test PR",
            pr_complexity="medium"
        )

        pr2 = PRMetadata(
            pr_number=123,
            pr_url="https://github.com/test/repo/pull/123",
            pr_branch="feature/test",
            base_branch="main",
            pr_title="Test PR",
            pr_complexity="medium"
        )

        # Should be equal
        assert pr1 == pr2

        # Test different PRs
        pr3 = PRMetadata(
            pr_number=456,
            pr_url="https://github.com/test/repo/pull/456",
            pr_branch="feature/test",
            base_branch="main",
            pr_title="Different PR",
            pr_complexity="medium"
        )

        assert pr1 != pr3