# Contributing to Agent Council

Thank you for your interest in contributing to Agent Council! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

By participating in this project, you agree to abide by our code of conduct:
- Be respectful and inclusive
- Welcome newcomers and help them get started
- Focus on constructive criticism
- Accept feedback gracefully

## How to Contribute

### Reporting Issues

1. **Search existing issues** to avoid duplicates
2. **Use issue templates** when available
3. **Provide detailed information**:
   - Agent Council version
   - Python version
   - Operating system
   - Steps to reproduce
   - Error messages and logs
   - Expected vs actual behavior

### Suggesting Enhancements

1. **Check the roadmap** in README.md
2. **Open a discussion** before large features
3. **Provide use cases** and examples
4. **Consider backward compatibility**

### Pull Requests

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/your-feature`
3. **Follow coding standards** (see below)
4. **Write tests** for new features
5. **Update documentation**
6. **Commit with clear messages**
7. **Push and create PR**

## Development Setup

### Prerequisites

```bash
# Clone your fork
git clone https://github.com/yourusername/agent-council.git
cd agent-council

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate  # Windows

# Install development dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_orchestrator.py

# Run with verbose output
pytest -v

# Run integration tests
pytest tests/integration/
```

### Code Quality Checks

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Lint code
flake8 src/ tests/
pylint src/

# Type checking
mypy src/

# Security checks
bandit -r src/

# All checks (pre-commit)
pre-commit run --all-files
```

## Coding Standards

### Python Style Guide

We follow PEP 8 with these additions:

```python
# Class docstrings
class AgentOrchestrator:
    """
    Brief description of the class.

    Longer description if needed, explaining purpose,
    usage, and important details.

    Attributes:
        agents: Dictionary of registered agents
        scheduler: Scheduling system instance

    Example:
        orchestrator = AgentOrchestrator()
        orchestrator.start()
    """

# Function docstrings
def execute_agent(agent_name: str, context: dict) -> dict:
    """
    Execute a specific agent with given context.

    Args:
        agent_name: Name of the agent to execute
        context: Execution context containing state and parameters

    Returns:
        Dictionary containing execution results and status

    Raises:
        AgentNotFoundError: If agent doesn't exist
        ExecutionTimeoutError: If execution exceeds timeout
    """

# Type hints are required
from typing import Dict, List, Optional, Union

def process_tasks(
    tasks: List[Dict[str, Any]],
    timeout: Optional[int] = None
) -> Dict[str, Union[str, int]]:
    pass

# Constants in UPPER_CASE
DEFAULT_TIMEOUT = 120
MAX_RETRIES = 3

# Private methods with leading underscore
def _internal_method(self):
    pass
```

### Commit Message Format

Follow the Conventional Commits specification:

```
type(scope): subject

body (optional)

footer (optional)
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Test additions or changes
- `chore`: Build process or auxiliary tool changes
- `perf`: Performance improvements

Examples:
```
feat(agents): add retry logic to Gemini agent

Implement exponential backoff for failed API calls.
Maximum 3 retries with delays of 1, 2, and 4 seconds.

Closes #123
```

```
fix(scheduler): prevent duplicate task execution

Add locking mechanism to ensure tasks aren't executed
multiple times when timer checks overlap.
```

### File Organization

```python
# Import order
import os
import sys
from datetime import datetime
from typing import Dict, List

import third_party_library
from third_party import specific_function

from src.agents import BaseAgent
from src.utils import logger

# File structure
"""Module docstring explaining the purpose."""

# Imports
# Constants
# Helper functions
# Classes
# Main execution
```

## Testing Guidelines

### Test Structure

```python
# tests/test_orchestrator.py
import pytest
from unittest.mock import Mock, patch

from src.orchestrator import AgentOrchestrator


class TestAgentOrchestrator:
    """Test cases for AgentOrchestrator."""

    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator instance for testing."""
        return AgentOrchestrator()

    def test_agent_registration(self, orchestrator):
        """Test that agents can be registered correctly."""
        # Arrange
        agent = Mock()
        agent.name = "test_agent"

        # Act
        orchestrator.register_agent(agent)

        # Assert
        assert "test_agent" in orchestrator.agents
        assert orchestrator.agents["test_agent"] == agent

    @patch('src.orchestrator.time')
    def test_scheduling(self, mock_time, orchestrator):
        """Test that scheduling works as expected."""
        # Test implementation
        pass
```

### Test Coverage Requirements

- Minimum 80% coverage for new code
- 90% coverage target for critical components
- Integration tests for agent interactions
- Performance tests for scheduling system

## Documentation

### Code Documentation

- All public functions must have docstrings
- Complex algorithms need inline comments
- Update relevant .md files when changing functionality

### API Documentation

When adding new endpoints or commands:

```markdown
## Command: `agent-council [command]`

**Description**: Brief description of what it does

**Usage**:
```bash
agent-council start --config custom.yaml
```

**Options**:
- `--config PATH`: Path to configuration file
- `--debug`: Enable debug logging
- `--daemon`: Run as daemon

**Examples**:
```bash
# Start with custom config
agent-council start --config my-config.yaml

# Run in debug mode
agent-council start --debug
```
```

## Review Process

### Before Submitting PR

- [ ] Tests pass locally
- [ ] Code follows style guide
- [ ] Documentation updated
- [ ] Changelog updated (if applicable)
- [ ] No merge conflicts
- [ ] PR description is clear

### PR Review Checklist

Reviewers will check:

- [ ] Code quality and style
- [ ] Test coverage
- [ ] Documentation completeness
- [ ] Performance impact
- [ ] Security considerations
- [ ] Backward compatibility

### After PR Approval

1. Squash commits if requested
2. Ensure CI passes
3. Maintainer will merge

## Release Process

### Version Numbering

We follow Semantic Versioning (MAJOR.MINOR.PATCH):

- MAJOR: Breaking changes
- MINOR: New features (backward compatible)
- PATCH: Bug fixes

### Release Checklist

1. Update version in `setup.py`
2. Update CHANGELOG.md
3. Run full test suite
4. Create release notes
5. Tag release: `git tag -a v1.2.3 -m "Release v1.2.3"`
6. Push tag: `git push origin v1.2.3`

## Getting Help

### Resources

- [Documentation](docs/)
- [Architecture Guide](ARCHITECTURE.md)
- [Issue Tracker](https://github.com/yourusername/agent-council/issues)

### Communication Channels

- GitHub Issues for bugs and features
- GitHub Discussions for questions
- Pull Request comments for code review

## Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Mentioned in release notes
- Given credit in commit messages

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to Agent Council! Your efforts help make AI orchestration better for everyone.