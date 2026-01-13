---
doc_type: reference
subsystem: factory
domain_code: fac
version: 1.0.0
status: draft
owners: pmacl
last_reviewed: 2025-12-12
version: 1.1.0
status: active
---

# Factory Domain

Agent factory pattern for dynamic agent creation and configuration.

## Components

| Component | Purpose |
|-----------|---------|
| `agent_factory.py` | Main factory class - coordinates agent creation |
| `prompts.py` | Agent templates (REVIEW_AGENT_TEMPLATES, CONTEXT_AGENT_TEMPLATES) |
| `llm_factory.py` | LLM instantiation with provider fallback |
| `model_pools.py` | Model pool definitions and selection strategies |

## Model Pools

```python
cheap_coding = ["claude-3-haiku", "gpt-4o-mini"]
expensive_coding = ["claude-3-opus", "gpt-4-turbo"]
reasoning = ["o1-preview", "claude-3-opus"]
```

## Modes

- **Simple**: Fixed model assignment per agent type
- **Advanced**: Random/best-available from pool

## Code Location

`src/multiagentpanic/factory/`

## Domain Documents

- `fac-templates.md` - Agent template details (see [Agent Factory Architecture](../../architecture/agent-factory.md))
- `fac-model-pools.md` - Model pool configuration (see [ModelTierSettings in settings.py](../../src/multiagentpanic/config/settings.py))

## Implementation Notes

### Agent Templates
Review agents use structured templates defined in `factory/prompts.py`:
- **Alignment Agent**: Architecture alignment reviewer (expensive_coding pool)
- **Dependencies Agent**: Dependency management reviewer (expensive_coding pool)
- **Testing Agent**: Test coverage reviewer (expensive_coding pool)
- **Security Agent**: Security vulnerability reviewer (expensive_coding pool)

Context agents also defined in `factory/prompts.py`:
- **zoekt_search**: Code search via Zoekt MCP (cheap_tool_use pool)
- **lsp_analysis**: Type/reference analysis via LSP MCP (cheap_tool_use pool)
- **git_history**: Git blame/log via Git MCP (cheap_tool_use pool)

Personality prompts (TEST_KILLER, CODE_JANITOR, etc.) are in `agents/prompts.py` for use with `create_jit_agent()`.

### LLM Factory
`llm_factory.py` handles LLM instantiation with:
- Provider selection (OpenAI, Anthropic, Google)
- Automatic fallback on provider errors
- Dummy key support for testing

### Model Pool Configuration
Model pools are configured via `ModelTierSettings`:
- **simple mode**: Fixed model assignments per agent type
- **advanced mode**: Dynamic selection from model pools with selection strategies
- Selection strategies: FIXED, RANDOM, ROUND_ROBIN, LEAST_COST, BEST_AVAILABLE

## Related Documentation

- [Agent Factory Architecture](../../architecture/agent-factory.md) - Design patterns
- [Configuration](../../guides/configuration.md) - Model pool setup
