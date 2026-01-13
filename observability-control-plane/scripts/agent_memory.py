#!/usr/bin/env python3
"""
Enhanced memory operations using both direct connections and DatabaseManager.
Provides unified interface to both Memori and Neo4j databases.
Maintains backward compatibility with existing code.
"""

import os
import logging
from typing import Any, Dict, List, Optional
from memori import recall as memori_recall, remember as memori_remember
from py2neo import Graph

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Neo4j connection - credentials from environment
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")

# Initialize graph connection (lazy - only when needed)
_graph = None


def _get_graph() -> Graph:
    """Get or create Neo4j graph connection"""
    global _graph
    if _graph is None:
        if not NEO4J_PASSWORD:
            logger.warning("NEO4J_PASSWORD not set, graph operations will fail")
            raise ValueError("Neo4j credentials not configured")
        _graph = Graph(NEO4J_URI, auth=("neo4j", NEO4J_PASSWORD))
    return _graph


def recall(key: str, limit: int = 10) -> Any:
    """
    Recall from Memori with optional Neo4j augmentation for issue queries
    """
    # If key starts with "issue:", try to also fetch from Neo4j
    if key.startswith("issue:"):
        issue_type = key.replace("issue:", "")
        combined_results = []

        # Get from Memori
        try:
            memori_results = memori_recall(key, limit=limit)
            if isinstance(memori_results, list):
                combined_results.extend(memori_results)
            elif memori_results:
                combined_results.append(memori_results)
        except Exception as e:
            logger.error(f"Memori recall failed: {e}")

        # Get from Neo4j
        try:
            similar_issues = find_similar_issues(issue_type, limit=5)
            for issue in similar_issues:
                combined_results.append(
                    f"[Neo4j] Issue: {issue['issue']}, Solution: {issue['solution']}, "
                    f"Success: {issue.get('success', 'unknown')}"
                )
        except Exception as e:
            logger.error(f"Neo4j query failed: {e}")

        return combined_results[:limit]

    # Default: use Memori only
    return memori_recall(key, limit=limit)


def remember(key: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
    """
    Remember in Memori (and optionally Neo4j if it's a fix)
    """
    # Store in Memori
    memori_remember(key, content, metadata=metadata or {})

    # If this looks like a fix (key starts with "issue:"), also store in Neo4j
    if key.startswith("issue:"):
        try:
            issue = key.replace("issue:", "")
            success = True
            if metadata and 'success' in metadata:
                success = metadata['success']
            elif 'failed' in content.lower() or 'error' in content.lower():
                success = False

            graph = _get_graph()
            graph.run(
                """
                CREATE (f:Fix {
                    issue: $issue,
                    solution: $solution,
                    success: $success,
                    ts: timestamp()
                })
                """,
                issue=issue,
                solution=content,
                success=success
            )
        except Exception as e:
            logger.error(f"Failed to store fix in Neo4j: {e}")


def find_similar_issues(issue_type: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Find similar issues from Neo4j based on issue type
    """
    try:
        graph = _get_graph()
        query = """
        MATCH (f:Fix)
        WHERE f.issue CONTAINS $issue_type
        RETURN f.issue as issue,
               f.solution as solution,
               f.success as success,
               count(*) as occurrence_count
        ORDER BY occurrence_count DESC
        LIMIT $limit
        """
        result = graph.run(query, issue_type=issue_type, limit=limit)

        issues = []
        for record in result:
            issues.append({
                "issue": record["issue"],
                "solution": record["solution"],
                "success": record.get("success", True),
                "occurrence_count": record["occurrence_count"]
            })

        return issues
    except Exception as e:
        logger.error(f"Error finding similar issues: {e}")
        return []


def get_recent_fixes(limit: int = 20) -> List[Dict[str, Any]]:
    """
    Get recent fixes from Neo4j.
    Returns list of fix records.
    """
    try:
        graph = _get_graph()
        query = """
        MATCH (f:Fix)
        RETURN f.issue as issue, f.solution as solution, f.ts as timestamp
        ORDER BY f.ts DESC
        LIMIT $limit
        """
        result = graph.run(query, limit=limit)

        fixes = []
        for record in result:
            fixes.append({
                "issue": record["issue"],
                "solution": record["solution"],
                "timestamp": record["timestamp"],
                "success": True  # Assume success if it's logged
            })

        return fixes
    except Exception as e:
        logger.error(f"Error fetching recent fixes: {e}")
        return []


def get_all_agents() -> List[Dict[str, Any]]:
    """
    Get all registered agents from Neo4j.
    Returns list of agent records.
    """
    try:
        graph = _get_graph()
        query = """
        MATCH (a:Agent)
        RETURN a.name as name, a.server as server, a.status as status, a.last_seen as last_seen
        ORDER BY a.last_seen DESC
        """
        result = graph.run(query)

        agents = []
        for record in result:
            agents.append({
                "name": record["name"],
                "server": record["server"] or "unknown",
                "status": record["status"] or "active",
                "last_seen": record["last_seen"]
            })

        return agents
    except Exception as e:
        logger.error(f"Error fetching agents: {e}")
        return []


def register_agent(name: str, server: str) -> bool:
    """
    Register or update an agent in Neo4j.
    Returns True if successful, False otherwise.
    """
    try:
        graph = _get_graph()
        query = """
        MERGE (a:Agent {name: $name})
        SET a.server = $server,
            a.status = 'active',
            a.last_seen = timestamp()
        RETURN a
        """
        result = graph.run(query, name=name, server=server)

        # Consume result to ensure query executed
        list(result)
        return True
    except Exception as e:
        logger.error(f"Error registering agent {name}: {e}")
        return False
