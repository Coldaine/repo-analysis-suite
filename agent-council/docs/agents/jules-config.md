# Jules Agent Configuration

## Role: Asynchronous Developer

Jules is the primary development agent, executing code implementation tasks asynchronously. It works on development tasks assigned by Gemini and handles the heavy lifting of writing code.

## Schedule

- **Frequency**: Every 60 minutes
- **Batch Size**: 3 tasks per execution
- **Timeout**: 10 minutes per task
- **Mode**: Asynchronous web-based execution

## Configuration

### Command Line Usage

```bash
# Create a new session
jules new "implement user authentication with JWT tokens"

# Create session for specific repository
jules new --repo agent-council "add error handling to orchestrator.py"

# Create multiple parallel sessions
jules new --parallel 3 "write unit tests for all agent classes"

# Pull results
jules remote pull --session <session_id>
jules remote pull --session <session_id> --apply  # Apply patch locally
```

### Environment Variables

```env
JULES_API_KEY=<your-api-key>
JULES_DEFAULT_REPO=agent-council
JULES_MAX_PARALLEL=3
JULES_TIMEOUT=600
```

## Task Submission Strategy

Since Jules doesn't support MCP servers, we use a task queue approach:

### Task Queue Structure

```json
{
  "timestamp": "2024-01-01T10:00:00Z",
  "batch_id": "batch_001",
  "tasks": [
    {
      "id": "task_001",
      "description": "Implement error recovery in scheduler.py",
      "context": {
        "files_to_modify": ["src/scheduler/round_robin.py"],
        "requirements": ["Add try-catch blocks", "Implement exponential backoff"],
        "test_requirements": ["Unit tests", "Integration tests"]
      },
      "priority": 1
    },
    {
      "id": "task_002",
      "description": "Add logging to all agent execute() methods",
      "context": {
        "files_to_modify": ["src/agents/*.py"],
        "requirements": ["Structured JSON logging", "Include timestamps"],
        "test_requirements": ["Verify log output format"]
      },
      "priority": 2
    },
    {
      "id": "task_003",
      "description": "Create API documentation",
      "context": {
        "files_to_create": ["docs/api/README.md"],
        "requirements": ["Document all endpoints", "Include examples"],
        "test_requirements": ["Validate markdown syntax"]
      },
      "priority": 3
    }
  ]
}
```

## Prompt Templates

### Development Task Prompt

```markdown
You are Jules, an expert developer working on the Agent Council orchestration system.

## Task
{task_description}

## Context
- Repository: agent-council
- Language: Python 3.9+
- Framework: Asyncio-based orchestration
- Testing: Pytest with 90% coverage requirement

## Recent Code Changes
{recent_commits}

## Current Issues
{current_issues}

## Requirements
{requirements}

## Deliverables
1. Implement the requested feature/fix
2. Write comprehensive tests
3. Update documentation if needed
4. Ensure code follows PEP 8 standards
5. Maintain backward compatibility

## Success Criteria
- All tests pass
- No linting errors
- Code review ready
- Documentation updated

Please implement this task following best practices and our coding standards.
```

### Code Review Request

```markdown
Review the following code changes and provide feedback:

## Changed Files
{changed_files}

## Diff
{git_diff}

## Review Checklist
- [ ] Code follows project conventions
- [ ] Tests are comprehensive
- [ ] Documentation is updated
- [ ] No security vulnerabilities
- [ ] Performance is acceptable
- [ ] Error handling is proper

Provide specific feedback with line numbers.
```

## Integration with Orchestrator

### Task Submission Flow

```python
class JulesAgent(BaseAgent):
    async def submit_tasks(self, tasks: List[Dict]):
        """Submit tasks to Jules"""

        sessions = []
        for task in tasks[:3]:  # Max 3 tasks per hour
            # Create Jules session
            cmd = [
                "jules", "new",
                "--repo", self.repo,
                task['description']
            ]

            result = await self.run_command(cmd)
            session_id = self.extract_session_id(result)
            sessions.append(session_id)

            # Store session for later retrieval
            self.store_session(session_id, task)

        return sessions

    async def retrieve_results(self, session_ids: List[str]):
        """Pull results from Jules sessions"""

        results = []
        for session_id in session_ids:
            cmd = ["jules", "remote", "pull", "--session", session_id]
            result = await self.run_command(cmd)
            results.append(self.parse_jules_output(result))

        return results
```

## Task Categories

### 1. Feature Implementation
- New functionality
- API endpoints
- UI components
- Database models

### 2. Bug Fixes
- Error corrections
- Performance issues
- Security patches
- Edge case handling

### 3. Refactoring
- Code optimization
- Architecture improvements
- Technical debt reduction
- Pattern implementation

### 4. Testing
- Unit tests
- Integration tests
- E2E tests
- Performance tests

### 5. Documentation
- API documentation
- Code comments
- README updates
- Architecture docs

## Context Management

Since Jules doesn't have persistent context, we provide comprehensive context in each task:

```python
def build_jules_context(self, task):
    """Build comprehensive context for Jules"""

    return {
        "task": task,
        "project_structure": self.get_project_structure(),
        "recent_changes": self.get_recent_commits(hours=24),
        "dependencies": self.get_dependencies(),
        "coding_standards": self.get_coding_standards(),
        "test_examples": self.get_test_examples(),
        "related_files": self.get_related_files(task)
    }
```

## Performance Optimization

### Batching Strategy

