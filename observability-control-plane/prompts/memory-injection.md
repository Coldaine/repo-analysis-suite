# Memory Injection Template

This template is injected into agent prompts to provide historical context from Memori and Neo4j.

## Historical Fixes

The following fixes have been applied to similar issues in the past:

{{HISTORICAL_FIXES}}

## Pattern Recognition

Common patterns observed across incidents:

{{COMMON_PATTERNS}}

## Lessons Learned

Key takeaways from previous fixes:

1. Always check disk space before assuming database corruption
2. Docker volume permissions issues often manifest as database connection failures
3. Memory sync failures are usually network-related, not code-related
4. Neo4j password changes require both docker-compose and application code updates

## Context-Aware Recommendations

Based on historical data:
- Issue: {{ISSUE_TYPE}}
- Frequency: {{OCCURRENCE_COUNT}} times in past 30 days
- Average resolution time: {{AVG_RESOLUTION_TIME}}
- Success rate of automated fixes: {{SUCCESS_RATE}}

Use this historical context to inform your analysis and recommendations.
