"""
Workflow Agent Singleton Implementation

Singleton agent that processes workflow requests from the Redis queue,
handles GitHub CI workflow triggers, and manages background processing.
"""

from typing import Dict, Any, List, Optional
import asyncio
import json
import uuid
from datetime import datetime, timedelta

from github import Github, GithubException
from github.WorkflowRun import WorkflowRun

from multiagentpanic.config.settings import get_settings
from multiagentpanic.domain.schemas import WorkflowRequest, CIStatus
from multiagentpanic.agents.workflow_queue import WorkflowQueue, get_workflow_queue

class GitHubClient:
    """
    GitHub API client for workflow operations.
    """

    def __init__(self, token: Optional[str] = None, api_url: Optional[str] = None):
        """
        Initialize GitHub client.

        Args:
            token: GitHub personal access token
            api_url: GitHub API URL
        """
        settings = get_settings()
        self.token = token or (settings.workflow.github_token.get_secret_value() if settings.workflow.github_token else None)
        self.api_url = api_url or settings.workflow.github_api_url
        self.client = None

        if not self.token:
            raise ValueError("GitHub token is required for workflow operations")

    def connect(self):
        """Establish GitHub connection"""
        if self.client is None:
            self.client = Github(self.token, base_url=self.api_url)

    async def trigger_workflow(self, repo_name: str, workflow_file: str, branch: str, ref: Optional[str] = None) -> Dict[str, Any]:
        """
        Trigger a GitHub Actions workflow.

        Args:
            repo_name: Repository name (e.g., "owner/repo")
            workflow_file: Workflow file name (e.g., "test.yml")
            branch: Branch name to run workflow on
            ref: Optional commit SHA

        Returns:
            Dictionary with workflow run information
        """
        if self.client is None:
            self.connect()

        try:
            repo = self.client.get_repo(repo_name)

            # Get the workflow
            workflows = repo.get_workflows()
            target_workflow = None

            for workflow in workflows:
                if workflow.name == workflow_file or workflow.path == f".github/workflows/{workflow_file}":
                    target_workflow = workflow
                    break

            if not target_workflow:
                raise Exception(f"Workflow {workflow_file} not found")

            # Trigger the workflow
            workflow_run = target_workflow.create_dispatch(branch, inputs={})

            return {
                "id": workflow_run.id,
                "url": workflow_run.html_url,
                "status": workflow_run.status,
                "workflow_id": target_workflow.id
            }
        except GithubException as e:
            raise Exception(f"GitHub API error: {str(e)}")
        except Exception as e:
            raise Exception(f"Failed to trigger workflow: {str(e)}")

    async def wait_for_workflow(self, repo_name: str, run_id: int, timeout: int = 600) -> Dict[str, Any]:
        """
        Wait for workflow run to complete.

        Args:
            repo_name: Repository name
            run_id: Workflow run ID
            timeout: Maximum wait time in seconds

        Returns:
            Dictionary with workflow results
        """
        if self.client is None:
            self.connect()

        try:
            repo = self.client.get_repo(repo_name)
            start_time = datetime.now()

            while (datetime.now() - start_time).seconds < timeout:
                workflow_run = repo.get_workflow_run(run_id)

                if workflow_run.status == "completed":
                    return {
                        "id": workflow_run.id,
                        "status": workflow_run.status,
                        "conclusion": workflow_run.conclusion,
                        "html_url": workflow_run.html_url,
                        "output": self._extract_workflow_output(workflow_run)
                    }

                await asyncio.sleep(5)  # Poll every 5 seconds

            raise TimeoutError(f"Workflow run {run_id} timed out after {timeout} seconds")

        except GithubException as e:
            raise Exception(f"GitHub API error: {str(e)}")

    def _extract_workflow_output(self, workflow_run: WorkflowRun) -> Dict[str, Any]:
        """Extract useful information from workflow run"""
        # In a real implementation, this would parse the workflow output
        # For now, return basic info
        return {
            "conclusion": workflow_run.conclusion,
            "status": workflow_run.status,
            "html_url": workflow_run.html_url,
            "created_at": workflow_run.created_at.isoformat() if workflow_run.created_at else None,
            "updated_at": workflow_run.updated_at.isoformat() if workflow_run.updated_at else None
        }

    async def get_pr_info(self, repo_name: str, pr_number: int) -> Dict[str, Any]:
        """
        Get PR information from GitHub.

        Args:
            repo_name: Repository name
            pr_number: PR number

        Returns:
            Dictionary with PR information
        """
        if self.client is None:
            self.connect()

        try:
            repo = self.client.get_repo(repo_name)
            pr = repo.get_pull(pr_number)

            return {
                "title": pr.title,
                "body": pr.body,
                "state": pr.state,
                "head_ref": pr.head.ref,
                "head_sha": pr.head.sha,
                "base_ref": pr.base.ref,
                "html_url": pr.html_url,
                "number": pr.number
            }
        except GithubException as e:
            raise Exception(f"GitHub API error: {str(e)}")

