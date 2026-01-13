---
doc_type: plan
subsystem: general
version: 1.0.0
status: draft
owners: pmacl
last_reviewed: 2025-12-03
---

# Documentation Gaps

Items from the historical research documents that weren't captured in the current documentation. These should be addressed in future iterations.

---

## From: Critique of Four-Agent Framework

### Missing: Agent-as-Judge Calibration

The research emphasized the need for **evaluator evaluation**:

- LLM-as-judge validation (are agents biased toward their own patterns?)
- Rubric consistency (0.0-1.0 scales with pass/fail thresholds)
- Inter-agent reliability metrics (Krippendorff's alpha)
- False positive rate tracking per agent over time

**Action**: Add meta-evaluation layer to the system design.

### Missing: Conflict Resolution Protocol

Current docs don't address what happens when agents disagree:

- Weight agents by project phase (Scope Agent veto power early, Test Agent veto late)
- Human-in-the-loop for 2-2 splits
- Hierarchical override rules (security > documentation)

**Action**: Add conflict resolution section to system-design.md.

### Missing: Structured Verdict Output Schema

The research proposed a standardized output format:

```json
{
  "agent": "Test Value Reviewer",
  "verdict": "SEVERELY_OVER_EXUBERANT",
  "score": 0.3,
  "current_count": 117,
  "recommended_count": 45,
  "confidence": 0.85,
  "key_issues": [
    {"pattern": "testing_library_features", "count": 42, "severity": "critical"}
  ],
  "specific_cuts": ["test_file_1.py:42-67"]
}
```

**Action**: Add to state-management.md as `AgentVerdict` Pydantic model.

### Missing: Learning Loops

- Evaluation/Feedback loops after cuts
- Human override tracking with reasons
- Agent prompt retraining based on false positive/negative patterns

**Action**: Expand memory system documentation.

---

## From: Comparative Context Retrieval Research

### Missing: MCP Server Integration Details

The research identified specific MCP servers for context retrieval:

| Server | Purpose | Downloads |
|--------|---------|-----------|
| **Acemcp** | Incremental codebase indexing | 89.6K |
| **Code Sage** | Hybrid BM25 + vector search (Cursor's approach) | 422 |
| **Sourcerer** | Tree-sitter AST + semantic search | 13.8K |
| **Code to Tree** | Pure AST conversion | 9.6K |
| **RagCode** | Local Ollama + Qdrant (privacy-first) | 281 |

**Current gap**: The agent-factory.md mentions MCP but doesn't specify which servers to use.

**Action**: Add MCP server recommendations to configuration.md.

### Missing: Hybrid Search Architecture

Research strongly recommends **BM25 keyword + vector embeddings + RRF reranking**:

```
User Query: "authentication error handling"
    ↓
┌─────────────────┐     ┌──────────────────┐
│ BM25 Keyword    │     │ Vector Embedding │
│ Search          │     │ Search           │
└────────┬────────┘     └────────┬─────────┘
         │                       │
         └───────────┬───────────┘
                     ↓
              ┌──────────────┐
              │ RRF Reranking│
              └──────────────┘
```

**Action**: Document hybrid search pattern in context agent architecture.

### Missing: Just-in-Time vs Indexed Trade-offs

Research conclusion:
- **JIT (grep/ripgrep)**: 95% token reduction, best for <500k LOC
- **AST indexing**: 90% reduction, best for >500k LOC
- **Hybrid**: 98% reduction, best for production

**Action**: Add codebase size recommendations to configuration.md.

### Missing: Tree-sitter Integration Details

All production tools use tree-sitter:
- Incremental parsing (10x faster updates)
- Error resilience (works on broken code)
- 40+ language support

**Action**: Add tree-sitter setup to context agent documentation.

### Missing: Spotify's Context Engineering Patterns

From Nov 2025 Spotify engineering blog:
- Very constrained tool sets (verify, limited git, tiny bash/ripgrep surface)
- Pre-condensed context via upstream workflow agents
- Don't give coding agents open-ended repo search

**Action**: Consider adding "prompt-building" workflow agent to architecture.

---

## From: Model Recommendations

### Missing: Model-to-Agent Mapping

Research suggested specific model assignments:

| Agent | Recommended Model | Reasoning |
|-------|------------------|-----------|
| Test Value Reviewer | Grok 4.1 Fast Reasoning | Pattern detection, 2M context |
| Documentation Reviewer | ZAIs 4.6 GLM | Writing evaluation, free access |
| Code Quality Reviewer | Kimi K2 Thinking | Deep reasoning, $0.30/1M tokens |
| Scope Alignment Reviewer | Grok 4.1 Fast Reasoning | Low hallucination |

**Action**: Add model recommendations to configuration.md model pools section.

### Missing: Cost-Optimized Configuration

Research showed ~$0.42 per review with optimal model mix, or ~$0.10 with aggressive cost optimization (Kimi/ZAIs primary, Grok for tie-breaking).

**Action**: Add cost analysis section.

---

## Priority Order

1. **High**: MCP server integration (blocks implementation)
2. **High**: Hybrid search architecture (core functionality)
3. **Medium**: Conflict resolution protocol (multi-agent coordination)
4. **Medium**: Model-to-agent mapping (optimization)
5. **Low**: Learning loops (future iteration)
6. **Low**: Agent calibration (advanced feature)

---

## Notes

These gaps were identified by comparing the historical research documents in `docs/research/` against the current documentation. The research represents design thinking that led to the current architecture but wasn't fully captured in the implementation docs.

See `docs/research/README.md` for the original source documents.