```python
def batch_tasks(self, tasks):
    """Batch tasks for efficient execution"""

    # Group by complexity
    simple_tasks = [t for t in tasks if t['complexity'] == 'simple']
    medium_tasks = [t for t in tasks if t['complexity'] == 'medium']
    complex_tasks = [t for t in tasks if t['complexity'] == 'complex']

    # Create balanced batches
    batch = []
    if complex_tasks:
        batch.append(complex_tasks[0])  # One complex task
    if medium_tasks:
        batch.extend(medium_tasks[:2])  # Up to two medium tasks
    if len(batch) < 3 and simple_tasks:
        batch.extend(simple_tasks[:3-len(batch)])  # Fill with simple

    return batch[:3]  # Maximum 3 tasks
```

### Parallel Execution

```python
async def execute_parallel(self, tasks):
    """Execute multiple Jules sessions in parallel"""

    if len(tasks) > 1 and self.can_parallelize(tasks):
        cmd = [
            "jules", "new",
            "--repo", self.repo,
            "--parallel", str(len(tasks)),
            self.combine_task_descriptions(tasks)
        ]
        return await self.run_command(cmd)
    else:
        return await self.execute_sequential(tasks)
```

## Error Handling

### Common Issues

1. **Session Timeout**
   - Strategy: Check session status periodically
   - Recovery: Create new session with same task

2. **API Rate Limit**
   - Strategy: Implement rate limiting
   - Recovery: Queue tasks for next cycle

3. **Invalid Task Format**
   - Strategy: Validate before submission
   - Recovery: Reformat and retry

4. **Merge Conflicts**
   - Strategy: Pull latest changes first
   - Recovery: Resolve conflicts automatically where possible

### Error Recovery

```python
async def handle_jules_error(self, error, task):
    """Handle Jules-specific errors"""

    if "rate limit" in str(error).lower():
        # Queue for next cycle
        self.queue_task_for_retry(task)
        return "queued"

    elif "session timeout" in str(error).lower():
        # Create new session
        return await self.resubmit_task(task)

    elif "merge conflict" in str(error).lower():
        # Try to resolve
        await self.resolve_conflicts()
        return await self.resubmit_task(task)

    else:
        # Log and skip
        self.logger.error(f"Unhandled Jules error: {error}")
        return "failed"
```

## Monitoring

### Key Metrics

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Task Completion Rate | > 80% | < 60% |
| Average Task Time | < 5 min | > 10 min |
| Session Success Rate | > 90% | < 70% |
| Code Quality Score | > 8/10 | < 6/10 |

### Session Tracking

```python
class JulesSessionTracker:
    """Track Jules sessions and results"""

    def __init__(self):
        self.sessions = {}
        self.completed = []
        self.failed = []

    def track_session(self, session_id, task):
        self.sessions[session_id] = {
            'task': task,
            'started': datetime.now(),
            'status': 'running'
        }

    def update_session(self, session_id, status, result=None):
        if session_id in self.sessions:
            self.sessions[session_id]['status'] = status
            self.sessions[session_id]['completed'] = datetime.now()
            self.sessions[session_id]['result'] = result

            if status == 'completed':
                self.completed.append(session_id)
            elif status == 'failed':
                self.failed.append(session_id)
```

## Best Practices

### DO
- Provide clear, specific task descriptions
- Include all necessary context upfront
- Break complex tasks into smaller pieces
- Verify task completion before moving on
- Monitor session status regularly

### DON'T
- Submit vague or ambiguous tasks
- Exceed 3 tasks per hour
- Ignore failed sessions
- Submit duplicate tasks
- Forget to pull and apply results

## Example Workflows

### Feature Development

```bash
# 1. Create development session
jules new "Implement user authentication with JWT tokens, including login/logout endpoints, token refresh, and middleware"

# 2. Check session status
jules remote list --session

# 3. Pull results when complete
jules remote pull --session abc123 --apply

# 4. Run tests locally
pytest tests/auth/
```

### Bug Fix

```bash
# 1. Create fix session with context
jules new "Fix memory leak in orchestrator.py causing high memory usage after 24 hours of operation. Check for unclosed connections and circular references."

# 2. Monitor progress
jules remote list --session

# 3. Apply fix
jules remote pull --session def456 --apply

# 4. Verify fix
python scripts/test_memory.py
```

### Batch Processing

```bash
# Create multiple sessions for related tasks
for task in "Add logging to gemini_agent.py" "Add logging to jules_agent.py" "Add logging to qwen_agent.py"; do
    jules new "$task"
done

# List all sessions
jules remote list --session

# Pull all completed sessions
for session in $(jules remote list --session | grep completed | awk '{print $1}'); do
    jules remote pull --session $session --apply
done
```

## Troubleshooting

### Jules Not Creating Sessions

```bash
# Check Jules is logged in
jules login

# Verify API key
echo $JULES_API_KEY

# Test with simple task
jules new "Add comment to README.md"

# Check Jules logs
tail -f data/logs/jules/*.log
```

### Sessions Timing Out

- Reduce task complexity
- Provide more specific instructions
- Break into smaller subtasks
- Increase timeout setting

### Poor Code Quality

- Improve task descriptions
- Provide code examples
- Include test requirements
- Specify coding standards

## Future Enhancements

1. **MCP Server Support**: When available, maintain persistent context
2. **Smart Batching**: ML-based task grouping for efficiency
3. **Auto-Review**: Automatic code review before applying
4. **Dependency Resolution**: Automatic handling of task dependencies
5. **Learning System**: Improve task descriptions based on success rates