#!/usr/bin/env python3
"""
Database management for observability control plane.
Provides Neo4j READ/WRITE operations and Memori initialization.
"""
import os
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from py2neo import Graph

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages Neo4j and Memori database operations"""

    def __init__(self):
        # Neo4j configuration
        self.neo4j_uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
        self.neo4j_password = os.getenv("NEO4J_PASSWORD", "")

        # Initialize Neo4j
        try:
            self.graph = Graph(self.neo4j_uri, auth=("neo4j", self.neo4j_password))
            logger.info("Neo4j connected successfully")
        except Exception as e:
            logger.error(f"Neo4j connection failed: {e}")
            self.graph = None

        # Initialize Memori with PostgreSQL
        # Memori initialization happens on import, but we can track it here
        self.memori_available = False
        try:
            # Check if memori module is importable
            import memori
            database_url = os.getenv("DATABASE_URL",
                                     "postgresql://memori:change-me@postgres:5432/memori")
            # Note: Memori auto-initializes based on environment variables
            # MEMORI_DATABASE_URL should be set in environment
            self.memori_available = True
            logger.info("Memori module available")
        except ImportError as e:
            logger.error(f"Memori module not available: {e}")
        except Exception as e:
            logger.error(f"Memori initialization issue: {e}")

    # ===== Neo4j READ Operations =====

    def get_recent_fixes(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent fixes from Neo4j"""
        if not self.graph:
            logger.warning("Neo4j not available, returning empty list")
            return []

        query = """
        MATCH (f:Fix)
        RETURN f.issue as issue,
               f.solution as solution,
               f.ts as timestamp,
               f.success as success
        ORDER BY f.ts DESC
        LIMIT $limit
        """
        try:
            results = self.graph.run(query, limit=limit).data()
            return results
        except Exception as e:
            logger.error(f"Failed to get recent fixes: {e}")
            return []

    def find_similar_issues(self, issue_type: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Find similar issues and their solutions"""
        if not self.graph:
            logger.warning("Neo4j not available, returning empty list")
            return []

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
        try:
            results = self.graph.run(query, issue_type=issue_type, limit=limit).data()
            return results
        except Exception as e:
            logger.error(f"Failed to find similar issues: {e}")
            return []

    def get_fix_success_rate(self, fix_type: str) -> float:
        """Calculate success rate for a specific fix type"""
        if not self.graph:
            logger.warning("Neo4j not available, returning 0.0")
            return 0.0

        query = """
        MATCH (f:Fix)
        WHERE f.solution CONTAINS $fix_type
        WITH count(*) as total,
             sum(CASE WHEN f.success = true THEN 1 ELSE 0 END) as successful
        RETURN CASE WHEN total > 0
               THEN toFloat(successful) / toFloat(total)
               ELSE 0.0 END as success_rate
        """
        try:
            result = self.graph.run(query, fix_type=fix_type).data()
            return result[0]['success_rate'] if result else 0.0
        except Exception as e:
            logger.error(f"Failed to calculate success rate: {e}")
            return 0.0

    def get_all_agents(self) -> List[Dict[str, Any]]:
        """Get all registered agents"""
        if not self.graph:
            logger.warning("Neo4j not available, returning empty list")
            return []

        query = """
        MATCH (a:Agent)
        RETURN a.name as name,
               a.status as status,
               a.last_seen as last_seen,
               a.server as server
        ORDER BY a.last_seen DESC
        """
        try:
            results = self.graph.run(query).data()
            return results
        except Exception as e:
            logger.error(f"Failed to get agents: {e}")
            return []

    def register_agent(self, name: str, server: str) -> bool:
        """Register or update an agent"""
        if not self.graph:
            logger.warning("Neo4j not available, cannot register agent")
            return False

        query = """
        MERGE (a:Agent {name: $name})
        SET a.server = $server,
            a.status = 'active',
            a.last_seen = timestamp()
        RETURN a
        """
        try:
            self.graph.run(query, name=name, server=server)
            logger.info(f"Registered agent: {name} on server: {server}")
            return True
        except Exception as e:
            logger.error(f"Failed to register agent: {e}")
            return False

    def get_issue_patterns(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get common issue patterns from the last N days"""
        if not self.graph:
            logger.warning("Neo4j not available, returning empty list")
            return []

        # Calculate cutoff timestamp (Neo4j uses milliseconds since epoch)
        cutoff = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
        query = """
        MATCH (f:Fix)
        WHERE f.ts > $cutoff
        WITH f.issue as issue, count(*) as count
        RETURN issue, count
        ORDER BY count DESC
        LIMIT 10
        """
        try:
            results = self.graph.run(query, cutoff=cutoff).data()
            return results
        except Exception as e:
            logger.error(f"Failed to get issue patterns: {e}")
            return []

    # ===== Memori Operations =====

    def recall_fixes(self, context: str, limit: int = 10) -> List[str]:
        """Recall relevant fixes from Memori"""
        if not self.memori_available:
            logger.warning("Memori not available, returning empty list")
            return []

        try:
            from memori import recall
            results = recall(context, limit=limit)
            # Memori returns various formats, normalize to list of strings
            if isinstance(results, list):
                return [str(r) for r in results]
            elif isinstance(results, str):
                return [results]
            else:
                return [str(results)]
        except Exception as e:
            logger.error(f"Memori recall failed: {e}")
            return []

    def remember_fix(self, issue: str, solution: str, success: bool = True):
        """Store a fix in both Neo4j and Memori"""
        # Store in Neo4j
        if self.graph:
            query = """
            CREATE (f:Fix {
                issue: $issue,
                solution: $solution,
                success: $success,
                ts: timestamp()
            })
            RETURN f
            """
            try:
                self.graph.run(query, issue=issue, solution=solution, success=success)
                logger.info(f"Stored fix in Neo4j: {issue}")
            except Exception as e:
                logger.error(f"Failed to store in Neo4j: {e}")

        # Store in Memori
        if self.memori_available:
            try:
                from memori import remember
                content = f"Issue: {issue}\nSolution: {solution}\nSuccess: {success}"
                remember(f"issue:{issue}", content, metadata={"type": "fix", "success": success})
                logger.info(f"Stored fix in Memori: {issue}")
            except Exception as e:
                logger.error(f"Failed to store in Memori: {e}")

    def get_database_stats(self) -> Dict[str, Any]:
        """Get statistics about the databases"""
        stats = {
            "neo4j_connected": self.graph is not None,
            "memori_available": self.memori_available,
        }

        if self.graph:
            try:
                # Count nodes and relationships
                node_count = self.graph.run("MATCH (n) RETURN count(n) as count").data()[0]['count']
                fix_count = self.graph.run("MATCH (f:Fix) RETURN count(f) as count").data()[0]['count']
                agent_count = self.graph.run("MATCH (a:Agent) RETURN count(a) as count").data()[0]['count']

                stats.update({
                    "total_nodes": node_count,
                    "total_fixes": fix_count,
                    "total_agents": agent_count,
                })
            except Exception as e:
                logger.error(f"Failed to get Neo4j stats: {e}")
                stats["neo4j_error"] = str(e)

        return stats

# Global instance
db_manager = DatabaseManager()

if __name__ == "__main__":
    # Quick test of database connections
    logging.basicConfig(level=logging.INFO)
    print("Database Manager Test")
    print("=" * 50)

    stats = db_manager.get_database_stats()
    print(f"Database Stats: {json.dumps(stats, indent=2)}")

    if db_manager.graph:
        print("\nTesting Neo4j operations...")
        agents = db_manager.get_all_agents()
        print(f"Found {len(agents)} agents")

        fixes = db_manager.get_recent_fixes(5)
        print(f"Found {len(fixes)} recent fixes")
    else:
        print("\nNeo4j not connected")
