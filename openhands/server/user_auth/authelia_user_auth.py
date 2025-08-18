from dataclasses import dataclass
import json
import base64
from typing import Dict

from fastapi import Request
from pydantic import SecretStr

from openhands.integrations.provider import PROVIDER_TOKEN_TYPE
from openhands.server import shared
from openhands.server.settings import Settings
from openhands.server.user_auth.user_auth import AuthType, UserAuth
from openhands.storage.data_models.user_secrets import UserSecrets
from openhands.storage.secrets.secrets_store import SecretsStore
from openhands.storage.settings.settings_store import SettingsStore


@dataclass
class AutheliaUserAuth(UserAuth):
    """Authelia SSO user authentication mechanism
    
    This implementation extracts user information from Authelia headers
    that are typically set by an authentication proxy.
    
    Common Authelia headers:
    - Remote-User: username
    - Remote-Name: display name
    - Remote-Email: email address
    - Remote-Groups: user groups (comma-separated)
    """

    request: Request
    _settings: Settings | None = None
    _settings_store: SettingsStore | None = None
    _secrets_store: SecretsStore | None = None
    _user_secrets: UserSecrets | None = None

    async def get_user_id(self) -> str | None:
        """Get the unique identifier for the current user from Authelia headers"""
        # Try Remote-User header first (most common)
        user_id = self.request.headers.get('Remote-User')
        if user_id:
            return user_id
        
        # Fallback to X-Remote-User or other common variants
        user_id = self.request.headers.get('X-Remote-User')
        if user_id:
            return user_id
            
        # Try to extract from Authorization header if it's a JWT
        auth_header = self.request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ', 1)[1]
            try:
                # Simple JWT payload extraction (without verification)
                # In production, you should verify the JWT signature
                parts = token.split('.')
                if len(parts) >= 2:
                    payload = parts[1]
                    # Add padding if needed
                    payload += '=' * (4 - len(payload) % 4)
                    decoded = json.loads(base64.b64decode(payload))
                    return decoded.get('sub') or decoded.get('preferred_username') or decoded.get('email')
            except (ValueError, json.JSONDecodeError):
                pass
        
        return None

    async def get_user_email(self) -> str | None:
        """Get the email for the current user from Authelia headers"""
        email = self.request.headers.get('Remote-Email')
        if email:
            return email
            
        email = self.request.headers.get('X-Remote-Email')
        if email:
            return email
            
        # Try to extract from JWT if present
        auth_header = self.request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ', 1)[1]
            try:
                parts = token.split('.')
                if len(parts) >= 2:
                    payload = parts[1]
                    payload += '=' * (4 - len(payload) % 4)
                    decoded = json.loads(base64.b64decode(payload))
                    return decoded.get('email')
            except (ValueError, json.JSONDecodeError):
                pass
        
        return None

    async def get_access_token(self) -> SecretStr | None:
        """Get the access token for the current user"""
        # Check for Bearer token in Authorization header
        auth_header = self.request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ', 1)[1]
            return SecretStr(token)
        
        # Check for access token in custom headers
        token = self.request.headers.get('X-Access-Token')
        if token:
            return SecretStr(token)
            
        return None

    async def get_user_settings_store(self) -> SettingsStore:
        """Get the settings store for the current user"""
        settings_store = self._settings_store
        if settings_store:
            return settings_store
        user_id = await self.get_user_id()
        settings_store = await shared.SettingsStoreImpl.get_instance(
            shared.config, user_id
        )
        if settings_store is None:
            raise ValueError('Failed to get settings store instance')
        self._settings_store = settings_store
        return settings_store

    async def get_user_settings(self) -> Settings | None:
        """Get the user settings for the current user"""
        settings = self._settings
        if settings:
            return settings
        settings_store = await self.get_user_settings_store()
        settings = await settings_store.load()

        # Merge config.toml settings with stored settings
        if settings:
            settings = settings.merge_with_config_settings()

        self._settings = settings
        return settings

    async def get_secrets_store(self) -> SecretsStore:
        """Get secrets store"""
        secrets_store = self._secrets_store
        if secrets_store:
            return secrets_store
        user_id = await self.get_user_id()
        secret_store = await shared.SecretsStoreImpl.get_instance(
            shared.config, user_id
        )
        if secret_store is None:
            raise ValueError('Failed to get secrets store instance')
        self._secrets_store = secret_store
        return secret_store

    async def get_user_secrets(self) -> UserSecrets | None:
        """Get the user's secrets"""
        user_secrets = self._user_secrets
        if user_secrets:
            return user_secrets
        secrets_store = await self.get_secrets_store()
        user_secrets = await secrets_store.load()
        self._user_secrets = user_secrets
        return user_secrets

    async def get_provider_tokens(self) -> PROVIDER_TOKEN_TYPE | None:
        """Get the provider tokens for the current user"""
        user_secrets = await self.get_user_secrets()
        if user_secrets is None:
            return None
        return user_secrets.provider_tokens

    def get_auth_type(self) -> AuthType | None:
        """Return the authentication type"""
        # Check if we have a Bearer token
        auth_header = self.request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            return AuthType.BEARER
        
        # Otherwise assume header-based authentication
        return AuthType.COOKIE

    @classmethod
    async def get_instance(cls, request: Request) -> UserAuth:
        """Get an instance of AutheliaUserAuth from the request"""
        user_auth = AutheliaUserAuth(request=request)
        return user_auth