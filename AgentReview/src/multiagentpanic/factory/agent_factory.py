from typing import Dict, Any, List, Literal, Optional
from langgraph.graph import StateGraph, END
from functools import partial
import json
import asyncio
import logging
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool

from multiagentpanic.domain.schemas import (
    ReviewAgentState, ContextAgentState, ContextGathering, Finding,
    ReviewAgentVerdict, ContextAgentVerdict
)
from multiagentpanic.factory.model_pools import ModelSelector, ModelPool, ModelTier
from multiagentpanic.factory.prompts import REVIEW_AGENT_TEMPLATES, CONTEXT_AGENT_TEMPLATES
from multiagentpanic.factory.llm_factory import LLMFactory
from multiagentpanic.config.settings import get_settings
from multiagentpanic.tools.mcp_tools import MCPToolProvider, get_mcp_tool_provider
import redis
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import aiohttp

# Configure logging
logger = logging.getLogger(__name__)

class AgentFactory:
    """Dynamically composes agents from templates"""

    def __init__(self, model_selector: ModelSelector, mcp_provider: Optional[MCPToolProvider] = None):
        self.model_selector = model_selector
        self.settings = get_settings()
        self.llm_factory = LLMFactory(self.settings)
        self._redis_client = None
        self._context_cache_ttl = getattr(self.settings, 'context_cache_ttl', 3600)  # Default 1 hour
        self._mcp_provider = mcp_provider or get_mcp_tool_provider()
        self._mcp_tools: Optional[List[BaseTool]] = None

    async def get_mcp_tools(self) -> List[BaseTool]:
        """
        Get MCP tools lazily initialized via langchain-mcp-adapters.
        
        Returns:
            List of LangChain BaseTool objects for MCP operations.
        """
        if self._mcp_tools is None:
            self._mcp_tools = await self._mcp_provider.get_tools()
            logger.info(f"AgentFactory loaded {len(self._mcp_tools)} MCP tools")
        return self._mcp_tools

    def get_mcp_tool_by_name(self, tool_name: str) -> Optional[BaseTool]:
        """
        Get a specific MCP tool by name.
        
        Args:
            tool_name: Name of the tool to retrieve (e.g., "git__git_log")
            
        Returns:
            The matching tool or None if not found.
        """
        if self._mcp_tools is None:
            raise RuntimeError("MCP tools not initialized. Call get_mcp_tools() first.")
        return next((t for t in self._mcp_tools if t.name == tool_name), None)

    async def _resolve_mcp_tool(self, tool_name: Optional[str] = None, tool_prefix: Optional[str] = None, match: Optional[str] = None) -> Optional[BaseTool]:
        """Resolve an MCP tool by exact name or by prefix and optional substring match.

        Returns the first matching tool or None if none found.
        """
        tools = await self.get_mcp_tools()
        if tool_name:
            exact = next((t for t in tools if t.name == tool_name), None)
            if exact:
                return exact

        if tool_prefix:
            # Find all tools with the prefix and optionally match a descriptive part
            prefixed = [t for t in tools if t.name.startswith(f"{tool_prefix}__")]
            if match:
                matched = next((t for t in prefixed if match.lower() in t.name.lower()), None)
                if matched:
                    return matched
            if prefixed:
                return prefixed[0]

        return None

    @property
    def redis_client(self) -> redis.Redis:
        """Lazy initialization of Redis client"""
        if self._redis_client is None:
            try:
                self._redis_client = redis.from_url(
                    self.settings.database.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=self.settings.database.redis_timeout
                )
                # Verify connectivity early to avoid late failures
                self._redis_client.ping()
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}. Using in-memory cache only.")
                self._redis_client = None
        return self._redis_client

    def get_model_for_agent(self, agent_type: str, model_pool: ModelPool) -> str:
        """Get appropriate model for agent based on settings"""
        if self.settings.llm.model_tier == "simple":
            # Use pre-configured models from settings
            if agent_type == "orchestrator":
                return self.settings.model_tier.simple_orchestrator_model
            elif agent_type == "review_agent":
                return self.settings.model_tier.simple_review_agent_model
            elif agent_type == "context_agent":
                return self.settings.model_tier.simple_context_agent_model
        
        # Advanced mode - use model selector
        return self.model_selector.get_model(agent_type, model_pool, "best_available")

    @classmethod
    def create_review_agent_subgraph(cls, specialty: str, model_selector: ModelSelector) -> StateGraph:
        """Creates a review agent subgraph that can spawn context agents"""

        template = REVIEW_AGENT_TEMPLATES[specialty]
        factory = cls(model_selector)

        graph = StateGraph(ReviewAgentState)

        # Review agent's workflow
        graph.add_node("plan", partial(cls._review_agent_plan, factory=factory, template=template))
        graph.add_node("spawn_context", partial(cls._spawn_context_agents, factory=factory, template=template))
        graph.add_node("analyze", partial(cls._review_agent_analyze, factory=factory, template=template))
        graph.add_node("finalize", partial(cls._review_agent_finalize, factory=factory, template=template))

        graph.set_entry_point("plan")
        graph.add_edge("plan", "spawn_context")
        graph.add_edge("spawn_context", "analyze")

        # Can iterate if needs more context
        graph.add_conditional_edges(
            "analyze",
            lambda s: "spawn_context" if s.needs_more_context and s.current_iteration < template["max_iterations"] else "finalize",
            {
                "spawn_context": "spawn_context",
                "finalize": "finalize"
            }
        )

        graph.add_edge("finalize", END)

        return graph.compile()

    @staticmethod
    async def _review_agent_plan(state: ReviewAgentState, factory: 'AgentFactory', template: Dict) -> Dict:
        """Review agent decides what context it needs"""

        try:
            # Get LLM for this agent using settings and model selector
            model_name = factory.get_model_for_agent("review_agent", template["model_pool"])
            llm = await factory.llm_factory.get_llm(model_name)

            decision = await llm.ainvoke([
                SystemMessage(content=template["prompt_template"].format(
                    specialty=state.specialty,
                    marching_orders=state.marching_orders,
                    context_agent_budget=template["context_agent_budget"]
                )),
                HumanMessage(content=f"PR Diff:\n{state.pr_diff}\n\nRepo conventions:\n{state.repo_memory.get('conventions', '')}")
            ])

            # Parse JSON response for context requests
            try:
                plan = json.loads(decision.content)
            except:
                plan = {"context_requests": [], "reasoning": "Failed to parse response"}

            return {
                "context_requests_this_iteration": plan.get("context_requests", []),
                "reasoning_history": [plan.get("reasoning", "")],
                "current_iteration": state.current_iteration + 1
            }
        except Exception as e:
            logger.error(f"Review agent planning failed: {e}")
            return {
                "context_requests_this_iteration": [],
                "reasoning_history": [f"Error in planning: {str(e)}"],
                "current_iteration": state.current_iteration + 1
            }

    @staticmethod
    async def _spawn_context_agents(state: ReviewAgentState, factory: 'AgentFactory', template: Dict, fail_fast: bool = False) -> Dict:
        """Spawns context agents and gathers results"""

        gathered = []

        for req in state.context_requests_this_iteration:
            context_type = req["type"]
            context_template = CONTEXT_AGENT_TEMPLATES[context_type]

            # Check cache first (both in-memory and Redis)
            cache_key = f"{context_type}:{req.get('query', '')}:{','.join(req.get('files', []))}"
            
            # Check in-memory cache using getattr to support both ReviewAgentState and PRReviewState
            context_cache = getattr(state, 'context_cache', None)
            if context_cache and cache_key in context_cache:
                gathered.append(state.context_cache[cache_key])
                continue
            
            # Check Redis cache
            try:
                cached_result = factory.redis_client.get(cache_key) if factory.redis_client else None
                if cached_result:
                    cached_data = json.loads(cached_result)
                    gathered.append(cached_data)
                    continue
            except Exception as e:
                logger.warning(f"Redis cache lookup failed: {e}")

            try:
                # Spawn disposable context agent
                context_agent = factory.create_async_context_agent(context_type)
                result = await context_agent({
                    "task": context_type,
                    "target_files": req.get("files", []),
                    "query": req.get("query", "")
                })

                gathered_item = {
                    "iteration": state.current_iteration,
                    "context_type": context_type,
                    "result": result["context_found"],
                    "cost_usd": result["cost"],
                    "tokens": result["tokens"],
                    "cache_key": cache_key
                }

                gathered.append(gathered_item)

                # Cache in Redis
                try:
                    if factory.redis_client:
                        factory.redis_client.setex(
                            cache_key, 
                            factory._context_cache_ttl, 
                            json.dumps(gathered_item)
                        )
                except Exception as e:
                    logger.warning(f"Redis cache storage failed: {e}")
                else:
                    # If state supports in-memory cache, store there as well
                    if context_cache is not None:
                        try:
                            context_cache[cache_key] = gathered_item
                        except Exception:
                            # ignore if model doesn't allow assignment
                            pass
                

            except Exception as e:
                # Improve error visibility with contextual details
                logger.error(
                    "Context agent %s failed during gather. iteration=%s query=%s files=%s error=%s",
                    context_type, state.current_iteration, req.get("query", ""), req.get("files", []), str(e)
                )
                # Add empty result to continue processing
                gathered.append({
                    "iteration": state.current_iteration,
                    "context_type": context_type,
                    "result": {"error": str(e)},
                    "failed": True,
                    "cost_usd": 0.0,
                    "tokens": 0,
                    "cache_key": cache_key
                })
                if fail_fast:
                    logger.error("Fail-fast enabled: aborting spawn_context_agents due to error in %s", context_type)
                    raise

        return {
            "context_gathered": gathered,
            "context_requests_this_iteration": []  # Clear for next iteration
        }

    @staticmethod
    async def _review_agent_analyze(state: ReviewAgentState, factory: 'AgentFactory', template: Dict) -> Dict:
        """Review agent analyzes gathered context and generates findings"""

        try:
            model_name = factory.get_model_for_agent("review_agent", template["model_pool"])
            llm = await factory.llm_factory.get_llm(model_name)

            analysis = await llm.ainvoke([
                SystemMessage(content=f"""{template['prompt_template']}

You are in iteration {state.current_iteration} of {template['max_iterations']}.

IMPORTANT: You have access to ALL context from previous iterations.
Context gathered so far: {len(state.context_gathered)} items
Findings so far: {len(state.findings)} issues

Review your previous work. If you need MORE context, request it.
If you have enough, provide your findings.

Return JSON: {{"findings": [...], "needs_more_context": false, "reasoning": "..."}}"""),
                HumanMessage(content=f"""
PR Diff: {state.pr_diff}

=== ALL CONTEXT GATHERED (Iterations 1-{state.current_iteration}) ===
{json.dumps(state.context_gathered, indent=2)}

=== YOUR FINDINGS SO FAR ===
{json.dumps(state.findings, indent=2)}

=== YOUR REASONING HISTORY ===
{chr(10).join(state.reasoning_history)}

=== CI STATUS ===
{state.ci_status or 'pending'}

What do you need next?
""")
            ])

            try:
                content = analysis.content.strip()
                if content.startswith("```"):
                    # Split by ``` and take the content between the first and second marker
                    parts = content.split("```")
                    if len(parts) >= 2:
                        content = parts[1]
                        if content.startswith("json"):
                            content = content[4:]
                    content = content.strip()

                result = json.loads(content)
            except:
                result = {
                    "findings": [],
                    "needs_more_context": False,
                    "reasoning": "Failed to parse analysis"
                }

            return {
                "findings": result.get("findings", []),
                "reasoning_history": [result.get("reasoning", "")],
                "needs_more_context": result.get("needs_more_context", False)
            }
        except Exception as e:
            logger.error(f"Review agent analysis failed: {e}")
            return {
                "findings": [],
                "reasoning_history": [f"Analysis failed: {str(e)}"],
                "needs_more_context": False
            }

    @staticmethod
    async def _review_agent_finalize(state: ReviewAgentState, factory: 'AgentFactory', template: Dict) -> Dict:
        """Review agent writes final report"""
        
        try:
            # Calculate confidence based on findings and context gathered
            high_severity_findings = [f for f in state.findings if f.get('severity') == 'high']
            medium_severity_findings = [f for f in state.findings if f.get('severity') == 'medium']
            
            # Confidence calculation: higher with more context, lower with high severity issues
            base_confidence = 0.8
            context_bonus = min(0.1, len(state.context_gathered) * 0.02)
            severity_penalty = len(high_severity_findings) * 0.2 + len(medium_severity_findings) * 0.1
            iteration_penalty = max(0, (state.current_iteration - template["max_iterations"]) * 0.1)
            
            confidence = max(0.1, min(0.95, base_confidence + context_bonus - severity_penalty - iteration_penalty))
            
            # Determine verdict based on findings
            if high_severity_findings:
                verdict = "FAIL"
            elif medium_severity_findings:
                verdict = "WARN" 
            elif state.findings:
                verdict = "NEEDS_WORK"
            else:
                verdict = "PASS"
            
            # Generate summary
            findings_summary = f"{len(state.findings)} findings"
            if high_severity_findings:
                findings_summary += f" (including {len(high_severity_findings)} high-severity issues)"
            elif medium_severity_findings:
                findings_summary += f" (including {len(medium_severity_findings)} medium-severity issues)"
                
            summary = f"Review completed with {findings_summary} in {state.current_iteration} iterations"
            
            # Check if we hit max iterations without enough context
            if state.current_iteration >= template["max_iterations"] and state.findings:
                summary += f". Review may benefit from additional context or manual review."
            
            return {
                "final_report": ReviewAgentVerdict(
                    verdict=verdict,
                    confidence=confidence,
                    summary=summary,
                    specialty=state.specialty,
                    findings=state.findings,
                    context_gathered=state.context_gathered,
                    iterations_used=state.current_iteration,
                    needs_more_context=False
                )
            }
            
        except Exception as e:
            logger.error(f"Review agent finalization failed: {e}")
            return {
                "final_report": ReviewAgentVerdict(
                    verdict="NEEDS_WORK",
                    confidence=0.1,  # Very low confidence due to error
                    summary=f"Review completed with error: {str(e)}",
                    specialty=state.specialty,
                    findings=[],
                    context_gathered=state.context_gathered,
                    iterations_used=state.current_iteration,
                    needs_more_context=False
                )
            }



    def create_async_context_agent(self, context_type: str):
        """Creates an async context agent function"""

        if context_type not in CONTEXT_AGENT_TEMPLATES:
            raise KeyError(f"Invalid context type: {context_type}. Valid types: {list(CONTEXT_AGENT_TEMPLATES.keys())}")

        template = CONTEXT_AGENT_TEMPLATES[context_type]

        async def async_context_agent_fn(state_data: Dict) -> Dict:
            """Async context agent function"""
            try:
                # Create ContextAgentState from dict
                state = ContextAgentState(
                    task=state_data.get("task", ""),
                    target_files=state_data.get("target_files", []),
                    query=state_data.get("query", ""),
                    context_found={},
                    cost=0.0,
                    tokens=0
                )
                
                # Get cheap model for context agents
                model_name = self.get_model_for_agent("context_agent", template["model_pool"])
                llm = await self.llm_factory.get_llm(model_name)

                # Call the actual tool (MCP, etc.) with timeout and retry logic
                fallback = template.get("fallback_tool")
                if context_type == "zoekt_search":
                    tool_result = await self._call_zoekt_tool(state, fallback_tool=fallback)
                elif context_type == "lsp_analysis":
                    tool_result = await self._call_lsp_tool(state, fallback_tool=fallback)
                elif context_type == "git_history":
                    tool_result = await self._call_git_tool(state, fallback_tool=fallback)
                elif context_type == "test_coverage":
                    if fallback and state.target_files:
                        named_tool = await self._resolve_mcp_tool(tool_name=fallback)
                        if named_tool:
                            file_path = state.target_files[0]
                            tool_result = await named_tool.ainvoke({"path": file_path})
                        else:
                            tool_result = {"results": [], "error": f"Fallback tool {fallback} not available"}
                    else:
                        tool_result = {"results": [], "error": "test_coverage tool not implemented"}
                else:
                    tool_result = {"results": [], "error": f"Unknown context type: {context_type}"}

                # LLM summarizes/structures the raw tool output
                if "error" not in tool_result:
                    summary = await llm.ainvoke([
                        SystemMessage(content="Summarize this tool output concisely for code review."),
                        HumanMessage(content=str(tool_result))
                    ])
                    summary_text = summary.content
                    tokens_estimate = len(summary_text) // 4  # Rough token estimation
                else:
                    summary_text = f"Tool failed: {tool_result.get('error', 'Unknown error')}"
                    tokens_estimate = 50
                
                return {
                    "context_found": {
                        "raw": tool_result,
                        "summary": summary_text
                    },
                    "cost": 0.001,  # Cheap models
                    "tokens": tokens_estimate
                }
                
            except Exception as e:
                logger.error(f"Context agent {context_type} failed: {e}")
                return {
                    "context_found": {
                        "raw": {
                            "results": [],
                            "error": str(e),
                            "source": "error",
                        },
                        "error": str(e),
                        "summary": f"Context gathering failed: {str(e)}"
                    },
                    "cost": 0.0,
                    "tokens": 0
                }

        return async_context_agent_fn

    def create_context_agent(self, context_type: str):
        """Creates a context agent function (async)"""

        # Validate context type
        if context_type not in CONTEXT_AGENT_TEMPLATES:
            raise KeyError(f"Invalid context type: {context_type}. Valid types: {list(CONTEXT_AGENT_TEMPLATES.keys())}")

        # Return the async function directly - LangGraph can handle async nodes
        return self.create_async_context_agent(context_type)
            
        return wrapper

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((Exception,))
    )
    async def _call_zoekt_tool(self, state: ContextAgentState, fallback_tool: Optional[str] = None) -> Dict:
        """Call Zoekt search via MCP tools"""
        if not self.settings.mcp.zoekt_enabled:
            return {"results": [], "error": "Zoekt search is disabled"}
        
        try:
            # Try to get real MCP tools via resolver
            search_tool = await self._resolve_mcp_tool(tool_prefix="zoekt", match="search")
            if search_tool:
                result = await search_tool.ainvoke({"query": state.query})
                return {
                    "results": result if isinstance(result, list) else [result],
                    "total_matches": 1,
                    "search_time_ms": 25,
                    "query": state.query,
                    "source": "mcp_zoekt"
                }
            
            # Try explicit fallback tool if provided
            if fallback_tool:
                fallback = await self._resolve_mcp_tool(tool_name=fallback_tool)
                if fallback:
                    result = await fallback.ainvoke({"query": state.query})
                    return {
                        "results": result if isinstance(result, list) else [result],
                        "total_matches": 1,
                        "query": state.query,
                        "source": "fallback_tool"
                    }
            
            # Fallback to filesystem search if zoekt unavailable
            # Try filesystem fallback by prefix
            search_tool = await self._resolve_mcp_tool(tool_prefix="filesystem", match="search")
            if search_tool:
                result = await search_tool.ainvoke({"query": state.query})
                return {
                        "results": result if isinstance(result, list) else [result],
                        "total_matches": 1,
                        "query": state.query,
                        "source": "mcp_filesystem_fallback"
                    }
            
            # Final fallback: mock results for testing
            logger.warning(f"No MCP search tools available, using mock for query: {state.query}")
            return {
                "results": [{
                    "file": f"src/{state.query.replace(' ', '_')}.py",
                    "line": 10,
                    "content": f"# Found pattern: {state.query}",
                    "match_type": "mock"
                }],
                "total_matches": 1,
                "query": state.query,
                "source": "mock_fallback"
            }
            
        except Exception as e:
            logger.error(f"Zoekt search failed: {e}")
            return {"results": [], "error": f"Search failed: {str(e)}"}

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((Exception,))
    )
    async def _call_lsp_tool(self, state: ContextAgentState, fallback_tool: Optional[str] = None) -> Dict:
        """Call LSP analysis via MCP tools"""
        if not self.settings.mcp.lsp_enabled:
            return {"hover": None, "references": [], "error": "LSP is disabled"}
        
        try:
            # Try to resolve LSP tools by prefix
            lsp_tool = await self._resolve_mcp_tool(tool_prefix="lsp", match="symbol")
            if lsp_tool and state.target_files:
                file_path = state.target_files[0]
                
                # Try to get symbols/definitions
                result = await lsp_tool.ainvoke({"file": file_path})
                return {
                        "analysis": result,
                        "file": file_path,
                        "source": "mcp_lsp"
                    }
            
            # Try explicit fallback tool if provided
            if fallback_tool and state.target_files:
                fallback = await self._resolve_mcp_tool(tool_name=fallback_tool)
                if fallback:
                    file_path = state.target_files[0]
                    result = await fallback.ainvoke({"path": file_path})
                    return {
                        "file_content": result,
                        "file": file_path,
                        "source": "fallback_tool"
                    }

            # Fallback: use filesystem to read the file
            # Fallback: use filesystem to read the file
            read_tool = await self._resolve_mcp_tool(tool_prefix="filesystem", match="read")
            if read_tool and state.target_files:
                    file_path = state.target_files[0]
                    result = await read_tool.ainvoke({"path": file_path})
                    return {
                        "file_content": result,
                        "file": file_path,
                        "source": "mcp_filesystem_fallback"
                    }
            
            # Final fallback: mock LSP results
            if not state.target_files:
                return {"hover": None, "references": [], "error": "No target files provided"}
            
            file_name = state.target_files[0]
            logger.warning(f"No MCP LSP tools available, using mock for file: {file_name}")
            
            return {
                "file": file_name,
                "hover": {
                    "text": f"class {file_name.replace('.py', '').title()} {{}}",
                    "range": {"start": {"line": 1, "character": 0}, "end": {"line": 1, "character": 10}}
                },
                "references": [
                    {"file": file_name, "line": 5, "column": 8},
                ],
                "source": "mock_fallback"
            }
            
        except Exception as e:
            logger.error(f"LSP analysis failed: {e}")
            return {"hover": None, "references": [], "error": f"LSP failed: {str(e)}"}

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((Exception,))
    )
    async def _call_git_tool(self, state: ContextAgentState, fallback_tool: Optional[str] = None) -> Dict:
        """Call Git history analysis via MCP tools"""
        if not self.settings.mcp.git_enabled:
            return {"history": [], "blame": [], "error": "Git analysis is disabled"}
        
        try:
            git_tool = await self._resolve_mcp_tool(tool_prefix="git", match="log")
            if git_tool and state.target_files:
                file_path = state.target_files[0]
                results = {}
                
                # Try git log
                log_tool = git_tool
                if log_tool:
                    try:
                        log_result = await log_tool.ainvoke({"path": file_path})
                        results["history"] = log_result if isinstance(log_result, list) else [log_result]
                    except Exception as e:
                        logger.warning(f"git log failed: {e}")
                        results["history"] = []
                
                # Try git blame; fall back to prefix match for blame
                blame_tool = await self._resolve_mcp_tool(tool_prefix="git", match="blame")
                if blame_tool:
                    try:
                        blame_result = await blame_tool.ainvoke({"path": file_path})
                        results["blame"] = blame_result if isinstance(blame_result, list) else [blame_result]
                    except Exception as e:
                        logger.warning(f"git blame failed: {e}")
                        results["blame"] = []
                
                if results:
                    results["source"] = "mcp_git"
                    results["total_commits"] = len(results.get("history", []))
                    return results
            
            # Try explicit fallback tool if provided
            if fallback_tool and state.target_files:
                fallback = await self._resolve_mcp_tool(tool_name=fallback_tool)
                if fallback:
                    file_path = state.target_files[0]
                    result = await fallback.ainvoke({"path": file_path})
                    return {
                        "history": result if isinstance(result, list) else [result],
                        "blame": [],
                        "source": "fallback_tool"
                    }
            
            # Fallback: mock git history
            if not state.target_files:
                return {"history": [], "blame": [], "error": "No target files provided"}
            
            file_name = state.target_files[0]
            logger.warning(f"No MCP git tools available, using mock for file: {file_name}")
            
            return {
                "history": [{
                    "commit": "abc123",
                    "author": "developer@example.com",
                    "date": "2024-01-15T10:30:00Z",
                    "message": "Initial implementation",
                    "file": file_name,
                }],
                "blame": [{
                    "line": 1,
                    "content": f"# {file_name}",
                    "commit": "abc123",
                    "author": "developer@example.com",
                }],
                "total_commits": 1,
                "source": "mock_fallback"
            }
            
        except Exception as e:
            logger.error(f"Git analysis failed: {e}")
            return {"history": [], "blame": [], "error": f"Git analysis failed: {str(e)}"}