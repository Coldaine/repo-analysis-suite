# MCP Integration Quick Start Guide

## What Was Implemented

The observability control plane now integrates with an MCP (Model Context Protocol) server to execute infrastructure operations automatically. The LLM agent can now:

- List available tools from the MCP server
- Execute Docker commands (restart containers, prune resources, etc.)
- Query databases (PostgreSQL, Neo4j)
- Access filesystems
- Interact with GitHub

## Files Created

```
scripts/
├── mcp_client.py              # MCP HTTP client
├── mcp_tools.py               # Tool patterns for common issues
├── test_mcp.py                # Test suite
├── MCP_INTEGRATION.md         # Full documentation
├── MCP_IMPLEMENTATION_SUMMARY.md  # Implementation details
└── MCP_QUICKSTART.md          # This file
```

## Modified Files

```
scripts/obs_agent.py           # Added MCP integration to LLMClient
```

## Quick Test

### 1. Test MCP Client (Without MCP Server)

This will show you what happens when MCP server is not available (graceful degradation):

```bash
cd E:\_projectsGithub\observability-implementation-package

# Run test suite (will show connection errors but shouldn't crash)
python scripts/test_mcp.py
```

**Expected Output**:
```
✗ MCP server health check failed
✗ No tools returned (or error occurred)
...
Overall: 0/4 tests passed (server not running)
```

### 2. Test with MCP Server Running

First, ensure the MCP server is running:

```bash
# Check if MCP server container is running
docker ps | grep mcp

# If not, start it
docker-compose up -d mcp-server

# Verify it's accessible
curl http://localhost:8433/health
```

Then run tests:

```bash
# Use default URL
python scripts/test_mcp.py

# Or specify custom URL
MCP_URL=http://localhost:8433 python scripts/test_mcp.py
```

**Expected Output**:
```
✓ MCP server is reachable
✓ Retrieved 5 tools
✓ Tool executed successfully
✓ Tool patterns validated

Overall: 4/4 tests passed
```

### 3. Test obs_agent Integration (Dry Run)

```bash
# See what prompt would be sent to LLM (no API key needed)
python scripts/obs_agent.py "test issue" --dry-run
```

This shows the full prompt including available MCP tools.

### 4. Test Full Integration (Requires API Key)

```bash
# Set your Goose AI API key
export GOOSEAI_API_KEY=your_key_here

# Set MCP URL
export MCP_URL=http://localhost:8433

# Run agent
python scripts/obs_agent.py "container nginx is down"
```

The agent will:
1. Connect to MCP server
2. List available tools
3. Send prompt to LLM with tool information
4. If LLM decides to use a tool, execute it via MCP
5. Return formatted result

## Using Tool Patterns in Python

```python
from mcp_tools import get_tool_for_issue, format_tool_arguments
from mcp_client import MCPClient

# Get pattern for an issue
pattern = get_tool_for_issue("container_down")
# Returns: {"tool": "docker", "arguments": {"command": "restart", "container": "{container_name}"}}

# Format with actual values
formatted = format_tool_arguments(pattern, container_name="nginx")
# Returns: {"tool": "docker", "arguments": {"command": "restart", "container": "nginx"}}

# Execute via MCP
client = MCPClient("http://localhost:8433")
result = client.call_tool(formatted["tool"], formatted["arguments"])
print(result)
```

## Using MCP Client Directly

```python
from mcp_client import MCPClient

# Create client
client = MCPClient("http://localhost:8433")

# Check health
if client.health_check():
    print("Server is up!")

# List tools
tools = client.list_tools()
for tool in tools:
    print(f"- {tool['name']}: {tool['description']}")

# Execute a tool
result = client.call_tool("docker", {
    "command": "ps",
    "all": True
})
print(result)

# Cleanup
client.close()
```

## Environment Variables

```bash
# MCP server URL (default: http://localhost:8433)
export MCP_URL=http://localhost:8433

# LLM configuration
export GOOSEAI_API_KEY=your_api_key
export GOOSE_MODEL=gpt-neo-20b
export LLM_BASE_URL=https://api.goose.ai/v1

# Logging level (DEBUG, INFO, WARNING, ERROR)
export OBS_AGENT_LOG_LEVEL=INFO
```

## Common Issues and Solutions

### Issue: "MCP server health check failed"

**Solution**:
```bash
# Check if server is running
docker ps | grep mcp

# Check server logs
docker logs mcp-server

# Verify network access
curl http://localhost:8433/health

# Check firewall/port forwarding
netstat -an | grep 8433
```

### Issue: "Connection error listing tools"

**Solution**:
```bash
# Verify MCP_URL is correct
echo $MCP_URL

# Try with explicit localhost
export MCP_URL=http://localhost:8433

# If in Docker, use host gateway
export MCP_URL=http://host.docker.internal:8433
```

### Issue: "Tool execution fails"

**Solution**:
1. Verify tool name is correct (check `client.list_tools()`)
2. Check argument format matches tool schema
3. Ensure required services are running (Docker, databases, etc.)
4. Check MCP server logs for detailed error

### Issue: "LLM not using tools"

**Possible causes**:
1. MCP server not reachable (agent falls back to text-only)
2. LLM model doesn't support tool calling well
3. Prompt not clear enough about when to use tools
4. API key invalid/missing

**Debug**:
```bash
# Enable debug logging
export OBS_AGENT_LOG_LEVEL=DEBUG
python scripts/obs_agent.py "your issue here"
```

## Next Steps

1. **Review Full Documentation**: See `MCP_INTEGRATION.md` for complete details
2. **Check Implementation Summary**: See `MCP_IMPLEMENTATION_SUMMARY.md` for technical details
3. **Run Tests**: Use `test_mcp.py` to verify setup
4. **Add Custom Patterns**: Edit `mcp_tools.py` to add your own tool patterns
5. **Configure Production**: Review security and authentication requirements

## Key Files to Read

1. **MCP_INTEGRATION.md** - Complete documentation (architecture, API, troubleshooting)
2. **MCP_IMPLEMENTATION_SUMMARY.md** - Implementation details and status
3. **test_mcp.py** - See example usage and testing patterns
4. **mcp_tools.py** - Available tool patterns and utilities

## Architecture Overview

```
┌─────────────────┐
│  User/System    │
│    Issues       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  obs_agent.py   │  Main agent
│  (LLMClient)    │  Builds prompts, calls LLM
└────────┬────────┘
         │
         ├─→ LLM API (Goose AI, OpenAI, etc.)
         │
         ├─→ MCPClient (mcp_client.py)
         │      │
         │      ├─→ list_tools()
         │      └─→ call_tool()
         │             │
         │             ▼
         │      ┌─────────────┐
         │      │ MCP Server  │  :8433
         │      └─────────────┘
         │             │
         │             ├─→ Docker
         │             ├─→ Filesystem
         │             ├─→ PostgreSQL
         │             ├─→ Neo4j
         │             └─→ GitHub
         │
         └─→ Memory (memori)
         └─→ Graph (Neo4j)
```

## Status

✓ Implementation complete
✓ All files syntax validated
✓ Documentation created
⚠ Requires MCP server for full functionality
⚠ Requires LLM API key for agent operation

## Support

For detailed information:
- **Architecture & API**: See `MCP_INTEGRATION.md`
- **Implementation Details**: See `MCP_IMPLEMENTATION_SUMMARY.md`
- **Testing**: Run `python scripts/test_mcp.py`
- **Code Examples**: See `test_mcp.py` and `mcp_tools.py`
