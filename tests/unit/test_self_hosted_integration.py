import pytest
from unittest.mock import Mock, patch
from fastapi import Request
from pydantic import SecretStr

from openhands.integrations.service_types import ProviderType
from openhands.integrations.provider import ProviderHandler, ProviderToken
from openhands.server.user_auth.authelia_user_auth import AutheliaUserAuth
from types import MappingProxyType


class TestSelfHostedIntegration:
    """Integration tests for self-hosted setup with Authelia + Gitea"""

    @pytest.mark.asyncio
    async def test_authelia_with_gitea_provider_integration(self):
        """Test that Authelia auth can work with Gitea provider"""
        # Mock request with Authelia headers
        mock_request = Mock(spec=Request)
        mock_request.headers = {
            'Remote-User': 'testuser',
            'Remote-Email': 'test@example.com',
            'Authorization': 'Bearer gitea-token-123'
        }
        
        # Create Authelia auth instance
        auth = AutheliaUserAuth(request=mock_request)
        
        # Test user info extraction
        user_id = await auth.get_user_id()
        email = await auth.get_user_email()
        token = await auth.get_access_token()
        
        assert user_id == 'testuser'
        assert email == 'test@example.com'
        assert token.get_secret_value() == 'gitea-token-123'

    def test_gitea_provider_in_handler(self):
        """Test that Gitea provider is properly registered in ProviderHandler"""
        # Create provider tokens with Gitea
        provider_tokens = MappingProxyType({
            ProviderType.GITEA: ProviderToken(token=SecretStr('gitea-token'))
        })
        
        # Create provider handler
        handler = ProviderHandler(provider_tokens)
        
        # Verify Gitea is in the service class map
        assert ProviderType.GITEA in handler.service_class_map
        assert handler.service_class_map[ProviderType.GITEA].__name__ == 'GiteaService'

    def test_all_provider_types_available(self):
        """Test that all provider types are available including Gitea"""
        expected_providers = ['github', 'gitlab', 'bitbucket', 'gitea', 'enterprise_sso']
        
        for provider_name in expected_providers:
            # Verify enum exists
            provider = ProviderType(provider_name)
            assert provider.value == provider_name

    @pytest.mark.asyncio
    async def test_gitea_service_with_custom_domain(self):
        """Test Gitea service with custom domain (self-hosted scenario)"""
        from openhands.integrations.gitea.gitea_service import GiteaService
        
        # Create service with custom domain
        service = GiteaService(
            token=SecretStr('test-token'),
            base_domain='git.mycompany.com'
        )
        
        assert service.BASE_URL == 'https://git.mycompany.com/api/v1'
        assert service.provider == ProviderType.GITEA.value

    def test_frontend_login_method_includes_gitea(self):
        """Test that frontend LoginMethod enum includes Gitea"""
        # This would be tested in TypeScript in the frontend test suite
        # Here we just verify our additions were made to the relevant files
        
        # Read the file to check Gitea was added
        with open('/home/runner/work/OpenHands/OpenHands/frontend/src/utils/local-storage.ts', 'r') as f:
            content = f.read()
            assert 'GITEA = "gitea"' in content

    @pytest.mark.asyncio 
    async def test_suggested_task_provider_terms_gitea(self):
        """Test that Gitea provider terms are available for suggested tasks"""
        from openhands.integrations.service_types import SuggestedTask, TaskType, ProviderType
        
        task = SuggestedTask(
            git_provider=ProviderType.GITEA,
            task_type=TaskType.OPEN_ISSUE,
            repo='test/repo',
            issue_number=1,
            title='Test Issue'
        )
        
        terms = task.get_provider_terms()
        
        assert terms['requestType'] == 'Pull Request'
        assert terms['requestTypeShort'] == 'PR'
        assert terms['apiName'] == 'Gitea API'
        assert terms['tokenEnvVar'] == 'GITEA_TOKEN'
        assert terms['ciSystem'] == 'Gitea Actions'
        assert terms['ciProvider'] == 'Gitea'
        assert terms['requestVerb'] == 'pull request'