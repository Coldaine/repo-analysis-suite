"""
Simple workflow agent tests that don't require full settings validation.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
import json
from datetime import datetime

from multiagentpanic.agents.workflow_queue import WorkflowQueue
from multiagentpanic.agents.workflow_agent import WorkflowAgent, GitHubClient
from multiagentpanic.domain.schemas import WorkflowRequest

@pytest.mark.asyncio
async def test_workflow_queue_basic():
    """Test basic workflow queue functionality"""
    with patch('multiagentpanic.agents.workflow_queue.redis.from_url', new_callable=AsyncMock) as mock_from_url:
        mock_client = AsyncMock()
        mock_from_url.return_value = mock_client

        # Mock Redis operations
        mock_client.hgetall.return_value = {}
        mock_client.hset.return_value = True
        mock_client.lpush.return_value = True
        mock_client.rpop.return_value = None
        mock_client.expire.return_value = True

        queue = WorkflowQueue(redis_url="redis://localhost:6379/0")
        await queue.connect()

        # Test basic enqueue
        request = WorkflowRequest(
            request_id="test1",
            requesting_agent="test_agent",
            request_type="run_ci",
            params={"pr_number": 1},
            timestamp=datetime.now()
        )

        with patch.object(queue, '_generate_request_id', return_value="test1"):
            request_id = await queue.enqueue(request)
            assert request_id == "test1"

        # Test request status
        mock_client.hgetall.return_value = {
            b'status': b'pending',
            b'result': b'{}'
        }

        status = await queue.get_request_status("test1")
        assert status == "pending"

        await queue.disconnect()

@pytest.mark.asyncio
async def test_workflow_agent_singleton():
    """Test workflow agent singleton pattern"""
    with patch('multiagentpanic.agents.workflow_agent.GitHubClient'):
        # Clear any existing instance
        WorkflowAgent._instance = None

        agent1 = WorkflowAgent.get_instance()
        agent2 = WorkflowAgent.get_instance()

        assert agent1 is agent2

        # Test that direct instantiation fails
        with pytest.raises(RuntimeError):
            WorkflowAgent()

@pytest.mark.asyncio
async def test_workflow_agent_start_stop():
    """Test workflow agent start/stop"""
    with patch('multiagentpanic.agents.workflow_agent.GitHubClient'):
        # Clear any existing instance
        WorkflowAgent._instance = None

        agent = WorkflowAgent.get_instance()

        # Test start
        await agent.start()
        assert agent.is_running is True

        # Test stop
        await agent.stop()
        assert agent.is_running is False

@pytest.mark.asyncio
async def test_github_client_mock():
    """Test GitHub client with mock"""
    with patch('multiagentpanic.agents.workflow_agent.Github') as mock_github:
        mock_client = Mock()
        mock_github.return_value = mock_client

        github_client = GitHubClient(token="test_token")

        # Test PR info
        mock_repo = Mock()
        mock_pr = Mock()
        mock_pr.title = "Test PR"
        mock_pr.body = "Test body"
        mock_pr.state = "open"
        mock_pr.head.ref = "test-branch"
        mock_pr.head.sha = "abc123"
        mock_pr.base.ref = "main"
        mock_pr.html_url = "https://github.com/test/repo/pull/1"
        mock_pr.number = 1

        mock_client.get_repo.return_value = mock_repo
        mock_repo.get_pull.return_value = mock_pr

        pr_info = await github_client.get_pr_info("test/repo", 1)

        assert pr_info["title"] == "Test PR"
        assert pr_info["head_ref"] == "test-branch"

@pytest.mark.asyncio
async def test_workflow_agent_ci_trigger():
    """Test workflow agent CI triggering"""
    with patch('multiagentpanic.agents.workflow_agent.GitHubClient') as mock_github_class:
        mock_github = AsyncMock()
        mock_github_class.return_value = mock_github

        # Clear any existing instance
        WorkflowAgent._instance = None

        agent = WorkflowAgent.get_instance()

        # Mock queue
        mock_queue = AsyncMock()
        mock_queue.enqueue.return_value = "test_request_id"
        agent.queue = mock_queue

        # Test CI trigger
        request_id = await agent.trigger_ci(pr_number=42, repo_name="test/repo")

        assert request_id == "test_request_id"
        mock_queue.enqueue.assert_called_once()

@pytest.mark.asyncio
async def test_workflow_agent_execute_request():
    """Test workflow agent request execution"""
    with patch('multiagentpanic.agents.workflow_agent.GitHubClient') as mock_github_class:
        mock_github = AsyncMock()
        mock_github.get_pr_info.return_value = {"head_ref": "test-branch"}
        mock_github.trigger_workflow.return_value = {"id": 123, "status": "queued"}
        mock_github.wait_for_workflow.return_value = {"status": "completed", "conclusion": "success", "output": {"coverage_report": {"lines": 85}}}
        mock_github_class.return_value = mock_github

        # Clear any existing instance
        WorkflowAgent._instance = None

        with patch('multiagentpanic.config.settings.get_settings') as mock_settings:
            mock_settings.return_value.workflow.ci_provider = "none"

            agent = WorkflowAgent.get_instance()

            # Test mock CI execution
            request = WorkflowRequest(
                request_id="test_exec",
                requesting_agent="test_agent",
                request_type="run_ci",
                params={"pr_number": 42, "repo_name": "test/repo"},
                timestamp=datetime.now()
            )

            result = await agent._execute_request(request)

            assert "tests_passed" in result
            assert "coverage_percentage" in result
            assert result["status"] == "completed"

if __name__ == "__main__":
    asyncio.run(test_workflow_queue_basic())
    asyncio.run(test_workflow_agent_singleton())
    asyncio.run(test_workflow_agent_start_stop())
    asyncio.run(test_github_client_mock())
    asyncio.run(test_workflow_agent_ci_trigger())
    asyncio.run(test_workflow_agent_execute_request())
    print("All simple workflow tests passed!")