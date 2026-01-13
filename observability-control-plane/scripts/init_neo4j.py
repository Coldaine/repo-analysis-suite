#!/usr/bin/env python3
"""
Initialize Neo4j with indexes and constraints for observability control plane.
Creates indexes for better query performance and enforces data consistency.
"""
import os
import sys
import logging
from py2neo import Graph

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def init_neo4j():
    """Initialize Neo4j database with indexes and constraints"""
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "")

    if not neo4j_password:
        logger.error("NEO4J_PASSWORD environment variable not set")
        sys.exit(1)

    try:
        graph = Graph(neo4j_uri, auth=("neo4j", neo4j_password))
        logger.info(f"Connected to Neo4j at {neo4j_uri}")
    except Exception as e:
        logger.error(f"Failed to connect to Neo4j: {e}")
        sys.exit(1)

    # Create indexes for better query performance
    # Note: Neo4j 4.x+ uses different syntax for index creation
    indexes = [
        # Fix node indexes
        "CREATE INDEX fix_timestamp IF NOT EXISTS FOR (f:Fix) ON (f.ts)",
        "CREATE INDEX fix_issue IF NOT EXISTS FOR (f:Fix) ON (f.issue)",
        "CREATE INDEX fix_success IF NOT EXISTS FOR (f:Fix) ON (f.success)",

        # Agent node indexes
        "CREATE INDEX agent_name IF NOT EXISTS FOR (a:Agent) ON (a.name)",
        "CREATE INDEX agent_status IF NOT EXISTS FOR (a:Agent) ON (a.status)",
        "CREATE INDEX agent_last_seen IF NOT EXISTS FOR (a:Agent) ON (a.last_seen)",
    ]

    # Create unique constraints (optional but recommended)
    constraints = [
        "CREATE CONSTRAINT agent_name_unique IF NOT EXISTS FOR (a:Agent) REQUIRE a.name IS UNIQUE",
    ]

    logger.info("Creating indexes...")
    for query in indexes:
        try:
            graph.run(query)
            logger.info(f"✓ Executed: {query.split('FOR')[0]}FOR...")
        except Exception as e:
            # Index might already exist
            logger.warning(f"⚠ Index creation warning (may already exist): {e}")

    logger.info("Creating constraints...")
    for query in constraints:
        try:
            graph.run(query)
            logger.info(f"✓ Executed: {query.split('FOR')[0]}FOR...")
        except Exception as e:
            # Constraint might already exist
            logger.warning(f"⚠ Constraint creation warning (may already exist): {e}")

    # Verify setup
    logger.info("\nVerifying database setup...")
    try:
        # Count existing nodes
        result = graph.run("MATCH (n) RETURN count(n) as count").data()
        total_nodes = result[0]['count'] if result else 0

        result = graph.run("MATCH (f:Fix) RETURN count(f) as count").data()
        fix_count = result[0]['count'] if result else 0

        result = graph.run("MATCH (a:Agent) RETURN count(a) as count").data()
        agent_count = result[0]['count'] if result else 0

        logger.info(f"Database statistics:")
        logger.info(f"  Total nodes: {total_nodes}")
        logger.info(f"  Fix nodes: {fix_count}")
        logger.info(f"  Agent nodes: {agent_count}")

    except Exception as e:
        logger.error(f"Failed to verify database: {e}")

    logger.info("\n✓ Neo4j initialization complete!")


if __name__ == "__main__":
    init_neo4j()
