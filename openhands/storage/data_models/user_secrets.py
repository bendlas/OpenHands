from types import MappingProxyType
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SerializationInfo,
    field_serializer,
    model_validator,
)
from pydantic.json import pydantic_encoder

from openhands.events.stream import EventStream
from openhands.integrations.provider import (
    CUSTOM_SECRETS_TYPE,
    CUSTOM_SECRETS_TYPE_WITH_JSON_SCHEMA,
    INTEGRATIONS_TYPE_WITH_JSON_SCHEMA,
    PROVIDER_TOKEN_TYPE,
    PROVIDER_TOKEN_TYPE_WITH_JSON_SCHEMA,
    CustomSecret,
    Integration,
    ProviderToken,
)
from openhands.integrations.service_types import ProviderType


class UserSecrets(BaseModel):
    provider_tokens: PROVIDER_TOKEN_TYPE_WITH_JSON_SCHEMA = Field(
        default_factory=lambda: MappingProxyType({})
    )

    custom_secrets: CUSTOM_SECRETS_TYPE_WITH_JSON_SCHEMA = Field(
        default_factory=lambda: MappingProxyType({})
    )

    # New field for dynamic integrations
    integrations: INTEGRATIONS_TYPE_WITH_JSON_SCHEMA = Field(
        default_factory=list,
        description="List of configured git provider integrations"
    )

    model_config = ConfigDict(
        frozen=True,
        validate_assignment=True,
        arbitrary_types_allowed=True,
    )

    @field_serializer('provider_tokens')
    def provider_tokens_serializer(
        self, provider_tokens: PROVIDER_TOKEN_TYPE, info: SerializationInfo
    ) -> dict[str, dict[str, str | Any]]:
        tokens = {}
        expose_secrets = info.context and info.context.get('expose_secrets', False)

        for token_type, provider_token in provider_tokens.items():
            if not provider_token or not provider_token.token:
                continue

            token_type_str = (
                token_type.value
                if isinstance(token_type, ProviderType)
                else str(token_type)
            )

            token = None
            if provider_token.token:
                token = (
                    provider_token.token.get_secret_value()
                    if expose_secrets
                    else pydantic_encoder(provider_token.token)
                )

            tokens[token_type_str] = {
                'token': token,
                'host': provider_token.host,
                'user_id': provider_token.user_id,
            }

        return tokens

    @field_serializer('custom_secrets')
    def custom_secrets_serializer(
        self, custom_secrets: CUSTOM_SECRETS_TYPE, info: SerializationInfo
    ):
        secrets = {}
        expose_secrets = info.context and info.context.get('expose_secrets', False)

        if custom_secrets:
            for secret_name, secret_value in custom_secrets.items():
                secrets[secret_name] = {
                    'secret': secret_value.secret.get_secret_value()
                    if expose_secrets
                    else pydantic_encoder(secret_value.secret),
                    'description': secret_value.description,
                }

        return secrets

    @field_serializer('integrations')
    def integrations_serializer(
        self, integrations: list[Integration], info: SerializationInfo
    ) -> list[dict[str, Any]]:
        expose_secrets = info.context and info.context.get('expose_secrets', False)
        serialized_integrations = []
        
        for integration in integrations:
            integration_data = {
                'id': integration.id,
                'provider_type': integration.provider_type,
                'name': integration.name,
                'host': integration.host,
                'user_id': integration.user_id,
            }
            
            if integration.token:
                integration_data['token'] = (
                    integration.token.get_secret_value()
                    if expose_secrets
                    else pydantic_encoder(integration.token)
                )
            else:
                integration_data['token'] = None
                
            serialized_integrations.append(integration_data)
        
        return serialized_integrations

    @model_validator(mode='before')
    @classmethod
    def convert_dict_to_mappingproxy(
        cls, data: dict[str, dict[str, Any] | MappingProxyType] | PROVIDER_TOKEN_TYPE
    ) -> dict[str, MappingProxyType | None]:
        """Custom deserializer to convert dictionary into MappingProxyType"""
        if not isinstance(data, dict):
            raise ValueError('UserSecrets must be initialized with a dictionary')

        new_data: dict[str, MappingProxyType | None] = {}

        if 'provider_tokens' in data:
            tokens = data['provider_tokens']
            if isinstance(
                tokens, dict
            ):  # Ensure conversion happens only for dict inputs
                converted_tokens = {}
                for key, value in tokens.items():
                    try:
                        provider_type = (
                            ProviderType(key) if isinstance(key, str) else key
                        )
                        converted_tokens[provider_type] = ProviderToken.from_value(
                            value
                        )
                    except ValueError:
                        # Skip invalid provider types or tokens
                        continue

                # Convert to MappingProxyType
                new_data['provider_tokens'] = MappingProxyType(converted_tokens)
            elif isinstance(tokens, MappingProxyType):
                new_data['provider_tokens'] = tokens

        if 'custom_secrets' in data:
            secrets = data['custom_secrets']
            if isinstance(secrets, dict):
                converted_secrets = {}
                for key, value in secrets.items():
                    try:
                        converted_secrets[key] = CustomSecret.from_value(value)
                    except ValueError:
                        continue

                new_data['custom_secrets'] = MappingProxyType(converted_secrets)
            elif isinstance(secrets, MappingProxyType):
                new_data['custom_secrets'] = secrets

        # Handle integrations field
        if 'integrations' in data:
            integrations_data = data['integrations']
            if isinstance(integrations_data, list):
                converted_integrations = []
                for integration_item in integrations_data:
                    try:
                        # If it's already an Integration object, use it directly
                        if isinstance(integration_item, Integration):
                            converted_integrations.append(integration_item)
                        # If it's a dict, convert it
                        elif isinstance(integration_item, dict):
                            integration = Integration.from_dict(integration_item)
                            converted_integrations.append(integration)
                    except (ValueError, KeyError, AttributeError):
                        # Skip invalid integrations
                        continue
                new_data['integrations'] = converted_integrations
            else:
                new_data['integrations'] = integrations_data

        # Migration: Convert legacy provider_tokens to integrations if no integrations exist
        if ('integrations' not in data or not data['integrations']) and 'provider_tokens' in data:
            legacy_tokens = data['provider_tokens']
            if isinstance(legacy_tokens, (dict, MappingProxyType)) and legacy_tokens:
                migrated_integrations = []
                for provider_key, provider_token in legacy_tokens.items():
                    try:
                        # Handle both string keys and ProviderType enum keys
                        provider_type = (
                            ProviderType(provider_key) 
                            if isinstance(provider_key, str) 
                            else provider_key
                        )
                        token_obj = (
                            ProviderToken.from_value(provider_token)
                            if not isinstance(provider_token, ProviderToken)
                            else provider_token
                        )
                        integration = Integration.from_legacy_provider_token(provider_type, token_obj)
                        migrated_integrations.append(integration)
                    except (ValueError, AttributeError):
                        # Skip invalid provider types or tokens
                        continue
                new_data['integrations'] = migrated_integrations

        return new_data

    def set_event_stream_secrets(self, event_stream: EventStream) -> None:
        """This ensures that provider tokens and custom secrets masked from the event stream
        Args:
            event_stream: Agent session's event stream
        """
        secrets = self.get_env_vars()
        event_stream.set_secrets(secrets)

    def get_env_vars(self) -> dict[str, str]:
        secret_store = self.model_dump(context={'expose_secrets': True})
        custom_secrets = secret_store.get('custom_secrets', {})
        secrets = {}
        for secret_name, value in custom_secrets.items():
            secrets[secret_name] = value['secret']

        return secrets

    def get_custom_secrets_descriptions(self) -> dict[str, str]:
        secrets = {}
        for secret_name, secret in self.custom_secrets.items():
            secrets[secret_name] = secret.description

        return secrets
