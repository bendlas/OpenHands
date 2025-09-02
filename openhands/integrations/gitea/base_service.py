import base64
from typing import Any

import httpx
from pydantic import SecretStr

from openhands.core.logger import openhands_logger as logger
from openhands.integrations.service_types import (
    AuthenticationError,
    BaseGitService,
    Branch,
    GitService,
    MicroagentContentResponse,
    OwnerType,
    PaginatedBranchesResponse,
    ProviderType,
    Repository,
    RequestMethod,
    ResourceNotFoundError,
    SuggestedTask,
    TaskType,
    UnknownException,
    User,
)
from openhands.server.types import AppMode


class BaseGiteaService(BaseGitService, GitService):
    """Base service class for Gitea-compatible services (Gitea and Forgejo).
    
    This class implements the common functionality for both Gitea and Forgejo,
    which share similar API structures since Forgejo is a Gitea fork.
    """
    
    BASE_URL = 'https://gitea.com/api/v1'  # Default for gitea.com
    token: SecretStr = SecretStr('')
    refresh = False

    def __init__(
        self,
        user_id: str | None = None,
        external_auth_id: str | None = None,
        external_auth_token: SecretStr | None = None,
        token: SecretStr | None = None,
        external_token_manager: bool = False,
        base_domain: str | None = None,
    ):
        self.user_id = user_id
        self.external_token_manager = external_token_manager

        if token:
            self.token = token

        if base_domain:
            # Check if protocol is already included
            if base_domain.startswith(('http://', 'https://')):
                # Use the provided protocol
                self.BASE_URL = f'{base_domain}/api/v1'
            else:
                # Default to https if no protocol specified
                self.BASE_URL = f'https://{base_domain}/api/v1'

        self.external_auth_id = external_auth_id
        self.external_auth_token = external_auth_token

    async def _get_gitea_headers(self) -> dict:
        """Retrieve the Gitea Token to construct the headers."""
        if not self.token:
            latest_token = await self.get_latest_token()
            if latest_token:
                self.token = latest_token

        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'User-Agent': 'OpenHands-Gitea-Integration/1.0',
        }

        if self.token:
            # Gitea supports both 'token' and 'Bearer' authorization
            headers['Authorization'] = f'token {self.token.get_secret_value()}'

        return headers

    def _has_token_expired(self, status_code: int) -> bool:
        return status_code == 401

    async def get_latest_token(self) -> SecretStr | None:
        return self.token

    async def _get_cursorrules_url(self, repository: str) -> str:
        """Get the URL for checking .cursorrules file."""
        return f'{self.BASE_URL}/repos/{repository}/contents/.cursorrules'

    async def _get_microagents_directory_url(
        self, repository: str, microagents_path: str
    ) -> str:
        """Get the URL for checking microagents directory."""
        return f'{self.BASE_URL}/repos/{repository}/contents/{microagents_path}'

    def _get_microagents_directory_params(self, microagents_path: str) -> dict | None:
        """Get parameters for the microagents directory request."""
        return None  # Gitea doesn't need additional parameters

    def _is_valid_microagent_file(self, item: dict) -> bool:
        """Check if an item represents a valid microagent file."""
        return (
            item.get('type') == 'file'
            and item.get('name', '').endswith('.md')
            and not item.get('name', '').startswith('.')
        )

    def _get_file_name_from_item(self, item: dict) -> str:
        """Extract file name from directory item."""
        return item.get('name', '')

    def _get_file_path_from_item(self, item: dict, microagents_path: str) -> str:
        """Extract file path from directory item."""
        return item.get('path', '')

    async def _make_request(
        self,
        url: str,
        params: dict | None = None,
        method: RequestMethod = RequestMethod.GET,
    ) -> tuple[Any, dict]:
        """Make an HTTP request to the Gitea API."""
        headers = await self._get_gitea_headers()

        async with httpx.AsyncClient() as client:
            try:
                if method == RequestMethod.GET:
                    response = await client.get(url, headers=headers, params=params)
                elif method == RequestMethod.POST:
                    response = await client.post(url, headers=headers, params=params)
                
                response.raise_for_status()

                # Parse response headers for pagination info
                response_headers = dict(response.headers)

                # Handle different content types
                if response.headers.get('content-type', '').startswith(
                    'application/json'
                ):
                    return response.json(), response_headers
                else:
                    return response.text, response_headers

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    raise AuthenticationError('Invalid token')
                elif e.response.status_code == 404:
                    raise ResourceNotFoundError('Resource not found')
                raise UnknownException(f'HTTP error: {e}')
            except httpx.HTTPError as e:
                raise UnknownException(f'HTTP error: {e}')

    async def verify_access(self) -> bool:
        """Verify that the token has access to the Gitea API."""
        try:
            await self.get_user()
            return True
        except Exception:
            return False

    async def get_user(self) -> User:
        """Get the authenticated user's information."""
        url = f'{self.BASE_URL}/user'
        response, _ = await self._make_request(url)

        return User(
            id=str(response['id']),
            login=response['login'],
            avatar_url=response['avatar_url'],
            company=response.get('company'),
            name=response.get('full_name'),
            email=response.get('email'),
        )

    async def search_repositories(
        self, query: str, per_page: int, sort: str, order: str, public: bool
    ) -> list[Repository]:
        """Search for repositories."""
        url = f'{self.BASE_URL}/repos/search'
        params = {
            'q': query,
            'limit': min(per_page, 100),  # Gitea's max per page is 100
            'sort': sort,
            'order': order,
        }

        if public:
            params['is_private'] = False

        response, _ = await self._make_request(url, params)
        repositories = []

        # The response structure has 'data' array containing repositories
        for repo in response.get('data', []):
            repositories.append(self._convert_to_repository(repo))

        return repositories

    async def get_all_repositories(
        self, sort: str, app_mode: AppMode
    ) -> list[Repository]:
        """Get all repositories for the authenticated user."""
        url = f'{self.BASE_URL}/user/repos'
        params = {
            'sort': sort,
            'limit': 100,  # Gitea's max per page
        }

        response, _ = await self._make_request(url, params)
        repositories = []

        # Handle both array response and object with data array
        repo_list = response if isinstance(response, list) else response.get('data', [])

        for repo in repo_list:
            repositories.append(self._convert_to_repository(repo))

        return repositories

    async def get_paginated_repos(
        self,
        page: int,
        per_page: int,
        sort: str,
        installation_id: str | None,
        query: str | None = None,
    ) -> list[Repository]:
        """Get a page of repositories."""
        url = f'{self.BASE_URL}/user/repos'
        params = {
            'page': page,
            'limit': min(per_page, 100),  # Gitea's max per page is 100
            'sort': sort,
        }

        response, _ = await self._make_request(url, params)
        repositories = []

        # Handle both array response and object with data array
        repo_list = response if isinstance(response, list) else response.get('data', [])

        for repo in repo_list:
            repositories.append(self._convert_to_repository(repo))

        return repositories

    async def get_suggested_tasks(self) -> list[SuggestedTask]:
        """Get suggested tasks for the authenticated user."""
        # Get user's repositories first
        repositories = await self.get_all_repositories('updated', AppMode.SAAS)
        tasks = []

        # For each repository, check for open issues and PRs
        for repo in repositories[:10]:  # Limit to first 10 repos for performance
            try:
                # Get open issues
                issues_url = f'{self.BASE_URL}/repos/{repo.full_name}/issues'
                issues_params = {'state': 'open', 'type': 'issues', 'limit': 5}
                issues_response, _ = await self._make_request(issues_url, issues_params)

                # Handle both array response and object with data array
                issues_list = (
                    issues_response
                    if isinstance(issues_response, list)
                    else issues_response.get('data', [])
                )

                for issue in issues_list:
                    if issue.get('number') and issue.get('title'):
                        tasks.append(
                            SuggestedTask(
                                git_provider=ProviderType(self.provider),  # Will be set by subclasses
                                task_type=TaskType.OPEN_ISSUE,
                                repo=repo.full_name,
                                issue_number=issue['number'],
                                title=issue['title'],
                            )
                        )

                # Get open PRs
                prs_url = f'{self.BASE_URL}/repos/{repo.full_name}/pulls'
                prs_params = {'state': 'open', 'limit': 5}
                prs_response, _ = await self._make_request(prs_url, prs_params)

                # Handle both array response and object with data array
                prs_list = (
                    prs_response
                    if isinstance(prs_response, list)
                    else prs_response.get('data', [])
                )

                for pr in prs_list:
                    if pr.get('number') and pr.get('title'):
                        tasks.append(
                            SuggestedTask(
                                git_provider=ProviderType(self.provider),  # Will be set by subclasses
                                task_type=TaskType.OPEN_PR,
                                repo=repo.full_name,
                                issue_number=pr['number'],
                                title=pr['title'],
                            )
                        )

            except Exception as e:
                logger.warning(f'Error fetching tasks for {repo.full_name}: {e}')
                continue

        return tasks

    async def get_repository_details_from_repo_name(
        self, repository: str
    ) -> Repository:
        """Get repository details from repository name."""
        url = f'{self.BASE_URL}/repos/{repository}'
        response, _ = await self._make_request(url)
        return self._convert_to_repository(response)

    async def get_branches(self, repository: str) -> list[Branch]:
        """Get branches for a repository."""
        url = f'{self.BASE_URL}/repos/{repository}/branches'
        response, _ = await self._make_request(url)

        branches = []
        for branch in response:
            # Extract commit information safely
            commit = branch.get('commit', {})
            branches.append(
                Branch(
                    name=branch['name'],
                    commit_sha=commit.get('id', ''),
                    protected=branch.get('protected', False),
                    last_push_date=commit.get('timestamp'),
                )
            )

        return branches

    async def get_paginated_branches(
        self, repository: str, page: int = 1, per_page: int = 30
    ) -> PaginatedBranchesResponse:
        """Get branches for a repository with pagination."""
        # Gitea API doesn't support pagination for branches, so we'll get all and slice
        all_branches = await self.get_branches(repository)
        
        # Calculate pagination
        start_index = (page - 1) * per_page
        end_index = start_index + per_page
        paginated_branches = all_branches[start_index:end_index]
        
        return PaginatedBranchesResponse(
            branches=paginated_branches,
            has_next_page=end_index < len(all_branches),
            current_page=page,
            per_page=per_page,
            total_count=len(all_branches),
        )

    async def search_branches(
        self, repository: str, query: str, per_page: int = 30
    ) -> list[Branch]:
        """Search for branches within a repository."""
        all_branches = await self.get_branches(repository)
        
        # Filter branches by query
        matching_branches = [
            branch for branch in all_branches 
            if query.lower() in branch.name.lower()
        ]
        
        # Return only the requested number of branches
        return matching_branches[:per_page]

    async def get_microagent_content(
        self, repository: str, file_path: str
    ) -> MicroagentContentResponse:
        """Get content of a specific microagent file."""
        url = f'{self.BASE_URL}/repos/{repository}/contents/{file_path}'
        response, _ = await self._make_request(url)

        # Decode base64 content
        content = base64.b64decode(response['content']).decode('utf-8')

        # Parse the microagent content
        return self._parse_microagent_content(content, file_path)

    def _convert_to_repository(self, repo_data: dict) -> Repository:
        """Convert Gitea repository data to Repository object."""
        return Repository(
            id=str(repo_data['id']),
            full_name=repo_data['full_name'],
            git_provider=ProviderType(self.provider),  # Will be set by subclasses
            is_public=not repo_data.get('private', False),
            stargazers_count=repo_data.get('stars_count', 0),
            pushed_at=repo_data.get('updated_at'),
            owner_type=OwnerType.ORGANIZATION
            if repo_data.get('owner', {}).get('type') == 'Organization'
            else OwnerType.USER,
            main_branch=repo_data.get('default_branch', 'main'),
        )

    async def get_pr_details(self, repository: str, pr_number: int) -> dict:
        """Get detailed information about a specific pull request.
        
        Args:
            repository: Repository name in format specific to the provider
            pr_number: The pull request/merge request number
            
        Returns:
            Raw API response from the git provider
        """
        url = f'{self.BASE_URL}/repos/{repository}/pulls/{pr_number}'
        response, _ = await self._make_request(url)
        return response

    async def is_pr_open(self, repository: str, pr_number: int) -> bool:
        """Check if a PR is still active (not closed/merged).
        
        Args:
            repository: Repository name in format 'owner/repo'
            pr_number: The PR number to check
            
        Returns:
            True if PR is active (open), False if closed/merged
        """
        try:
            pr_details = await self.get_pr_details(repository, pr_number)
            return pr_details.get('state') == 'open'
        except Exception:
            # If we can't determine the PR status, return True to be safe
            return True