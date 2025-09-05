from __future__ import annotations

import os
from dataclasses import dataclass

from fastapi import Request
from pydantic import SecretStr

from openhands.integrations.provider import PROVIDER_TOKEN_TYPE
from openhands.server import shared
from openhands.server.settings import Settings
from openhands.server.user_auth.user_auth import AuthType, UserAuth
from openhands.storage.data_models.user_secrets import UserSecrets
from openhands.storage.secrets.secrets_store import SecretsStore
from openhands.storage.settings.settings_store import SettingsStore


def _first_header(headers: dict[str, str], *candidates: str) -> str | None:
    for name in candidates:
        if name in headers:
            value = headers.get(name)
            if value:
                return value
    return None


@dataclass
class AutheliaForwardAuth(UserAuth):
    """UserAuth implementation for deployments behind an auth proxy like Authelia.

    This implementation trusts identity headers injected by the reverse proxy.
    Configure which headers to read via environment variables if needed.

    Defaults (checked in order):
    - user:  FORWARDED_USER_HEADER or one of ["X-Forwarded-User", "Remote-User", "X-Remote-User"]
    - email: FORWARDED_EMAIL_HEADER or one of ["X-Forwarded-Email", "Remote-Email", "X-Remote-Email"]
    - name:  FORWARDED_NAME_HEADER  or one of ["X-Forwarded-Preferred-Username", "X-Forwarded-Name"]
    """

    request: Request | None = None
    _settings: Settings | None = None
    _settings_store: SettingsStore | None = None
    _secrets_store: SecretsStore | None = None
    _user_secrets: UserSecrets | None = None

    def _lower_headers(self) -> dict[str, str]:
        assert self.request is not None
        return {k: v for k, v in self.request.headers.items()}

    def _get_user_from_headers(self) -> tuple[str | None, str | None, str | None]:
        headers = self._lower_headers()
        # Allow overriding header names via env
        user_hdr = os.getenv('FORWARDED_USER_HEADER')
        email_hdr = os.getenv('FORWARDED_EMAIL_HEADER')
        name_hdr = os.getenv('FORWARDED_NAME_HEADER')

        user = None
        email = None
        name = None

        if user_hdr:
            user = headers.get(user_hdr)
        if email_hdr:
            email = headers.get(email_hdr)
        if name_hdr:
            name = headers.get(name_hdr)

        if not user:
            user = _first_header(
                headers,
                'X-Forwarded-User',
                'Remote-User',
                'X-Remote-User',
                'X-Auth-Request-User',
            )
        if not email:
            email = _first_header(
                headers,
                'X-Forwarded-Email',
                'Remote-Email',
                'X-Remote-Email',
                'X-Auth-Request-Email',
            )
        if not name:
            name = _first_header(
                headers,
                'X-Forwarded-Preferred-Username',
                'X-Forwarded-Name',
                'X-Auth-Request-Preferred-Username',
            )
        return user, email, name

    async def get_user_id(self) -> str | None:
        user, email, _ = self._get_user_from_headers()
        return user or email

    async def get_user_email(self) -> str | None:
        _, email, _ = self._get_user_from_headers()
        return email

    async def get_access_token(self) -> SecretStr | None:
        # In a forward-auth cookie-based setup, application doesn't see tokens
        return None

    async def get_user_settings_store(self) -> SettingsStore:
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
        settings = self._settings
        if settings:
            return settings
        settings_store = await self.get_user_settings_store()
        settings = await settings_store.load()
        if settings:
            settings = settings.merge_with_config_settings()
        self._settings = settings
        return settings

    async def get_secrets_store(self) -> SecretsStore:
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
        user_secrets = self._user_secrets
        if user_secrets:
            return user_secrets
        secrets_store = await self.get_secrets_store()
        user_secrets = await secrets_store.load()
        self._user_secrets = user_secrets
        return user_secrets

    async def get_provider_tokens(self) -> PROVIDER_TOKEN_TYPE | None:
        user_secrets = await self.get_user_secrets()
        if user_secrets is None:
            return None
        return user_secrets.provider_tokens

    def get_auth_type(self) -> AuthType | None:
        return AuthType.COOKIE

    @classmethod
    async def get_instance(cls, request: Request) -> UserAuth:
        return AutheliaForwardAuth(request=request)
