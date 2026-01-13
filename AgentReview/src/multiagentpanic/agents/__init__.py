from langchain_core.language_models import BaseChatModel
from multiagentpanic.agents.core import create_jit_agent
from multiagentpanic.agents.prompts import (
    TEST_KILLER_AGENT_PROMPT,
    DOCS_EDITOR_AGENT_PROMPT,
    CODE_JANITOR_AGENT_PROMPT,
    SCOPE_POLICE_AGENT_PROMPT,
)
from multiagentpanic.domain.schemas import (
    ReviewAgentVerdict,
)

# Workflow Agent exports
from multiagentpanic.agents.workflow_agent import (
    WorkflowAgent,
    get_workflow_agent,
    GitHubClient,
)
from multiagentpanic.agents.workflow_queue import (
    WorkflowQueue,
    get_workflow_queue,
)

def get_test_killer_agent(llm: BaseChatModel):
    return create_jit_agent(
        llm=llm,
        system_prompt=TEST_KILLER_AGENT_PROMPT,
        output_schema=ReviewAgentVerdict,
        name="Test Killer Agent"
    )

def get_docs_editor_agent(llm: BaseChatModel):
    return create_jit_agent(
        llm=llm,
        system_prompt=DOCS_EDITOR_AGENT_PROMPT,
        output_schema=ReviewAgentVerdict,
        name="Docs Editor Agent"
    )

def get_code_janitor_agent(llm: BaseChatModel):
    return create_jit_agent(
        llm=llm,
        system_prompt=CODE_JANITOR_AGENT_PROMPT,
        output_schema=ReviewAgentVerdict,
        name="Code Janitor Agent"
    )

def get_scope_police_agent(llm: BaseChatModel):
    return create_jit_agent(
        llm=llm,
        system_prompt=SCOPE_POLICE_AGENT_PROMPT,
        output_schema=ReviewAgentVerdict,
        name="Scope Police Agent"
    )