from typing import List, Dict, Annotated, Literal
from pydantic import BaseModel, Field, validator
import enum
from datetime import datetime
from functools import partial
from langgraph.graph import StateGraph, END
from .checkpointing import PostgresCheckpointSaver

class PRReviewState(BaseModel):
    """Root state shared across all agents"""
    
    pr_number: int = Field(description="PR number")
    pr_diff: str
    pr_body: str
    changed_files: List[str]
    pr_complexity: str
    
    repo_memory: Dict = Field(default_factory=dict, description="Past learnings about this repo")
    similar_prs: List[Dict] = Field(default_factory=list)
    
    orchestrator_plan: Dict = Field(default_factory=dict)
    ab_test_variant: str
    
    ci_status: Dict = Field(default_factory=dict)
    ci_triggered_by: str
    
    review_agent_reports: List[Dict] = Field(default_factory=list)
    context_cache: Dict[str, any] = Field(default_factory=dict)
    
    ready_for_healing: bool = Field(default=False)
    healing_approved_tasks: List[Dict] = Field(default_factory=list)
    
    tokens_used: Annotated[int, Field(default=0)]
    agents_spawned: Annotated[List[str], Field(default_factory=list)]

class ReviewAgentState(BaseModel):
    """State specific to each review agent subgraph"""
    
    pr_diff: str
    changed_files: List[str]
    repo_memory: Dict
    ci_status: Dict
    context_cache: Dict[str, any]
    specialty: str = Field(description="Agent's domain or subgraph type")
    marching_orders: str
    context_requests: List[Dict] = Field(default_factory=list)
    context_gathered: List[Dict] = Field(default_factory=list)
    findings: List[Dict] = Field(default_factory=list)
    iterations: int = Field(default=1)
    needs_more_context: bool = Field(default=False)
    cost_usd: float = Field(default=0)
    tokens: int = Field(default=0)

class ContextAgentState(BaseModel):
    """State for disposable context agents"""
    
    task: str = Field(description="Context gathering task type")
    target_files: List[str]
    query: str
    context_found: Dict = Field(default_factory=dict)
    cost_usd: float = Field(default=0)
    tokens: int = Field(default=0)