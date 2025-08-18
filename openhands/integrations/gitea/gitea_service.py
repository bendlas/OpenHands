import base64
import json
import os
from datetime import datetime
from typing import Any

import httpx
from pydantic import SecretStr

from openhands.core.logger import openhands_logger as logger
from openhands.integrations.service_types import (
    BaseGitService,
    Branch,
    GitService,
    InstallationsService,
    OwnerType,
    ProviderType,
    Repository,
    RequestMethod,
    SuggestedTask,
    TaskType,
    UnknownException,
    User,
)
from openhands.microagent.types import MicroagentContentResponse
from openhands.server.types import AppMode
from openhands.utils.import_utils import get_impl


class GiteaService(BaseGitService, GitService, InstallationsService):
    """Implementation of GitService for Gitea/Forgejo integration.
    
    Gitea and Forgejo use GitHub-compatible APIs, so this implementation
    is largely based on the GitHub service with Gitea-specific modifications.
    """

    BASE_URL = 'https://gitea.com/api/v1'  # Default Gitea URL, should be configurable
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

        # Support custom Gitea instances
        if base_domain and base_domain != 'gitea.com':
            self.BASE_URL = f'https://{base_domain}/api/v1'

        self.external_auth_id = external_auth_id
        self.external_auth_token = external_auth_token

    @property
    def provider(self) -> str:
        return ProviderType.GITEA.value

    async def _get_gitea_headers(self) -> dict:
        """Retrieve the Gitea Token to construct the headers."""
        if self.external_token_manager:
            if self.external_auth_token:
                token = self.external_auth_token.get_secret_value()
            else:
                raise ValueError('External auth token is required when external_token_manager is True')
        else:
            token = self.token.get_secret_value()

        if not token:
            raise ValueError('Gitea token is required')

        return {
            'Authorization': f'token {token}',  # Gitea uses 'token' prefix like GitHub
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }

    def _has_token_expired(self, status_code: int) -> bool:
        """Check if the token has expired based on response status code."""
        return status_code == 401

    async def get_latest_token(self) -> SecretStr | None:
        """Get the latest token (for refresh scenarios)."""
        # For now, return the current token
        # In a real implementation, this might refresh the token
        return self.token

    async def get_user(self) -> User:
        """Get the current authenticated user information."""
        url = f'{self.BASE_URL}/user'
        response, _ = await self._make_request(url)

        return User(
            id=str(response.get('id', '')),
            login=response.get('login'),
            avatar_url=response.get('avatar_url'),
            company=response.get('company'),
            name=response.get('full_name'),  # Gitea uses 'full_name' instead of 'name'
            email=response.get('email'),
        )

    async def verify_access(self) -> bool:
        """Verify if the token is valid by making a simple request."""
        url = f'{self.BASE_URL}/user'
        await self._make_request(url)
        return True

    async def get_repository_details_from_repo_name(self, repository: str) -> Repository:
        """Get repository details from repository name."""
        if '/' not in repository:
            raise ValueError(f'Invalid repository format: {repository}. Expected: owner/repo')
        
        owner, repo = repository.split('/', 1)
        url = f'{self.BASE_URL}/repos/{owner}/{repo}'
        response, _ = await self._make_request(url)

        return Repository(
            id=str(response.get('id', '')),
            full_name=response.get('full_name'),
            git_provider=ProviderType.GITEA,
            is_public=not response.get('private', False),
            stargazers_count=response.get('stargazers_count'),
            owner_type=OwnerType.ORGANIZATION if response.get('owner', {}).get('type') == 'Organization' else OwnerType.USER,
            main_branch=response.get('default_branch'),
        )

    async def get_branches(self, repository: str) -> list[Branch]:
        """Get branches for a repository."""
        if '/' not in repository:
            raise ValueError(f'Invalid repository format: {repository}. Expected: owner/repo')
        
        owner, repo = repository.split('/', 1)
        url = f'{self.BASE_URL}/repos/{owner}/{repo}/branches'
        response, _ = await self._make_request(url)

        branches = []
        for branch_data in response:
            branches.append(Branch(
                name=branch_data.get('name'),
                commit_sha=branch_data.get('commit', {}).get('id'),
                protected=branch_data.get('protected', False),
            ))

        return branches

    async def get_installations(self) -> list[str]:
        """Get installations (for app-based authentication)."""
        # Gitea doesn't have the same app installation concept as GitHub
        # Return empty list for now
        return []

    async def _get_cursorrules_url(self, repository: str) -> str:
        """Get the URL for checking .cursorrules file."""
        return f'{self.BASE_URL}/repos/{repository}/contents/.cursorrules'

    async def _get_microagents_directory_url(
        self, repository: str, microagents_path: str
    ) -> str:
        """Get the URL for checking microagents directory."""
        return f'{self.BASE_URL}/repos/{repository}/contents/{microagents_path}'

    def _is_valid_microagent_file(self, item: dict) -> bool:
        """Check if an item represents a valid microagent file."""
        return (
            item['type'] == 'file'
            and item['name'].endswith('.md')
            and item['name'] != 'README.md'
        )

    def _get_file_name_from_item(self, item: dict) -> str:
        """Extract file name from directory item."""
        return item['name']

    def _get_file_path_from_item(self, item: dict, microagents_path: str) -> str:
        """Extract file path from directory item."""
        return f'{microagents_path}/{item["name"]}'

    def _get_microagents_directory_params(self, microagents_path: str) -> dict | None:
        """Get parameters for the microagents directory request. Return None if no parameters needed."""
        return None

    async def _make_request(
        self,
        url: str,
        params: dict | None = None,
        method: RequestMethod = RequestMethod.GET,
    ) -> tuple[Any, dict]:
        """Make an HTTP request to the Gitea API."""
        try:
            async with httpx.AsyncClient() as client:
                gitea_headers = await self._get_gitea_headers()

                # Make initial request
                response = await self.execute_request(
                    client=client,
                    url=url,
                    headers=gitea_headers,
                    params=params,
                    method=method,
                )

                # Handle token refresh if needed
                if self.refresh and self._has_token_expired(response.status_code):
                    await self.get_latest_token()
                    gitea_headers = await self._get_gitea_headers()
                    response = await self.execute_request(
                        client=client,
                        url=url,
                        headers=gitea_headers,
                        params=params,
                        method=method,
                    )

                response.raise_for_status()
                headers = {}
                if 'Link' in response.headers:
                    headers['Link'] = response.headers['Link']

                return response.json(), headers

        except httpx.HTTPStatusError as e:
            raise self.handle_http_status_error(e)
        except httpx.HTTPError as e:
            raise self.handle_http_error(e)

    # Additional methods can be implemented as needed
    # For microagents, suggested tasks, etc.


# Create alias for compatibility with Forgejo
ForgejoService = GiteaService


# For backward compatibility and import consistency
GiteaServiceImpl = GiteaService