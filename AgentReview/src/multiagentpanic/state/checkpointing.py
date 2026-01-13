"""
Checkpointing module for LangGraph state persistence.

This module provides checkpointing implementations:
- InMemoryCheckpointer: For development and testing
- PostgresCheckpointer: Production-grade persistence using langgraph-checkpoint-postgres

Usage:
    from multiagentpanic.state.checkpointing import get_checkpointer
    
    # Get the appropriate checkpointer based on environment
    checkpointer = await get_async_checkpointer()
    
    # Use with LangGraph
    graph = workflow.compile(checkpointer=checkpointer)
"""

from typing import Any, Dict, Optional
from abc import ABC, abstractmethod
import os
import logging
import atexit
import asyncio

logger = logging.getLogger(__name__)


class Checkpointer(ABC):
    """Abstract base class for checkpointers (legacy interface)"""
    
    @abstractmethod
    def save(self, thread_id: str, checkpoint: Dict[str, Any]):
        pass

    @abstractmethod
    def load(self, thread_id: str) -> Optional[Dict[str, Any]]:
        pass


class InMemoryCheckpointer(Checkpointer):
    """
    Simple in-memory checkpointer for development and testing.
    
    Note: For LangGraph integration, prefer using langgraph's MemorySaver directly:
        from langgraph.checkpoint.memory import MemorySaver
    """
    
    def __init__(self):
        self._storage = {}

    def save(self, thread_id: str, checkpoint: Dict[str, Any]):
        self._storage[thread_id] = checkpoint

    def load(self, thread_id: str) -> Optional[Dict[str, Any]]:
        return self._storage.get(thread_id)


class PostgresCheckpointer(Checkpointer):
    """
    Legacy PostgreSQL checkpointer wrapper.
    
    For production use, prefer the async version via get_async_checkpointer()
    which uses langgraph-checkpoint-postgres directly.
    """
    
    def __init__(self, connection_string: str):
        self.conn_str = connection_string
        logger.info(f"Initialized PostgresCheckpointer (legacy wrapper)")

    def save(self, thread_id: str, checkpoint: Dict[str, Any]):
        """Legacy save - logs warning to use async version"""
        logger.warning(
            "PostgresCheckpointer.save() called - use async checkpointer for production. "
            "Consider using get_async_checkpointer() with langgraph-checkpoint-postgres."
        )

    def load(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """Legacy load - logs warning to use async version"""
        logger.warning(
            "PostgresCheckpointer.load() called - use async checkpointer for production. "
            "Consider using get_async_checkpointer() with langgraph-checkpoint-postgres."
        )
        return None


def get_checkpointer() -> Checkpointer:
    """
    Get a legacy checkpointer instance (for backward compatibility).
    
    For LangGraph applications, prefer:
    - get_langgraph_checkpointer() for sync operations
    - get_async_checkpointer() for async operations
    """
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return PostgresCheckpointer(db_url)
    return InMemoryCheckpointer()


def get_langgraph_checkpointer():
    """
    Get a LangGraph-compatible checkpointer for sync operations.
    
    Returns MemorySaver for development or PostgresSaver for production
    based on DATABASE_URL environment variable.
    
    Usage:
        checkpointer = get_langgraph_checkpointer()
        graph = workflow.compile(checkpointer=checkpointer)
    """
    from langgraph.checkpoint.memory import MemorySaver
    
    db_url = os.getenv("DATABASE_URL")
    
    if not db_url:
        logger.info("No DATABASE_URL found, using MemorySaver")
        return MemorySaver()
    
    try:
        from langgraph.checkpoint.postgres import PostgresSaver
        from psycopg.rows import dict_row
        import psycopg
        
        # Create connection with required settings
        conn = psycopg.connect(db_url, autocommit=True, row_factory=dict_row)
        checkpointer = PostgresSaver(conn)
        
        # Setup tables on first use
        checkpointer.setup()

        def _close_conn():
            try:
                conn.close()
            except Exception as close_err:
                logger.warning(f"Failed to close Postgres connection: {close_err}")
        atexit.register(_close_conn)
        
        logger.info("Using PostgresSaver for checkpointing")
        return checkpointer
        
    except ImportError as e:
        logger.warning(f"langgraph-checkpoint-postgres not available: {e}. Using MemorySaver.")
        return MemorySaver()
    except Exception as e:
        logger.error(f"Failed to initialize PostgresSaver: {e}. Falling back to MemorySaver.")
        return MemorySaver()


async def get_async_checkpointer():
    """
    Get a LangGraph-compatible async checkpointer.
    
    Returns AsyncPostgresSaver for production (when DATABASE_URL is set)
    or MemorySaver for development.
    
    Usage:
        checkpointer = await get_async_checkpointer()
        graph = workflow.compile(checkpointer=checkpointer)
    
    Note: For proper resource management with AsyncPostgresSaver,
    prefer using it as an async context manager directly:
    
        async with AsyncPostgresSaver.from_conn_string(db_url) as checkpointer:
            await checkpointer.setup()
            graph = workflow.compile(checkpointer=checkpointer)
    """
    from langgraph.checkpoint.memory import MemorySaver
    
    db_url = os.getenv("DATABASE_URL")
    
    if not db_url:
        logger.info("No DATABASE_URL found, using MemorySaver")
        return MemorySaver()
    
    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

        context = AsyncPostgresSaver.from_conn_string(db_url)
        checkpointer = await context.__aenter__()
        await checkpointer.setup()

        async def _close():
            try:
                await context.__aexit__(None, None, None)
            except Exception as close_err:
                logger.warning(f"Failed to close AsyncPostgresSaver: {close_err}")

        # Expose a best-effort cleanup hook for callers
        setattr(checkpointer, "close", _close)
        atexit.register(lambda: asyncio.run(_close()))

        logger.info("Using AsyncPostgresSaver for checkpointing")
        return checkpointer

    except ImportError as e:
        logger.warning(f"langgraph-checkpoint-postgres not available: {e}. Using MemorySaver.")
        return MemorySaver()
    except Exception as e:
        logger.error(f"Failed to initialize AsyncPostgresSaver: {e}. Falling back to MemorySaver.")
        return MemorySaver()


class AsyncPostgresCheckpointerContext:
    """
    Async context manager for proper AsyncPostgresSaver lifecycle.
    
    Usage:
        async with AsyncPostgresCheckpointerContext() as checkpointer:
            graph = workflow.compile(checkpointer=checkpointer)
            # ... use graph ...
    """
    
    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or os.getenv("DATABASE_URL")
        self._checkpointer = None
        self._context = None
    
    async def __aenter__(self):
        from langgraph.checkpoint.memory import MemorySaver
        
        if not self.db_url:
            logger.info("No DATABASE_URL, using MemorySaver")
            self._checkpointer = MemorySaver()
            return self._checkpointer
        
        try:
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
            
            self._context = AsyncPostgresSaver.from_conn_string(self.db_url)
            self._checkpointer = await self._context.__aenter__()
            await self._checkpointer.setup()
            
            logger.info("Using AsyncPostgresSaver for checkpointing")
            return self._checkpointer
            
        except ImportError as e:
            logger.warning(f"langgraph-checkpoint-postgres not available: {e}")
            self._checkpointer = MemorySaver()
            return self._checkpointer
        except Exception as e:
            logger.error(f"Failed to initialize AsyncPostgresSaver: {e}")
            self._checkpointer = MemorySaver()
            return self._checkpointer
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._context is not None:
            await self._context.__aexit__(exc_type, exc_val, exc_tb)

