from typing import List, TypedDict, Optional, Dict, Any

# Represents the state of a single agent's review
class AgentReview(TypedDict):
    verdict: Optional[Dict[str, Any]] # Pydantic model will be stored here later
    raw_output: str # Raw LLM output for debugging
    error: Optional[str] # Any error encountered by the agent

# The overall state for the LangGraph workflow
class ReviewState(TypedDict):
    # Input
    repo_path: str # Path to the repository being reviewed
    pr_diff: Optional[str] # The pull request diff content
    issue_description: Optional[str] # Description of the issue/feature for context

    # Agent Outputs
    test_agent_review: Optional[AgentReview]
    docs_agent_review: Optional[AgentReview]
    code_agent_review: Optional[AgentReview]
    scope_agent_review: Optional[AgentReview]

    # Aggregated / Final Output
    final_report: Optional[str]
    errors: List[str]
