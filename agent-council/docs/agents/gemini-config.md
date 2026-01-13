# Gemini Agent Configuration

## Role: Project Reviewer & Architect

Gemini serves as the strategic reviewer and architectural decision-maker in the Agent Council system. It reviews progress, identifies issues, and proposes next steps for the other agents.

## Schedule

- **Frequency**: Every 10 minutes
- **Timeout**: 2 minutes per execution
- **Retry Policy**: 3 attempts with exponential backoff

## Configuration

### Command Line Arguments

```bash
gemini \
  -p "<prompt>" \           # Prompt with context
  -y \                      # YOLO mode (non-interactive)
  --model gemini-2.5-flash \ # Fast model for quick reviews
  --output-format json \    # Structured output
  --sandbox false          # Sandbox not needed for review
```

### Environment Variables

```env
GEMINI_API_KEY=<your-api-key>
GEMINI_MODEL=gemini-2.5-flash
GEMINI_TIMEOUT=120
```

## Prompts

### Review Prompt Template

```markdown
You are a senior architect reviewing an AI agent orchestration project.

## Current Project State
{project_state}

## Recent Agent Activities
- Gemini (last run): {gemini_last_output}
- Jules (last run): {jules_last_output}
- Qwen (last run): {qwen_last_output}
- Goose (last run): {goose_last_output}

## Recent Errors
{recent_errors}

## Your Tasks
1. Review the progress made in the last cycle
2. Identify any architectural issues or code quality problems
3. Determine if agents are working effectively together
4. Propose the next 3-5 high-priority tasks
5. Flag any blockers or critical issues

## Output Format
Provide your analysis in the following JSON structure:
{
  "summary": "Brief overview of current state",
  "progress_assessment": {
    "completed_tasks": [],
    "quality_score": 0-10,
    "concerns": []
  },
  "issues_identified": [
    {
      "severity": "critical|high|medium|low",
      "description": "",
      "recommended_action": "",
      "assigned_agent": "jules|qwen|goose"
    }
  ],
  "recommendations": {
    "immediate_tasks": [],
    "architectural_changes": [],
    "process_improvements": []
  },
  "priority_queue": [
    {
      "task": "",
      "agent": "",
      "priority": 1-5,
      "estimated_complexity": "simple|medium|complex"
    }
  ]
}
```

## Context Building

Gemini receives a comprehensive context including:

1. **Project State**: Current phase, completed features, technical debt
2. **Agent Performance**: Execution times, success rates, error counts
3. **Code Metrics**: Test coverage, linting results, bundle sizes
4. **Recent Changes**: Git commits, file modifications, PR status
5. **External Factors**: API limits, resource usage, time constraints

## Decision Authority

Gemini has authority to:

- **Redirect Focus**: Change project priorities based on analysis
- **Pause Agents**: Recommend stopping specific agents if issues detected
- **Escalate Issues**: Flag critical problems for human intervention
- **Approve Deployments**: Green-light production deployments
- **Trigger Rollbacks**: Recommend reverting problematic changes

## Integration Points

### Input Sources
- State management system (memory.json)
- Agent output logs
- Git repository status
- System metrics

### Output Consumers
- Jules: Receives development task assignments
- Qwen: Gets analysis focus areas
- Goose: Receives execution commands
- Orchestrator: Updates scheduling based on recommendations

## Performance Metrics

Target metrics for Gemini:

| Metric | Target | Actual |
|--------|--------|--------|
| Response Time | < 2s | - |
| Token Usage | < 4000/request | - |
| Accuracy | > 90% | - |
| False Positives | < 5% | - |

## Error Handling

### Common Errors

1. **API Rate Limit**
   - Strategy: Exponential backoff
   - Fallback: Skip cycle, maintain previous recommendations

2. **Context Too Large**
   - Strategy: Summarize older context
   - Fallback: Use rolling 2-hour window

3. **Invalid JSON Response**
   - Strategy: Retry with clarified prompt
   - Fallback: Extract key points as text

4. **Timeout**
   - Strategy: Reduce context size
   - Fallback: Use cached previous analysis

## Best Practices

