#!/usr/bin/env python3
"""
Test script for database operations.
Tests both Neo4j and Memori functionality.
"""
import os
import sys
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import database helpers
try:
    from database_helpers import DatabaseManager
    from agent_memory import (
        recall, remember, get_recent_fixes,
        get_all_agents, register_agent, find_similar_issues
    )
except ImportError as e:
    logger.error(f"Failed to import database modules: {e}")
    sys.exit(1)


def test_database_manager():
    """Test DatabaseManager class directly"""
    logger.info("=" * 60)
    logger.info("Testing DatabaseManager Class")
    logger.info("=" * 60)

    db = DatabaseManager()

    # Test database stats
    logger.info("\n1. Testing get_database_stats...")
    stats = db.get_database_stats()
    logger.info(f"Database Stats:")
    for key, value in stats.items():
        logger.info(f"  {key}: {value}")

    # Test Neo4j operations
    if db.graph:
        logger.info("\n2. Testing Neo4j operations...")

        # Register a test agent
        logger.info("  - Registering test agent...")
        success = db.register_agent("test-agent-1", "test-server")
        logger.info(f"    Agent registration: {'SUCCESS' if success else 'FAILED'}")

        # Store a test fix
        logger.info("  - Storing test fix...")
        db.remember_fix("test_issue", "test_solution", True)
        logger.info("    Fix stored")

        # Query recent fixes
        logger.info("  - Querying recent fixes...")
        fixes = db.get_recent_fixes(5)
        logger.info(f"    Found {len(fixes)} recent fixes")
        for fix in fixes[:3]:  # Show first 3
            logger.info(f"      - {fix.get('issue', 'N/A')}: {fix.get('solution', 'N/A')[:50]}...")

        # Query all agents
        logger.info("  - Querying all agents...")
        agents = db.get_all_agents()
        logger.info(f"    Found {len(agents)} agents")
        for agent in agents[:3]:  # Show first 3
            logger.info(f"      - {agent.get('name', 'N/A')} on {agent.get('server', 'N/A')}")

        # Find similar issues
        logger.info("  - Finding similar issues...")
        similar = db.find_similar_issues("test", 3)
        logger.info(f"    Found {len(similar)} similar issues")

        # Get issue patterns
        logger.info("  - Getting issue patterns (last 30 days)...")
        patterns = db.get_issue_patterns(30)
        logger.info(f"    Found {len(patterns)} issue patterns")
        for pattern in patterns[:3]:  # Show first 3
            logger.info(f"      - {pattern.get('issue', 'N/A')}: {pattern.get('count', 0)} occurrences")

    else:
        logger.warning("Neo4j not connected, skipping Neo4j tests")

    # Test Memori operations
    if db.memori_available:
        logger.info("\n3. Testing Memori operations...")

        logger.info("  - Recalling from Memori...")
        results = db.recall_fixes("test", 5)
        logger.info(f"    Found {len(results)} Memori results")
        for result in results[:3]:  # Show first 3
            logger.info(f"      - {str(result)[:80]}...")

    else:
        logger.warning("Memori not available, skipping Memori tests")


def test_agent_memory():
    """Test agent_memory module functions"""
    logger.info("\n" + "=" * 60)
    logger.info("Testing agent_memory Module")
    logger.info("=" * 60)

    # Test remember and recall
    logger.info("\n1. Testing remember/recall...")
    test_key = "issue:database-test"
    test_content = f"Test fix stored at {datetime.now().isoformat()}"

    logger.info(f"  - Storing fix: {test_key}")
    remember(test_key, test_content, metadata={"success": True, "type": "test"})
    logger.info("    Fix stored successfully")

    logger.info(f"  - Recalling fix: {test_key}")
    recalled = recall(test_key, limit=5)
    logger.info(f"    Recalled {len(recalled) if isinstance(recalled, list) else 1} items")
    if isinstance(recalled, list):
        for item in recalled[:3]:
            logger.info(f"      - {str(item)[:80]}...")
    else:
        logger.info(f"      - {str(recalled)[:80]}...")

    # Test get_recent_fixes
    logger.info("\n2. Testing get_recent_fixes...")
    try:
        fixes = get_recent_fixes(10)
        logger.info(f"  Found {len(fixes)} recent fixes")
        for fix in fixes[:3]:
            logger.info(f"    - {fix.get('issue', 'N/A')}: {fix.get('solution', 'N/A')[:50]}...")
    except Exception as e:
        logger.error(f"  Failed: {e}")

    # Test get_all_agents
    logger.info("\n3. Testing get_all_agents...")
    try:
        agents = get_all_agents()
        logger.info(f"  Found {len(agents)} agents")
        for agent in agents[:3]:
            logger.info(f"    - {agent.get('name', 'N/A')} ({agent.get('status', 'N/A')})")
    except Exception as e:
        logger.error(f"  Failed: {e}")

    # Test register_agent
    logger.info("\n4. Testing register_agent...")
    try:
        test_agent_name = f"test-agent-{datetime.now().timestamp()}"
        success = register_agent(test_agent_name, "test-server-123")
        logger.info(f"  Registration: {'SUCCESS' if success else 'FAILED'}")
    except Exception as e:
        logger.error(f"  Failed: {e}")

    # Test find_similar_issues
    logger.info("\n5. Testing find_similar_issues...")
    try:
        similar = find_similar_issues("test", 5)
        logger.info(f"  Found {len(similar)} similar issues")
        for issue in similar[:3]:
            logger.info(f"    - {issue.get('issue', 'N/A')}: {issue.get('occurrence_count', 0)} times")
    except Exception as e:
        logger.error(f"  Failed: {e}")


def test_error_handling():
    """Test error handling with invalid operations"""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Error Handling")
    logger.info("=" * 60)

    db = DatabaseManager()

    logger.info("\n1. Testing with invalid Neo4j query...")
    try:
        if db.graph:
            # This should fail gracefully
            result = db.get_fix_success_rate("nonexistent_fix_type")
            logger.info(f"  Success rate for nonexistent type: {result}")
        else:
            logger.info("  Neo4j not connected, skipping")
    except Exception as e:
        logger.error(f"  Error (expected): {e}")

    logger.info("\n2. Testing with empty results...")
    try:
        patterns = db.get_issue_patterns(0)  # 0 days = no results
        logger.info(f"  Patterns found: {len(patterns)}")
    except Exception as e:
        logger.error(f"  Error: {e}")


def main():
    """Run all tests"""
    logger.info("\n" + "=" * 60)
    logger.info("DATABASE OPERATIONS TEST SUITE")
    logger.info("=" * 60)
    logger.info(f"Started at: {datetime.now().isoformat()}")
    logger.info("")

    # Check environment
    logger.info("Environment Check:")
    logger.info(f"  NEO4J_URI: {os.getenv('NEO4J_URI', 'NOT SET')}")
    logger.info(f"  NEO4J_PASSWORD: {'SET' if os.getenv('NEO4J_PASSWORD') else 'NOT SET'}")
    logger.info(f"  DATABASE_URL: {os.getenv('DATABASE_URL', 'NOT SET')}")
    logger.info("")

    try:
        # Run test suites
        test_database_manager()
        test_agent_memory()
        test_error_handling()

        logger.info("\n" + "=" * 60)
        logger.info("ALL TESTS COMPLETED")
        logger.info("=" * 60)
        logger.info(f"Finished at: {datetime.now().isoformat()}")

    except Exception as e:
        logger.error(f"\nTest suite failed with error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
