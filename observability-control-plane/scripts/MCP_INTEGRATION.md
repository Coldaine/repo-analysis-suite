# MCP Integration Documentation

## Overview

The observability control plane now integrates with a Model Context Protocol (MCP) server to execute tools for automated infrastructure management. This integration allows the LLM-based agent to interact with Docker, filesystems, databases, and other services through a standardized protocol.

## Architecture

```
┌─────────────────┐
│   obs_agent.py  │  Main control plane agent
│   (LLMClient)   │
└────────┬────────┘
         │
         │ Uses
         ▼
┌─────────────────┐
│  mcp_client.py  │  MCP client implementation
│  (MCPClient)    │  Handles HTTP communication
└────────┬────────┘
         │
         │ HTTP/REST
         ▼
┌─────────────────┐
│   MCP Server    │  Running on port 8433
│  (localhost)    │  Provides tools for operations
└─────────────────┘
         │
         │ Executes
         ▼
┌─────────────────┐
│  Docker, FS,    │  Infrastructure services
│  PostgreSQL,    │
│  Neo4j, GitHub  │
└─────────────────┘
```

## Components

### 1. MCPClient (`mcp_client.py`)

**Purpose**: HTTP client for communicating with the MCP server.

**Key Methods**:
- `list_tools()` - Retrieves available tools from MCP server
- `call_tool(tool_name, arguments)` - Executes a tool with given arguments
- `health_check()` - Verifies server is reachable

**Features**:
- Automatic error handling and logging
- Connection timeout management
- Context manager support for resource cleanup
- Graceful degradation if MCP server is unavailable

**Example Usage**:
```python
from mcp_client import MCPClient

# Basic usage
client = MCPClient("http://localhost:8433")
tools = client.list_tools()
result = client.call_tool("docker", {"command": "ps"})

# With context manager
with MCPClient("http://localhost:8433") as client:
    result = client.call_tool("filesystem", {"command": "df", "path": "/"})
```

### 2. Tool Patterns (`mcp_tools.py`)

**Purpose**: Pre-defined tool execution patterns for common infrastructure issues.

**Available Patterns**:
- `restart_container` - Restart a Docker container
- `prune_system` - Clean up Docker resources
- `check_disk` - Check disk usage
- `check_logs` - View service logs
- `inspect_container` - Get container details
- `container_stats` - Resource usage statistics
- `check_network` - Network configuration
- `query_database` - PostgreSQL queries
- `query_graph` - Neo4j Cypher queries
- `check_github_status` - GitHub repository info

**Issue Type Mapping**:
```python
ISSUE_TO_TOOL_MAPPING = {
    "container_down": "restart_container",
    "container_unhealthy": "inspect_container",
    "disk_full": "prune_system",
    "high_disk_usage": "check_disk",
    "service_error": "check_logs",
    "high_memory": "container_stats",
    "network_issue": "check_network",
    "database_slow": "query_database",
    "graph_query_slow": "query_graph"
}
```

**Example Usage**:
```python
from mcp_tools import get_tool_for_issue, format_tool_arguments

# Get pattern for an issue type
pattern = get_tool_for_issue("container_down")

# Format with actual values
formatted = format_tool_arguments(
    pattern,
    container_name="nginx"
)

# Execute via MCP client
result = mcp_client.call_tool(
    formatted["tool"],
    formatted["arguments"]
)
```

### 3. Updated LLMClient (`obs_agent.py`)

**Changes**:
- Added `mcp_client` attribute to store MCPClient instance
- Enhanced `ask()` method to:
  - Initialize MCP client on first use
  - List available tools and add to system prompt
  - Parse LLM responses for tool execution requests
  - Execute tools and return formatted results
  - Gracefully handle MCP server unavailability

**Tool Execution Flow**:
1. LLM receives prompt with available tools
2. LLM responds with JSON: `{"tool": "name", "arguments": {...}}`
3. Client detects JSON response and parses it
4. Tool is executed via MCP server
5. Result is formatted and returned

**Example**:
```python
from obs_agent import llm_client

# Agent automatically uses MCP if available
response = llm_client.ask(
    "Container nginx is down, please investigate",
    mcp_url="http://localhost:8433"
)

# If LLM decides to use a tool, response includes:
# - Tool name
# - Arguments used
# - Execution result
```

### 4. Test Suite (`test_mcp.py`)

**Purpose**: Verify MCP integration is working correctly.

**Tests**:
- Connection test - Verify MCP server is reachable
- List tools test - Confirm tools can be retrieved
- Tool execution test - Execute a simple command
- Tool patterns test - Validate pattern utilities
- Error handling test - Ensure errors are handled gracefully

**Usage**:
```bash
# Run tests with default URL (localhost:8433)
python scripts/test_mcp.py

# Run with custom MCP URL
MCP_URL=http://host.docker.internal:8433 python scripts/test_mcp.py
```

## Configuration

### Environment Variables

- `MCP_URL` - MCP server URL (default: `http://localhost:8433`)
- `OBS_AGENT_LOG_LEVEL` - Logging level (default: `INFO`)

### MCP Server Setup

The MCP server should be running and accessible at the configured URL. Default configuration expects:

```yaml
# In docker-compose.yml
mcp-server:
  image: your-mcp-server-image
  ports:
    - "8433:8433"
  environment:
    - MCP_PORT=8433
```

