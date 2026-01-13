from typing import Dict, Any, List, Type
import json
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage
from langgraph.prebuilt import create_react_agent
from langgraph.graph import StateGraph

from multiagentpanic.domain.schemas import BaseAgentVerdict
from multiagentpanic.tools import list_files, read_file, search_codebase

def create_jit_agent(
    llm: BaseChatModel,
    system_prompt: str,
    output_schema: Type[BaseAgentVerdict],
    name: str
):
    """
    Creates a ReAct agent (Agent + Tools) using langgraph.prebuilt.create_react_agent.
    The agent is equipped with JIT file system tools.
    It returns a callable that accepts state, runs the agent loop, and extracts the final JSON verdict.
    """

    # Define the tools available to the agent
    tools = [list_files, read_file, search_codebase]
    
    # Create the agent graph (Agent -> Tools -> Agent loop)
    agent_executor = create_react_agent(llm, tools, messages_modifier=system_prompt)

    def agent_wrapper(context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Wrapper to bridge the main graph's state with the ReAct agent's execution.
        """
        # Initial user message to kick off the investigation
        # We prompt the agent to start exploring the codebase.
        initial_message = HumanMessage(
            content="Begin your investigation of the repository. Use the available tools (list_files, read_file, search_codebase) to explore the code. When you have gathered enough information, output the final JSON verdict as specified in your system prompt."
        )
        
        try:
            # Run the agent loop
            # The input to create_react_agent is typically a dict with "messages"
            result = agent_executor.invoke({"messages": [initial_message]})
            
            # Extract the final response from the agent
            # result["messages"] contains the full conversation history
            messages: List[BaseMessage] = result["messages"]
            final_message = messages[-1]
            raw_output = final_message.content
            
            if not isinstance(raw_output, str):
                 # Handle cases where content might be a list (e.g. Claude with tool use blocks)
                 # Typically the final message after tool use is text.
                 raw_output = str(raw_output)

            # Attempt to extract JSON
            json_start = raw_output.find("```json")
            json_end = raw_output.find("```", json_start + 1)
            
            if json_start != -1 and json_end != -1:
                json_str = raw_output[json_start + len("```json"):json_end].strip()
            else:
                # Fallback: try to find the first { and last }
                start = raw_output.find("{")
                end = raw_output.rfind("}")
                if start != -1 and end != -1:
                     json_str = raw_output[start:end+1]
                else:
                     json_str = raw_output # Hope for the best

            # Validate against schema
            parsed_data = json.loads(json_str)
            verdict_model = output_schema.model_validate(parsed_data)
            
            return {
                "verdict": verdict_model.model_dump(),
                "raw_output": raw_output,
                "error": None
            }

        except Exception as e:
            # Catch-all for tool errors, parsing errors, or context limit errors
            error_msg = f"Agent {name} failed: {e}"
            # print(error_msg) # Optional logging
            return {
                "verdict": None,
                "raw_output": str(e),
                "error": error_msg
            }

    return agent_wrapper