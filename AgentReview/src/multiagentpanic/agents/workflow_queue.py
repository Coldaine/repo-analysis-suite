"""
Redis-backed workflow queue for deduplication and request management.

This module implements a Redis-based queue system that prevents duplicate workflow
requests from being processed multiple times, ensuring that multiple agents
requesting the same workflow operation (e.g., running CI) only results in a single
execution.
"""

from typing import Dict, Any, Optional, List
import asyncio
import json
import uuid
import hashlib
from datetime import datetime, timedelta

import redis.asyncio as redis
from pydantic import BaseModel, Field
from typing import Literal

from multiagentpanic.config.settings import get_settings
from multiagentpanic.domain.schemas import WorkflowRequest, CIStatus

class WorkflowQueue:
    """
    Redis-backed queue for workflow agent requests with deduplication.

    Uses Redis for:
    - Request deduplication (same request type/params = same request_id)
    - Request tracking and status management
    - Result storage and retrieval
    - Timeout handling
    """

    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize the workflow queue with Redis connection.

        Args:
            redis_url: Redis connection URL. If None, uses settings.database.redis_url
        """
        self.redis_url = redis_url or get_settings().database.redis_url
        self.redis_client = None
        self._queue_key = "workflow:queue"
        self._request_prefix = "workflow:request:"
        self._dedup_prefix = "workflow:dedup:"
        self._timeout = get_settings().workflow.queue_processing_timeout

    async def connect(self):
        """Establish Redis connection"""
        if self.redis_client is None:
            self.redis_client = await redis.from_url(self.redis_url)

    async def disconnect(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()

    def _generate_request_id(self, request: WorkflowRequest) -> str:
        """
        Generate deterministic request ID based on request type and parameters
        for deduplication purposes.
        """
        # Create hash of request type and params for deduplication
        dedup_key = f"{request.request_type}:{json.dumps(request.params, sort_keys=True)}"
        return hashlib.md5(dedup_key.encode()).hexdigest()

    def _get_request_key(self, request_id: str) -> str:
        """Get Redis key for request storage"""
        return f"{self._request_prefix}{request_id}"

    def _get_dedup_key(self, request_type: str, params_hash: str) -> str:
        """Get Redis key for deduplication tracking"""
        return f"{self._dedup_prefix}{request_type}:{params_hash}"

    async def enqueue(self, request: WorkflowRequest) -> str:
        """
        Enqueue a workflow request with deduplication.

        If the same request (type + params) is already pending/in_progress,
        returns the existing request_id instead of creating a new one.

        Args:
            request: WorkflowRequest to enqueue

        Returns:
            request_id: ID of the request (existing or new)
        """
        if not self.redis_client:
            await self.connect()

        # Generate deterministic request ID for deduplication
        request_id = self._generate_request_id(request)
        request_key = self._get_request_key(request_id)

        # Check if request with same type/params already exists and is active
        existing_request = await self.redis_client.hgetall(request_key)

        if existing_request and existing_request.get(b'status') in [b'pending', b'in_progress']:
            # Return existing request ID to avoid duplication
            return request_id

        # Create new request
        request_data = {
            'request_id': request_id,
            'requesting_agent': request.requesting_agent,
            'request_type': request.request_type,
            'params': json.dumps(request.params),
            'timestamp': request.timestamp.isoformat(),
            'status': 'pending',
            'result': None
        }

        # Store request in Redis hash
        await self.redis_client.hset(request_key, mapping=request_data)

        # Add to queue (list)
        await self.redis_client.lpush(self._queue_key, request_id)

        # Set expiration for request data (cleanup)
        await self.redis_client.expire(request_key, timedelta(seconds=self._timeout * 2))

        return request_id

    async def wait_for_result(self, request_id: str, timeout: int = None) -> Dict[str, Any]:
        """
        Wait for workflow request result with timeout.

        Args:
            request_id: ID of request to wait for
            timeout: Maximum wait time in seconds (default: from settings)

        Returns:
            Result dictionary from workflow execution

        Raises:
            TimeoutError: If request doesn't complete within timeout
            Exception: If request fails
        """
        if not self.redis_client:
            await self.connect()

        if timeout is None:
            timeout = self._timeout

        request_key = self._get_request_key(request_id)
        start_time = datetime.now()

        while (datetime.now() - start_time).seconds < timeout:
            # Get current request status
            request_data = await self.redis_client.hgetall(request_key)

            if not request_data:
                raise Exception(f"Request {request_id} not found")

            status = request_data.get(b'status', b'pending').decode()

            if status == 'completed':
                result_json = request_data.get(b'result', b'{}').decode()
                return json.loads(result_json)
            elif status == 'failed':
                error_data = request_data.get(b'result', b'{"error": "unknown"}').decode()
                raise Exception(f"Workflow request failed: {error_data}")

            # Poll every 1 second
            await asyncio.sleep(1)

        raise TimeoutError(f"Workflow request {request_id} timed out after {timeout} seconds")

    async def get_next_request(self) -> Optional[WorkflowRequest]:
        """
        Get the next pending request from the queue.

        Returns:
            WorkflowRequest if available, None otherwise
        """
        if not self.redis_client:
            await self.connect()

        # Get request ID from queue (FIFO)
        request_id = await self.redis_client.rpop(self._queue_key)

        if not request_id:
            return None

        request_id = request_id.decode()
        request_key = self._get_request_key(request_id)

        # Get request data
        request_data = await self.redis_client.hgetall(request_key)

        if not request_data:
            return None

        # Parse request data
        try:
            return WorkflowRequest(
                request_id=request_data[b'request_id'].decode(),
                requesting_agent=request_data[b'requesting_agent'].decode(),
                request_type=request_data[b'request_type'].decode(),
                params=json.loads(request_data[b'params'].decode()),
                timestamp=datetime.fromisoformat(request_data[b'timestamp'].decode()),
                status=request_data[b'status'].decode()
            )
        except (KeyError, json.JSONDecodeError):
            return None

    async def mark_in_progress(self, request_id: str):
        """Mark request as in progress"""
        if not self.redis_client:
            await self.connect()

        request_key = self._get_request_key(request_id)
        await self.redis_client.hset(request_key, 'status', 'in_progress')

    async def mark_completed(self, request_id: str, result: Dict[str, Any]):
        """Mark request as completed with result"""
        if not self.redis_client:
            await self.connect()

        request_key = self._get_request_key(request_id)
        await self.redis_client.hset(request_key, mapping={
            'status': 'completed',
            'result': json.dumps(result),
            'completed_at': datetime.now().isoformat()
        })

    async def mark_failed(self, request_id: str, error: str):
        """Mark request as failed with error message"""
        if not self.redis_client:
            await self.connect()

        request_key = self._get_request_key(request_id)
        await self.redis_client.hset(request_key, mapping={
            'status': 'failed',
            'result': json.dumps({'error': error}),
            'failed_at': datetime.now().isoformat()
        })

    async def get_request_status(self, request_id: str) -> Optional[str]:
        """Get current status of a request"""
        if not self.redis_client:
            await self.connect()

        request_key = self._get_request_key(request_id)
        request_data = await self.redis_client.hgetall(request_key)

        if not request_data:
            return None

        return request_data.get(b'status', b'pending').decode()

    async def cleanup_expired_requests(self):
        """Clean up expired/completed requests"""
        if not self.redis_client:
            await self.connect()

        # This would be implemented with Redis keyspace scanning
        # For now, rely on TTL expiration
        pass

# Singleton instance for global access
_workflow_queue_instance = None

def get_workflow_queue() -> WorkflowQueue:
    """
    Get the global workflow queue instance (singleton pattern).

    Returns:
        WorkflowQueue: Shared queue instance
    """
    global _workflow_queue_instance
    if _workflow_queue_instance is None:
        _workflow_queue_instance = WorkflowQueue()
    return _workflow_queue_instance