import pytest
from unittest.mock import AsyncMock, Mock, patch
from pydantic import SecretStr

from openhands.integrations.gitea.gitea_service import GiteaService
from openhands.integrations.service_types import ProviderType, User, Repository, OwnerType


class TestGiteaService:
    @pytest.fixture
    def gitea_service(self):
        return GiteaService(
            token=SecretStr('test-token'),
            base_domain='git.example.com'
        )

    def test_init_with_custom_domain(self):
        service = GiteaService(base_domain='git.example.com')
        assert service.BASE_URL == 'https://git.example.com/api/v1'

    def test_init_with_default_domain(self):
        service = GiteaService()
        assert service.BASE_URL == 'https://gitea.com/api/v1'

    def test_provider_property(self, gitea_service):
        assert gitea_service.provider == ProviderType.GITEA.value

    @pytest.mark.asyncio
    async def test_get_gitea_headers(self, gitea_service):
        headers = await gitea_service._get_gitea_headers()
        assert headers['Authorization'] == 'token test-token'
        assert headers['Accept'] == 'application/json'
        assert headers['Content-Type'] == 'application/json'

    @pytest.mark.asyncio
    async def test_get_gitea_headers_no_token(self):
        service = GiteaService()
        with pytest.raises(ValueError, match='Gitea token is required'):
            await service._get_gitea_headers()

    @pytest.mark.asyncio
    async def test_get_user(self, gitea_service):
        mock_response = {
            'id': 123,
            'login': 'testuser',
            'avatar_url': 'https://example.com/avatar.png',
            'company': 'Test Company',
            'full_name': 'Test User',
            'email': 'test@example.com'
        }
        
        with patch.object(gitea_service, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = (mock_response, {})
            
            user = await gitea_service.get_user()
            
            assert isinstance(user, User)
            assert user.id == '123'
            assert user.login == 'testuser'
            assert user.avatar_url == 'https://example.com/avatar.png'
            assert user.company == 'Test Company'
            assert user.name == 'Test User'
            assert user.email == 'test@example.com'
            
            mock_request.assert_called_once_with('https://git.example.com/api/v1/user')

    @pytest.mark.asyncio
    async def test_verify_access(self, gitea_service):
        with patch.object(gitea_service, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = ({}, {})
            
            result = await gitea_service.verify_access()
            
            assert result is True
            mock_request.assert_called_once_with('https://git.example.com/api/v1/user')

    @pytest.mark.asyncio
    async def test_get_repository_details_from_repo_name(self, gitea_service):
        mock_response = {
            'id': 123,
            'full_name': 'testowner/test-repo',
            'stargazers_count': 42,
            'owner': {'login': 'testowner', 'type': 'User'},
            'private': False,
            'default_branch': 'main'
        }
        
        with patch.object(gitea_service, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = (mock_response, {})
            
            repo = await gitea_service.get_repository_details_from_repo_name('testowner/test-repo')
            
            assert isinstance(repo, Repository)
            assert repo.id == '123'
            assert repo.full_name == 'testowner/test-repo'
            assert repo.git_provider == ProviderType.GITEA
            assert repo.is_public is True
            assert repo.stargazers_count == 42
            assert repo.owner_type == OwnerType.USER
            assert repo.main_branch == 'main'
            
            mock_request.assert_called_once_with(
                'https://git.example.com/api/v1/repos/testowner/test-repo'
            )

    @pytest.mark.asyncio
    async def test_get_repository_details_invalid_format(self, gitea_service):
        with pytest.raises(ValueError, match='Invalid repository format'):
            await gitea_service.get_repository_details_from_repo_name('invalid-repo-name')

    @pytest.mark.asyncio
    async def test_get_branches(self, gitea_service):
        mock_response = [
            {
                'name': 'main',
                'commit': {'id': 'abc123'},
                'protected': True
            },
            {
                'name': 'develop',
                'commit': {'id': 'def456'},
                'protected': False
            }
        ]
        
        with patch.object(gitea_service, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = (mock_response, {})
            
            branches = await gitea_service.get_branches('testowner/test-repo')
            
            assert len(branches) == 2
            assert branches[0].name == 'main'
            assert branches[0].commit_sha == 'abc123'
            assert branches[0].protected is True
            assert branches[1].name == 'develop'
            assert branches[1].commit_sha == 'def456'
            assert branches[1].protected is False
            
            mock_request.assert_called_once_with(
                'https://git.example.com/api/v1/repos/testowner/test-repo/branches'
            )

    @pytest.mark.asyncio
    async def test_get_installations(self, gitea_service):
        # Gitea doesn't have app installations like GitHub
        installations = await gitea_service.get_installations()
        assert installations == []

    def test_has_token_expired(self, gitea_service):
        assert gitea_service._has_token_expired(401) is True
        assert gitea_service._has_token_expired(200) is False
        assert gitea_service._has_token_expired(404) is False

    @pytest.mark.asyncio
    async def test_get_latest_token(self, gitea_service):
        token = await gitea_service.get_latest_token()
        assert token == gitea_service.token