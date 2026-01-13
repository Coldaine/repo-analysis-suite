#!/usr/bin/env python3
import os
import sys
import json
import httpx
import logging

from memori import recall, remember
from py2neo import Graph
from mcp_client import MCPClient

logging.basicConfig(
    level=os.getenv("OBS_AGENT_LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class LLMClient:
    """
    Simple LLM client that integrates with MCP.
    Compatible with OpenAI-compatible APIs (Goose AI, OpenAI, etc.)
    """
    def __init__(self, api_key: str, model: str, base_url: str = "https://api.goose.ai/v1"):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.client = httpx.Client(timeout=30.0)
        self.mcp_client = None

    def ask(self, prompt: str, mcp_url: str | None = None) -> str:
        """
        Send a prompt to the LLM and execute tools via MCP if needed.

        Args:
            prompt: The prompt to send to the LLM
            mcp_url: Optional MCP server URL for tool execution

        Returns:
            LLM response or tool execution result
        """
        # Initialize MCP client if URL provided
        if mcp_url and not self.mcp_client:
            try:
                self.mcp_client = MCPClient(mcp_url)
                # Verify connection
                if not self.mcp_client.health_check():
                    logger.warning(f"MCP server at {mcp_url} is not responding, continuing without MCP")
                    self.mcp_client = None
            except Exception as e:
                logger.error(f"Failed to initialize MCP client: {e}")
                self.mcp_client = None

        # Get available tools
        tools = []
        if self.mcp_client:
            tools = self.mcp_client.list_tools()
            if tools:
                logger.info(f"Available MCP tools: {[t.get('name', 'unknown') for t in tools]}")

        # Build system prompt with tool information
        system_content = "You are an observability control plane agent."
        if tools:
            system_content += f"\n\nAvailable tools: {json.dumps(tools, indent=2)}"
            system_content += "\n\nTo use a tool, respond with JSON in this format:"
            system_content += '\n{"tool": "tool_name", "arguments": {...}}'
            system_content += "\n\nOnly use tools when necessary to resolve the issue."

        # Call LLM
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7
        }

        try:
            response = self.client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            llm_response = data["choices"][0]["message"]["content"]

            # Check if LLM wants to use a tool
            if self.mcp_client and llm_response.strip().startswith("{"):
                try:
                    tool_request = json.loads(llm_response)
                    if "tool" in tool_request:
                        logger.info(f"Executing tool: {tool_request['tool']}")
                        tool_result = self.mcp_client.call_tool(
                            tool_request["tool"],
                            tool_request.get("arguments", {})
                        )

                        # Format the response to include both the tool call and result
                        formatted_response = f"Tool executed: {tool_request['tool']}\n"
                        formatted_response += f"Arguments: {json.dumps(tool_request.get('arguments', {}), indent=2)}\n"
                        formatted_response += f"Result: {json.dumps(tool_result, indent=2)}"

                        return formatted_response
                except json.JSONDecodeError:
                    # Not a tool request, return as text
                    pass

            return llm_response

        except Exception as e:
            logger.error(f"LLM API call failed: {e}")
            return f"ERROR: LLM call failed: {e}"

    def __del__(self):
        if self.mcp_client:
            self.mcp_client.close()
        self.client.close()


# LLM client - uses Goose AI by default, configurable via env
llm_client = LLMClient(
    api_key=os.getenv("GOOSEAI_API_KEY", ""),
    model=os.getenv("GOOSE_MODEL", "gpt-neo-20b"),
    base_url=os.getenv("LLM_BASE_URL", "https://api.goose.ai/v1")
)

# Neo4j client - credentials from environment
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")

if not NEO4J_PASSWORD:
    logger.warning("NEO4J_PASSWORD not set, graph operations will fail")

graph = Graph(NEO4J_URI, auth=("neo4j", NEO4J_PASSWORD))

# Load master control-plane prompt
CONTROL_PLANE_PROMPT_PATH = os.path.join(BASE_DIR, "prompts", "control-plane.md")
with open(CONTROL_PLANE_PROMPT_PATH, encoding="utf-8") as f:
    CONTROL_PLANE_PROMPT = f.read()


def build_prompt(issue: str) -> str:
    """
    Build the prompt sent to Goose, including current state + past fixes.
    """
    history = recall(f"issue:{issue}", limit=10)

    try:
        state = httpx.get(
            "http://localhost:5555/api/state",
            timeout=2.0
        ).json()
    except Exception as e:
        state = {
            "error": f"dashboard unreachable: {e.__class__.__name__}: {e}"
        }

    return f"""{CONTROL_PLANE_PROMPT}

## Current State
{json.dumps(state, indent=2)}

## Past Similar Fixes
{history}

Task: {issue}
"""


def main() -> None:
    issue = sys.argv[1] if len(sys.argv) > 1 else "periodic-health-check"

    if "--dry-run" in sys.argv:
        print("DRY RUN MODE")
        print(build_prompt(issue))
        return

    prompt = build_prompt(issue)

    # MCP URL wired via env (or pass explicitly)
    mcp_url = os.getenv("MCP_URL", "http://host.docker.internal:8433")

    logger.info(f"Processing issue: {issue}")
    response = llm_client.ask(prompt, mcp_url=mcp_url)
    print(response)

    # Heuristic: if response looks like it did something, remember it
    if any(
        kw in response.lower()
        for kw in ("fixed", "restarted", "synced", "pruned", "resolved")
    ):
        remember(
            f"issue:{issue}",
            response,
            metadata={"server": os.uname().nodename},
        )
        graph.run(
            "CREATE (f:Fix {issue:$issue, solution:$solution, ts:timestamp()})",
            issue=issue,
            solution=response,
        )


if __name__ == "__main__":
    main()