### DO
- Keep reviews focused and actionable
- Prioritize blockers and critical issues
- Consider agent capabilities when assigning tasks
- Maintain consistent output format
- Balance between progress and quality

### DON'T
- Micromanage other agents
- Request impossible tasks
- Ignore error patterns
- Duplicate recent recommendations
- Exceed token limits

## Example Outputs

### Successful Review

```json
{
  "summary": "Project progressing well with 3 features completed. Minor performance issues detected.",
  "progress_assessment": {
    "completed_tasks": [
      "API endpoint implementation",
      "Database schema setup",
      "Basic UI components"
    ],
    "quality_score": 7,
    "concerns": ["Test coverage at 72%, below 80% target"]
  },
  "issues_identified": [
    {
      "severity": "medium",
      "description": "Database queries not optimized",
      "recommended_action": "Add indexes to user and session tables",
      "assigned_agent": "goose"
    }
  ],
  "recommendations": {
    "immediate_tasks": [
      "Increase test coverage for API endpoints",
      "Implement caching layer"
    ],
    "architectural_changes": [],
    "process_improvements": ["Add performance benchmarks to CI"]
  },
  "priority_queue": [
    {
      "task": "Write integration tests for auth flow",
      "agent": "jules",
      "priority": 1,
      "estimated_complexity": "medium"
    },
    {
      "task": "Analyze bundle size and optimize",
      "agent": "qwen",
      "priority": 2,
      "estimated_complexity": "simple"
    }
  ]
}
```

### Error Detection

```json
{
  "summary": "Critical issue detected: Production deployment failed",
  "progress_assessment": {
    "completed_tasks": [],
    "quality_score": 3,
    "concerns": ["Deployment pipeline broken", "Tests failing"]
  },
  "issues_identified": [
    {
      "severity": "critical",
      "description": "TypeScript compilation errors in production build",
      "recommended_action": "Fix type errors immediately",
      "assigned_agent": "jules"
    }
  ],
  "recommendations": {
    "immediate_tasks": ["STOP all feature development", "Fix build errors"],
    "architectural_changes": [],
    "process_improvements": ["Add pre-commit hooks for type checking"]
  },
  "priority_queue": [
    {
      "task": "Fix TypeScript errors in src/api/routes.ts",
      "agent": "jules",
      "priority": 1,
      "estimated_complexity": "simple"
    }
  ]
}
```

## Monitoring

### Key Metrics to Track

1. **Review Quality**: Are recommendations being followed?
2. **Issue Detection Rate**: How many issues caught early?
3. **Task Completion Rate**: Are assigned tasks being completed?
4. **Response Time**: Is Gemini responding quickly enough?
5. **Token Efficiency**: Are we staying within limits?

### Alerting Thresholds

- Response time > 5 seconds
- Token usage > 8000 per request
- Error rate > 10%
- Consecutive failures > 3

## Optimization Tips

1. **Context Window Management**
   - Summarize older interactions
   - Focus on recent 2-4 hours
   - Prioritize error logs

2. **Prompt Engineering**
   - Use clear, structured prompts
   - Provide examples in prompt
   - Specify exact output format

3. **Model Selection**
   - Use gemini-2.5-flash for speed
   - Switch to gemini-2.5-pro for complex analysis
   - Consider gemini-exp for experimental features

## Troubleshooting

### Gemini Not Responding

```bash
# Check if Gemini CLI is working
gemini --version

# Test with simple prompt
gemini -p "Hello, respond with 'OK'" -y

# Check API key
echo $GEMINI_API_KEY

# View Gemini logs
tail -f data/logs/gemini/*.log
```

### Poor Quality Reviews

- Reduce context size
- Provide more specific examples
- Adjust prompt temperature
- Check for context pollution

### High Token Usage

- Implement context summarization
- Remove redundant information
- Use more efficient prompts
- Consider batching reviews

## Future Enhancements

1. **Multi-Model Support**: Use different models for different review types
2. **Learning System**: Adapt based on successful recommendations
3. **Predictive Analysis**: Anticipate issues before they occur
4. **Cross-Agent Coordination**: Direct agent-to-agent communication
5. **Visual Analysis**: Review UI/UX through screenshots