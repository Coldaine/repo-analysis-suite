# Testing Strategy

## Testing Philosophy

### Core Principles

1. **Integration tests catch real issues** - Mocks hide integration problems
2. **Real LLM calls required** - Agent behavior varies with actual models
3. **Test the workflow, not the implementation** - Focus on outcomes
4. **Budget-conscious testing** - Use z.ai or cheap models for test runs
5. **Deterministic where possible** - Seed models, use consistent test data

### Test Pyramid (Inverted)

We prioritize integration tests over unit tests because mocking LLM responses creates false confidence.

```
       ┌─────────────────────────────────┐
       │                                 │
       │    Integration Tests (E2E)      │  ← Real LLM, real workflow
       │                                 │
       └─────────────────────────────────┘
              ┌───────────────────┐
              │                   │
              │   Factory Unit    │  ← No LLM, test foundations
              │      Tests        │
              │                   │
              └───────────────────┘
```

## Running Tests

Refer to the `tests/` directory for the actual test suite.

- **Integration Tests**: `tests/integration/`
- **Unit Tests**: `tests/unit/`

Run with:
```bash
pytest
```
