# Personal Troubleshooting Guide

Common issues and solutions for the AgentReview multi-agent system. This guide captures real debugging experiences and solutions for future reference.

## Quick Diagnostic Commands

```bash
# Check environment variables are loaded correctly
python -c "from multiagentpanic.config.settings import get_settings; print(get_settings().model_dump())"

# Test LLM connectivity
python -c "
from multiagentpanic.config.settings import get_settings
from langchain_openai import ChatOpenAI
settings = get_settings()
llm = ChatOpenAI(api_key=settings.llm.openai_api_key.get_secret_value(), base_url=settings.llm.openai_base_url)
print('LLM test:', llm.invoke('hello').content)
"

# Verify database connections
python -c "
from multiagentpanic.config.settings import get_settings
settings = get_settings()
print('Postgres:', settings.database.postgres_url)
print('Redis:', settings.database.redis_url)
"
```

## Common Issues

### 1. LLM API Key Problems

**Symptoms:**
- `ValueError: Configuration validation failed: At least one LLM provider API key must be configured`
- Authentication errors when calling LLM

**Diagnosis:**
```python
# Check if API keys are being loaded
from multiagentpanic.config.settings import get_settings
settings = get_settings()
print("OpenAI key:", bool(settings.llm.openai_api_key))
print("Base URL:", settings.llm.openai_base_url)
```

**Solutions:**
1. **Check environment variables**: Ensure `Z_AI_API_KEY` or `LLM_OPENAI_API_KEY` is set
2. **Verify key format**: Keys shouldn't start with "test" in production
3. **Base URL issues**: z.ai requires `https://api.zai.ai/v1` base URL
4. **Reload after setting**: Use `reload_settings()` if setting env vars dynamically

### 2. Database Connection Issues

**Symptoms:**
- PostgreSQL connection errors
- Redis connection failures
- Timeout errors during agent execution

**Diagnosis:**
```python
# Test database connections
import asyncpg
import redis.asyncio as redis

async def test_db():
    try:
        conn = await asyncpg.connect(settings.database.postgres_url)
        await conn.execute('SELECT 1')
        print("✅ PostgreSQL: OK")
    except Exception as e:
        print(f"❌ PostgreSQL: {e}")
    
    try:
        r = redis.from_url(settings.database.redis_url)
        await r.ping()
        print("✅ Redis: OK")
    except Exception as e:
        print(f"❌ Redis: {e}")
```

**Solutions:**
1. **PostgreSQL**: Ensure database exists and credentials are correct
2. **Redis**: Check if Redis server is running
3. **Connection pooling**: Verify pool settings aren't too restrictive
4. **Network issues**: Ensure services are accessible from container/VM

### 3. MCP Tool Discovery Failures

**Symptoms:**
- MCP tool calls return empty results
- "Tool not found" errors
- Timeout errors on MCP operations

**Diagnosis:**
```python
# Check MCP tool discovery
from multiagentpanic.tools.mcp_tools import get_mcp_provider
provider = get_mcp_provider()
tools = provider.get_tools()
print(f"Discovered {len(tools)} tools:", [t.name for t in tools])
```

**Solutions:**
1. **Server availability**: Ensure MCP servers are installed and running
2. **Command configuration**: Verify server commands in settings
3. **Timeout issues**: Increase `mcp_timeout` setting for slow operations
4. **Tool registration**: Some tools require specific MCP server installations

### 4. Agent Execution Failures

**Symptoms:**
- Agents fail to start
- LangGraph execution errors
- State management issues

**Diagnosis:**
```python
# Test agent factory
from multiagentpanic.factory.agent_factory import AgentFactory
from multiagentpanic.factory.model_pools import ModelSelector

try:
    factory = AgentFactory(ModelSelector())
    print("✅ AgentFactory: OK")
except Exception as e:
    print(f"❌ AgentFactory: {e}")
```

**Solutions:**
1. **Model availability**: Ensure configured models are accessible
2. **Agent templates**: Verify factory templates are properly defined
3. **State schemas**: Check Pydantic model validation
4. **Memory issues**: Monitor memory usage during long executions

### 5. Configuration Reload Issues

**Symptoms:**
- Settings don't update after changing environment
- Configuration validation fails intermittently

**Solutions:**
```python
# Force reload settings
from multiagentpanic.config.settings import reload_settings
settings = reload_settings()
print("Settings reloaded")
```

## Performance Issues

### Slow Agent Execution

**Diagnosis:**
1. Check model response times
2. Monitor database query performance  
3. Verify MCP tool latency
4. Review LangGraph execution traces

**Solutions:**
1. **Model selection**: Switch to faster models for context agents
2. **Caching**: Ensure Redis caching is working
3. **Concurrency**: Adjust parallel execution limits
4. **Tool optimization**: Optimize MCP tool usage patterns

### High Memory Usage

**Diagnosis:**
```python
# Monitor memory during execution
import psutil
import os

def get_memory_usage():
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024  # MB

print(f"Memory usage: {get_memory_usage():.1f} MB")
```

**Solutions:**
1. **Batch processing**: Process smaller PRs
2. **Context limits**: Reduce context window sizes
3. **Cache eviction**: Tune Redis TTL settings
4. **Garbage collection**: Add explicit cleanup in long-running operations

## Debugging Workflows

### 1. Systematic Testing Approach

```bash
# 1. Environment validation
python -c "from multiagentpanic.config.settings import get_settings; get_settings()"

# 2. Basic LLM test
python -c "
from multiagentpanic.agents.orchestrator import PRReviewOrchestrator
# Test basic orchestration
"

# 3. Integration test
python -m pytest tests/integration/test_01_e2e_simple_review.py -v
```

### 2. Logging and Tracing

Enable detailed logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# LangGraph tracing
from langfuse.langchain import LangfuseTracer
tracer = LangfuseTracer()
```

### 3. State Inspection

```python
# Inspect LangGraph state
from multiagentpanic.domain.schemas import PRReviewState
print("State schema:", PRReviewState.model_json_schema())
```

## Emergency Procedures

### Complete System Reset

```bash
# 1. Clear all caches
redis-cli FLUSHALL

# 2. Reset settings
unset Z_AI_API_KEY LLM_OPENAI_API_KEY GITHUB_TOKEN

# 3. Fresh environment
source .env

# 4. Test basic functionality
python -m pytest tests/unit/test_orchestrator.py -v
```

### Recovery from Failed Reviews

1. **Checkpoint cleanup**: Remove stale checkpoints from PostgreSQL
2. **Queue reset**: Clear Redis queues
3. **Agent restart**: Restart any hanging agent processes
4. **Fresh start**: Re-run review with new thread ID

## Prevention Strategies

### 1. Health Checks

Add to your development workflow:
```python
def health_check():
    """Quick system health validation"""
    settings = get_settings()
    
    checks = {
        "llm_configured": bool(settings.llm.openai_api_key),
        "database_connected": test_db_connection(),
        "mcp_available": test_mcp_tools(),
    }
    
    return all(checks.values()), checks
```

### 2. Monitoring

Monitor key metrics:
- LLM response times
- Database connection pool usage
- MCP tool success rates
- Memory usage patterns

### 3. Regular Maintenance

- **Weekly**: Clear old checkpoints and cache entries
- **Monthly**: Review and update agent prompts
- **Quarterly**: Audit security configurations and API keys

## Personal Notes

*Add your own debugging discoveries and solutions here as you encounter them.*

---

**Last Updated**: 2025-12-12  
**For**: Solo development and personal use  
**Context**: Multi-agent PR review system using LangGraph