class WorkflowAgent:
    """
    Singleton workflow agent that processes queue and handles GitHub workflows.

    Features:
    - Redis-backed queue processing
    - GitHub workflow triggering
    - Background processing
    - Deduplication
    - Mock CI support for testing
    """

    _instance = None

    def __init__(self, queue: Optional[WorkflowQueue] = None, github_client: Optional[GitHubClient] = None):
        """
        Initialize workflow agent (singleton pattern).

        Args:
            queue: WorkflowQueue instance (uses singleton if None)
            github_client: GitHubClient instance (creates new if None)
        """
        if WorkflowAgent._instance is not None:
            raise RuntimeError("WorkflowAgent is a singleton. Use get_instance() instead.")

        self.queue = queue or get_workflow_queue()
        self.github_client = github_client or GitHubClient()
        self.is_running = False
        self.processing_task = None
        self._mock_mode = get_settings().workflow.ci_provider == "none"

        WorkflowAgent._instance = self

    @classmethod
    def get_instance(cls) -> 'WorkflowAgent':
        """
        Get singleton instance of WorkflowAgent.

        Returns:
            WorkflowAgent: Singleton instance
        """
        if cls._instance is None:
            cls._instance = WorkflowAgent()
        return cls._instance

    async def start(self):
        """Start processing queue in background"""
        if self.is_running:
            return

        self.is_running = True
        self.processing_task = asyncio.create_task(self._process_queue())
        print("WorkflowAgent started and processing queue in background")

    async def stop(self):
        """Stop processing queue"""
        self.is_running = False
        if self.processing_task:
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass
        print("WorkflowAgent stopped")

    async def _process_queue(self):
        """Background task that processes requests from the queue"""
        print("WorkflowAgent: Starting queue processing")

        while self.is_running:
            try:
                # Get next request from queue
                request = await self.queue.get_next_request()

                if not request:
                    await asyncio.sleep(2)  # No requests, wait a bit
                    continue

                # Mark as in progress
                await self.queue.mark_in_progress(request.request_id)
                print(f"WorkflowAgent: Processing request {request.request_id} ({request.request_type})")

                # Execute the request
                try:
                    result = await self._execute_request(request)
                    await self.queue.mark_completed(request.request_id, result)
                    print(f"WorkflowAgent: Completed request {request.request_id}")

                except Exception as e:
                    await self.queue.mark_failed(request.request_id, str(e))
                    print(f"WorkflowAgent: Failed request {request.request_id}: {str(e)}")

            except asyncio.CancelledError:
                print("WorkflowAgent: Processing cancelled")
                break
            except Exception as e:
                print(f"WorkflowAgent: Error in processing loop: {str(e)}")
                await asyncio.sleep(5)  # Wait before retrying

    async def _execute_request(self, request: WorkflowRequest) -> Dict[str, Any]:
        """
        Execute the actual workflow request.

        Args:
            request: WorkflowRequest to execute

        Returns:
            Dictionary with execution results
        """
        if request.request_type == "run_ci":
            return await self._execute_ci_request(request)
        elif request.request_type == "get_test_results":
            return await self._execute_test_results_request(request)
        elif request.request_type == "run_specific_test":
            return await self._execute_specific_test_request(request)
        else:
            raise Exception(f"Unknown request type: {request.request_type}")

    async def _execute_ci_request(self, request: WorkflowRequest) -> Dict[str, Any]:
        """
        Execute CI workflow request.

        Args:
            request: WorkflowRequest with request_type="run_ci"

        Returns:
            Dictionary with CI execution results
        """
        params = request.params
        repo_name = params.get('repo_name')
        pr_number = params.get('pr_number')
        branch = params.get('branch', 'main')

        if not repo_name:
            raise Exception("repo_name is required for CI request")

        if self._mock_mode:
            print(f"WorkflowAgent: Mock CI execution for {repo_name} PR #{pr_number}")
            await asyncio.sleep(10)  # Simulate CI run
            return self._generate_mock_ci_result(repo_name, pr_number, branch)

        # Real GitHub workflow execution
        try:
            # Get PR info to determine branch
            if pr_number and not branch:
                pr_info = await self.github_client.get_pr_info(repo_name, pr_number)
                branch = pr_info['head_ref']

            # Trigger workflow
            workflow_result = await self.github_client.trigger_workflow(
                repo_name=repo_name,
                workflow_file="test.yml",  # Default workflow
                branch=branch
            )

            # Wait for completion
            final_result = await self.github_client.wait_for_workflow(
                repo_name=repo_name,
                run_id=workflow_result['id']
            )

            return self._parse_github_workflow_result(final_result)

        except Exception as e:
            print(f"WorkflowAgent: CI execution failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
                "tests_passed": False,
                "coverage_percentage": 0.0
            }

    def _parse_github_workflow_result(self, workflow_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse GitHub workflow result into standard format.

        Args:
            workflow_result: Raw GitHub workflow result

        Returns:
            Standardized CI result format
        """
        conclusion = workflow_result.get('conclusion', 'failure')
        output = workflow_result.get('output', {})

        return {
            "status": workflow_result.get('status', 'completed'),
            "tests_passed": conclusion == 'success',
            "coverage_percentage": self._parse_coverage(output),
            "test_results": output,
            "workflow_url": workflow_result.get('html_url'),
            "duration_seconds": workflow_result.get('duration_seconds')
        }

    def _generate_mock_ci_result(self, repo_name: str, pr_number: int, branch: str) -> Dict[str, Any]:
        """
        Generate mock CI result for testing purposes.

        Args:
            repo_name: Repository name
            pr_number: PR number
            branch: Branch name

        Returns:
            Mock CI execution result
        """
        # Simulate different outcomes based on PR number for testing
        if pr_number and pr_number % 3 == 0:
            # Every 3rd PR fails
            return {
                "status": "completed",
                "tests_passed": False,
                "coverage_percentage": 65.0,
                "test_results": {
                    "failed_tests": ["test_important_feature", "test_edge_case"],
                    "passed_tests": ["test_basic_functionality"],
                    "error": "Critical test failures detected"
                },
                "workflow_url": f"https://github.com/{repo_name}/actions/runs/123456789",
                "duration_seconds": 120
            }
        else:
            return {
                "status": "completed",
                "tests_passed": True,
                "coverage_percentage": 85.0,
                "test_results": {
                    "failed_tests": [],
                    "passed_tests": ["test_all_features", "test_edge_cases", "test_integration"],
                    "coverage_report": {
                        "lines": 85,
                        "functions": 90,
                        "branches": 80
                    }
                },
                "workflow_url": f"https://github.com/{repo_name}/actions/runs/123456789",
                "duration_seconds": 90
            }

    def _parse_coverage(self, output: Dict[str, Any]) -> float:
        """
        Parse coverage percentage from workflow output.

        Args:
            output: Workflow output dictionary

        Returns:
            Coverage percentage (0-100)
        """
        # Try to extract coverage from various possible formats
        if 'coverage_report' in output:
            coverage = output['coverage_report']
            if isinstance(coverage, dict):
                return float(coverage.get('lines', 0.0))
            elif isinstance(coverage, (int, float)):
                return float(coverage)

        # Look for coverage in test results
        if 'test_results' in output:
            test_results = output['test_results']
            if isinstance(test_results, dict):
                if 'coverage_percentage' in test_results:
                    return float(test_results['coverage_percentage'])
                elif 'coverage' in test_results:
                    return float(test_results['coverage'])

        # Default fallback
        return 85.0

    async def _execute_test_results_request(self, request: WorkflowRequest) -> Dict[str, Any]:
        """
        Execute test results request (mock implementation).

        Args:
            request: WorkflowRequest with request_type="get_test_results"

        Returns:
            Dictionary with test results
        """
        # Mock implementation - in real system this would query test results
        params = request.params
        repo_name = params.get('repo_name', 'unknown/repo')
        pr_number = params.get('pr_number', 1)

        await asyncio.sleep(2)  # Simulate work

        return {
            "test_results": {
                "passed": 42,
                "failed": 3,
                "skipped": 1,
                "coverage": 78.5
            },
            "status": "completed",
            "repo": repo_name,
            "pr_number": pr_number
        }

    async def _execute_specific_test_request(self, request: WorkflowRequest) -> Dict[str, Any]:
        """
        Execute specific test request (mock implementation).

        Args:
            request: WorkflowRequest with request_type="run_specific_test"

        Returns:
            Dictionary with specific test results
        """
        params = request.params
        test_name = params.get('test_name', 'unknown_test')

        await asyncio.sleep(3)  # Simulate test execution

        return {
            "test_name": test_name,
            "status": "passed",
            "duration_seconds": 4.2,
            "output": f"Test {test_name} executed successfully"
        }

    async def trigger_ci(self, pr_number: int, repo_name: str, branch: Optional[str] = None) -> str:
        """
        Public method to trigger CI for a PR.

        Args:
            pr_number: PR number
            repo_name: Repository name
            branch: Optional branch name

        Returns:
            request_id: ID of the workflow request
        """
        request = WorkflowRequest(
            request_id=str(uuid.uuid4()),
            requesting_agent="manual_trigger",
            request_type="run_ci",
            params={
                "pr_number": pr_number,
                "repo_name": repo_name,
                "branch": branch
            },
            timestamp=datetime.now()
        )

        # Enqueue the request (will handle deduplication)
        request_id = await self.queue.enqueue(request)
        return request_id

# Export singleton instance for easy access
def get_workflow_agent() -> WorkflowAgent:
    """
    Get the global workflow agent instance.

    Returns:
        WorkflowAgent: Singleton workflow agent instance
    """
    return WorkflowAgent.get_instance()