## Integration Workflow

### Normal Operation

1. **Issue Detected**: Monitoring system detects an issue
2. **Agent Invoked**: `obs_agent.py` is called with issue description
3. **MCP Initialized**: LLMClient initializes MCP connection
4. **Tools Listed**: Available tools are retrieved and added to prompt
5. **LLM Analysis**: LLM analyzes issue and available tools
6. **Tool Execution**: If needed, LLM requests tool execution via JSON
7. **Result Logged**: Action and result are stored in memory/graph

### Fallback Behavior

If MCP server is unavailable:
- Client logs warning
- Continues without MCP integration
- LLM still provides analysis (but cannot execute tools)
- System remains functional for monitoring/alerting

## Error Handling

### Connection Errors
- MCP client retries are not automatic
- Errors are logged with full context
- System continues operation without MCP

### Tool Execution Errors
- Tool errors return structured error response
- LLM receives error information
- Can attempt alternative approaches

### Timeout Handling
- Default timeout: 30 seconds for listing tools
- Tool execution timeout: 60 seconds
- Health check timeout: 5 seconds

## Logging

All MCP operations are logged at appropriate levels:

```
INFO: Successful operations, tool listings
WARNING: Server unavailable, degraded operation
ERROR: Failed tool executions, connection failures
DEBUG: Detailed request/response information
```

## Security Considerations

### Current Implementation
- No authentication on MCP server (localhost only)
- Trusts all tool execution requests from LLM
- No rate limiting on tool execution

### Recommendations for Production
1. Add API key authentication to MCP server
2. Implement tool execution approval workflow
3. Rate limit tool executions per time window
4. Audit log all tool executions with timestamps
5. Restrict MCP server access to internal network
6. Validate all tool arguments before execution

## Testing

### Manual Testing

```bash
# Test basic connectivity
python scripts/test_mcp.py

# Test with custom URL
MCP_URL=http://host.docker.internal:8433 python scripts/test_mcp.py

# Test full agent workflow (dry run)
python scripts/obs_agent.py "test issue" --dry-run

# Test actual execution (requires valid GOOSEAI_API_KEY)
export GOOSEAI_API_KEY=your_key_here
python scripts/obs_agent.py "container nginx is down"
```

### Expected Test Output

```
==========================================================
MCP Client Integration Tests
==========================================================

MCP Server URL: http://localhost:8433

✓ MCP server is reachable
✓ Retrieved 5 tools:
  - docker: Docker container management
  - filesystem: File system operations
  - postgresql: PostgreSQL database queries
  - neo4j: Neo4j graph database queries
  - github: GitHub operations

✓ Tool executed successfully: {
  "output": "/app",
  "exit_code": 0
}

✓ Found 10 predefined patterns:
  - restart_container: Restart a Docker container
  - prune_system: Remove unused Docker resources
  ...

==========================================================
Test Summary
==========================================================
✓ Connection Test: PASS
✓ List Tools Test: PASS
✓ Tool Execution Test: PASS
✓ Tool Patterns Test: PASS

Overall: 4/4 tests passed
```

## Troubleshooting

### MCP Server Not Responding

**Symptoms**: `MCP server health check failed` warning

**Solutions**:
1. Check if MCP server container is running: `docker ps`
2. Verify port 8433 is accessible: `curl http://localhost:8433/health`
3. Check MCP server logs: `docker logs mcp-server`
4. Verify network connectivity from agent container

### Tool Execution Fails

**Symptoms**: Tool returns error in result

**Solutions**:
1. Verify tool name matches available tools
2. Check argument format matches tool schema
3. Ensure required services (Docker, databases) are running
4. Check MCP server has permissions for requested operation

### LLM Not Using Tools

**Symptoms**: LLM responds with text instead of tool JSON

**Solutions**:
1. Check system prompt includes tool definitions
2. Verify LLM model supports tool calling
3. Adjust prompt to be more explicit about using tools
4. Check LLM API key and model configuration

## Future Enhancements

1. **Tool Discovery**: Automatic tool registration/discovery
2. **Async Execution**: Non-blocking tool execution for long operations
3. **Tool Chaining**: Execute multiple tools in sequence
4. **Approval Workflow**: Human-in-the-loop for critical operations
5. **Enhanced Logging**: Structured logging with trace IDs
6. **Metrics**: Track tool usage, success rates, execution times
7. **Caching**: Cache tool results for frequently requested data
8. **Webhooks**: Notify external systems of tool executions

## API Reference

### MCPClient

```python
class MCPClient:
    def __init__(self, base_url: str = "http://localhost:8433")
    def list_tools(self) -> List[Dict[str, Any]]
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]
    def health_check(self) -> bool
    def close(self) -> None
```

### Tool Patterns

```python
def get_tool_for_issue(issue_type: str) -> Optional[Dict[str, Any]]
def format_tool_arguments(pattern: Dict[str, Any], **kwargs) -> Dict[str, Any]
def list_all_patterns() -> Dict[str, str]
def get_pattern_by_name(pattern_name: str) -> Optional[Dict[str, Any]]
```

## Support

For issues or questions:
1. Check MCP server logs
2. Review agent logs (`OBS_AGENT_LOG_LEVEL=DEBUG`)
3. Run test suite to isolate issues
4. Verify all environment variables are set correctly
