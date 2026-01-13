from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Any, Literal, Optional
from datetime import datetime
import operator
from typing import Annotated

# ═══════════════════════════════════════════════════════════════
# METADATA MODELS
# ═══════════════════════════════════════════════════════════════

class PRMetadata(BaseModel):
    """Type-safe PR metadata with validation"""

    model_config = ConfigDict(frozen=True)  # Immutable

    pr_number: int = Field(gt=0)
    pr_url: str = Field(pattern=r"https://github\.com/.+/pull/\d+")
    pr_branch: str = Field(min_length=1)
    base_branch: str = Field(min_length=1)
    pr_title: str = Field(min_length=1, max_length=500)
    pr_complexity: Literal["simple", "medium", "complex"]
    pr_body: Optional[str] = None
    pr_diff: Optional[str] = None


# ═══════════════════════════════════════════════════════════════
# CONTEXT GATHERING MODELS
# ═══════════════════════════════════════════════════════════════

class ContextGathering(BaseModel):
    """Type-safe context gathering result"""

    iteration: int = Field(ge=1)
    context_type: Literal["zoekt_search", "lsp_analysis", "git_history", "test_coverage"]
    result: Dict[str, Any]
    cost_usd: float = Field(ge=0)
    tokens: int = Field(ge=0)
    timestamp: datetime = Field(default_factory=datetime.now)


# ═══════════════════════════════════════════════════════════════
# FINDING MODELS
# ═══════════════════════════════════════════════════════════════

class Finding(BaseModel):
    """Type-safe review finding"""

    id: str
    iteration: int
    severity: Literal["high", "medium", "low"]
    finding_type: Literal["type_error", "bug", "security", "performance", "style", "architecture", "dependency"]
    file: str
    line: int = Field(ge=1)
    description: str = Field(min_length=10)
    suggestion: Optional[str] = None
    code_snippet: Optional[str] = None


# ═══════════════════════════════════════════════════════════════
# AGENT VERDICT MODELS
# ═══════════════════════════════════════════════════════════════

class BaseAgentVerdict(BaseModel):
    """Base verdict structure for all agents"""

    verdict: Literal["PASS", "WARN", "FAIL", "NEEDS_WORK"]
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str = Field(min_length=10)


class ReviewAgentVerdict(BaseAgentVerdict):
    """Verdict from review agents"""

    specialty: Literal["alignment", "dependencies", "testing", "security"]
    findings: List[Finding]
    context_gathered: List[ContextGathering]
    iterations_used: int = Field(ge=1)
    needs_more_context: bool = False


class ContextAgentVerdict(BaseAgentVerdict):
    """Verdict from context agents"""

    context_type: Literal["zoekt_search", "lsp_analysis", "git_history", "test_coverage"]
    raw_data: Dict[str, Any]
    processed_summary: str


# ═══════════════════════════════════════════════════════════════
# WORKFLOW MODELS
# ═══════════════════════════════════════════════════════════════

class WorkflowRequest(BaseModel):
    """Request for workflow agent"""

    request_id: str
    requesting_agent: str
    request_type: Literal["run_ci", "get_test_results", "run_specific_test"]
    params: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)
    status: Literal["pending", "in_progress", "completed", "failed"] = "pending"
    result: Optional[Dict[str, Any]] = None


class CIStatus(BaseModel):
    """CI/test execution status"""

    triggered_by: str
    status: Literal["pending", "running", "success", "failure"]
    tests_passed: Optional[bool] = None
    coverage_percentage: Optional[float] = None
    test_results: Optional[Dict[str, Any]] = None
    duration_seconds: Optional[int] = None


# ═══════════════════════════════════════════════════════════════
# STATE MODELS
# ═══════════════════════════════════════════════════════════════

class ReviewAgentState(BaseModel):
    """
    State for individual review agent subgraph.
    Accumulates context and findings across iterations.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # ═══ Inherited (read-only) ═══
    pr_metadata: PRMetadata
    pr_diff: str
    changed_files: List[str]
    repo_memory: Dict[str, Any]
    ci_status: Optional[CIStatus] = None

    # ═══ Agent Identity (set once) ═══
    specialty: Literal["alignment", "dependencies", "testing", "security"]
    agent_id: str
    marching_orders: str

    # ═══ ACCUMULATED STATE (grows over iterations) ═══
    context_gathered: Annotated[List[ContextGathering], operator.add] = Field(default_factory=list)
    findings: Annotated[List[Finding], operator.add] = Field(default_factory=list)
    reasoning_history: Annotated[List[str], operator.add] = Field(default_factory=list)

    # ═══ Iteration State (resets each iteration) ═══
    current_iteration: int = Field(default=1, ge=1)
    context_requests_this_iteration: List[Dict[str, Any]] = Field(default_factory=list)
    needs_more_context: bool = False

    # ═══ Final Output ═══
    final_report: Optional[ReviewAgentVerdict] = None


class ContextAgentState(BaseModel):
    """State for disposable context agents"""

    task: str
    target_files: List[str]
    query: str

    # Results
    context_found: Dict[str, Any]
    cost: float
    tokens: int


class PRReviewState(BaseModel):
    """
    Root state for the entire PR review orchestration.
    Shared across all agents and rounds.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # ═══ PR Context ═══
    pr_metadata: PRMetadata
    pr_diff: str
    changed_files: List[str]
    pr_complexity: str

    # ═══ Memory Context ═══
    repo_memory: Dict[str, Any]
    similar_prs: List[Dict[str, Any]]
    repo_conventions: List[str]

    # ═══ Orchestrator Decisions ═══
    orchestrator_plan: Dict[str, Any]
    ab_test_variant: str = "default"

    # ═══ Workflow Agent State ═══
    ci_status: Optional[CIStatus] = None
    ci_triggered_by: Optional[str] = None

    # ═══ Review Agent Results (Accumulated) ═══
    review_agent_reports: Annotated[List[ReviewAgentVerdict], operator.add] = Field(default_factory=list)

    # ═══ Context Gathering Results ═══
    context_cache: Dict[str, Any] = Field(default_factory=dict)

    # ═══ Handoff to Healing ═══
    ready_for_healing: bool = False
    healing_approved_tasks: List[Dict[str, Any]] = Field(default_factory=list)

    # ═══ Tracking ═══
    tokens_used: Annotated[int, operator.add] = 0
    agents_spawned: Annotated[List[str], operator.add] = Field(default_factory=list)
    total_cost_usd: Annotated[float, operator.add] = 0.0

    orchestration_metadata: Dict[str, Any] = Field(default_factory=dict)
    agent_execution_times: Dict[str, float] = Field(default_factory=dict)

    # ═══ Timing ═══
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
