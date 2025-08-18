import pytest
from unittest.mock import Mock
from fastapi import Request

from openhands.server.user_auth.authelia_user_auth import AutheliaUserAuth
from openhands.server.user_auth.user_auth import AuthType


class TestAutheliaUserAuth:
    @pytest.fixture
    def mock_request(self):
        request = Mock(spec=Request)
        request.headers = {}
        return request

    @pytest.fixture
    def authelia_auth(self, mock_request):
        return AutheliaUserAuth(request=mock_request)

    @pytest.mark.asyncio
    async def test_get_user_id_from_remote_user_header(self, mock_request):
        mock_request.headers = {'Remote-User': 'testuser'}
        auth = AutheliaUserAuth(request=mock_request)
        
        user_id = await auth.get_user_id()
        assert user_id == 'testuser'

    @pytest.mark.asyncio
    async def test_get_user_id_from_x_remote_user_header(self, mock_request):
        mock_request.headers = {'X-Remote-User': 'testuser2'}
        auth = AutheliaUserAuth(request=mock_request)
        
        user_id = await auth.get_user_id()
        assert user_id == 'testuser2'

    @pytest.mark.asyncio
    async def test_get_user_email_from_remote_email_header(self, mock_request):
        mock_request.headers = {'Remote-Email': 'test@example.com'}
        auth = AutheliaUserAuth(request=mock_request)
        
        email = await auth.get_user_email()
        assert email == 'test@example.com'

    @pytest.mark.asyncio
    async def test_get_access_token_from_bearer_header(self, mock_request):
        mock_request.headers = {'Authorization': 'Bearer test-token-123'}
        auth = AutheliaUserAuth(request=mock_request)
        
        token = await auth.get_access_token()
        assert token.get_secret_value() == 'test-token-123'

    @pytest.mark.asyncio
    async def test_get_access_token_from_x_access_token_header(self, mock_request):
        mock_request.headers = {'X-Access-Token': 'test-token-456'}
        auth = AutheliaUserAuth(request=mock_request)
        
        token = await auth.get_access_token()
        assert token.get_secret_value() == 'test-token-456'

    def test_get_auth_type_bearer_when_authorization_header_present(self, mock_request):
        mock_request.headers = {'Authorization': 'Bearer test-token'}
        auth = AutheliaUserAuth(request=mock_request)
        
        auth_type = auth.get_auth_type()
        assert auth_type == AuthType.BEARER

    def test_get_auth_type_cookie_when_no_authorization_header(self, mock_request):
        mock_request.headers = {'Remote-User': 'testuser'}
        auth = AutheliaUserAuth(request=mock_request)
        
        auth_type = auth.get_auth_type()
        assert auth_type == AuthType.COOKIE

    @pytest.mark.asyncio
    async def test_get_instance_class_method(self, mock_request):
        auth = await AutheliaUserAuth.get_instance(mock_request)
        assert isinstance(auth, AutheliaUserAuth)
        assert auth.request == mock_request

    @pytest.mark.asyncio
    async def test_no_user_info_returns_none(self, mock_request):
        # Empty headers should return None for all methods
        auth = AutheliaUserAuth(request=mock_request)
        
        user_id = await auth.get_user_id()
        email = await auth.get_user_email()
        token = await auth.get_access_token()
        
        assert user_id is None
        assert email is None
        assert token is None