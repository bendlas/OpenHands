from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from openhands.core.logger import openhands_logger as logger
from openhands.integrations.provider import PROVIDER_TOKEN_TYPE, CustomSecret
from openhands.integrations.service_types import ProviderType
from openhands.integrations.utils import validate_provider_token
from openhands.server.dependencies import get_dependencies
from openhands.server.settings import (
    CustomSecretModel,
    CustomSecretWithoutValueModel,
    GETCustomSecrets,
    POSTIntegrationModel,
    POSTProviderModel,
)
from openhands.server.user_auth import (
    get_provider_tokens,
    get_secrets_store,
    get_user_secrets,
)
from openhands.storage.data_models.settings import Settings
from openhands.storage.data_models.user_secrets import UserSecrets
from openhands.storage.secrets.secrets_store import SecretsStore
from openhands.storage.settings.settings_store import SettingsStore

app = APIRouter(prefix='/api', dependencies=get_dependencies())


# =================================================
# SECTION: Handle git provider tokens
# =================================================


async def invalidate_legacy_secrets_store(
    settings: Settings, settings_store: SettingsStore, secrets_store: SecretsStore
) -> UserSecrets | None:
    """We are moving `secrets_store` (a field from `Settings` object) to its own dedicated store
    This function moves the values from Settings to UserSecrets, and deletes the values in Settings
    While this function in called multiple times, the migration only ever happens once
    """
    if len(settings.secrets_store.provider_tokens.items()) > 0:
        user_secrets = UserSecrets(
            provider_tokens=settings.secrets_store.provider_tokens
        )
        await secrets_store.store(user_secrets)

        # Invalidate old tokens via settings store serializer
        invalidated_secrets_settings = settings.model_copy(
            update={'secrets_store': UserSecrets()}
        )
        await settings_store.store(invalidated_secrets_settings)

        return user_secrets

    return None


def process_token_validation_result(
    confirmed_token_type: ProviderType | None, token_type: ProviderType
) -> str:
    if not confirmed_token_type or confirmed_token_type != token_type:
        return (
            f'Invalid token. Please make sure it is a valid {token_type.value} token.'
        )

    return ''


async def check_provider_tokens(
    incoming_provider_tokens: POSTProviderModel,
    existing_provider_tokens: PROVIDER_TOKEN_TYPE | None,
) -> str:
    msg = ''
    if incoming_provider_tokens.provider_tokens:
        # Determine whether tokens are valid
        for token_type, token_value in incoming_provider_tokens.provider_tokens.items():
            if token_value.token:
                confirmed_token_type = await validate_provider_token(
                    token_value.token, token_value.host
                )  # FE always sends latest host
                msg = process_token_validation_result(confirmed_token_type, token_type)

            existing_token = (
                existing_provider_tokens.get(token_type, None)
                if existing_provider_tokens
                else None
            )
            if (
                existing_token
                and (existing_token.host != token_value.host)
                and existing_token.token
            ):
                confirmed_token_type = await validate_provider_token(
                    existing_token.token, token_value.host
                )  # Host has changed, check it against existing token
                if not confirmed_token_type or confirmed_token_type != token_type:
                    msg = process_token_validation_result(
                        confirmed_token_type, token_type
                    )

    return msg


@app.post('/add-git-providers')
async def store_provider_tokens(
    provider_info: POSTProviderModel,
    secrets_store: SecretsStore = Depends(get_secrets_store),
    provider_tokens: PROVIDER_TOKEN_TYPE | None = Depends(get_provider_tokens),
) -> JSONResponse:
    provider_err_msg = await check_provider_tokens(provider_info, provider_tokens)
    if provider_err_msg:
        # We don't have direct access to user_id here, but we can log the provider info
        logger.info(
            f'Returning 401 Unauthorized - Provider token error: {provider_err_msg}'
        )
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={'error': provider_err_msg},
        )

    try:
        user_secrets = await secrets_store.load()
        if not user_secrets:
            user_secrets = UserSecrets()

        if provider_info.provider_tokens:
            existing_providers = [provider for provider in user_secrets.provider_tokens]

            # Merge incoming settings store with the existing one
            for provider, token_value in list(provider_info.provider_tokens.items()):
                if provider in existing_providers and not token_value.token:
                    existing_token = user_secrets.provider_tokens.get(provider)
                    if existing_token and existing_token.token:
                        provider_info.provider_tokens[provider] = existing_token

                provider_info.provider_tokens[provider] = provider_info.provider_tokens[
                    provider
                ].model_copy(update={'host': token_value.host})

        updated_secrets = user_secrets.model_copy(
            update={'provider_tokens': provider_info.provider_tokens}
        )
        await secrets_store.store(updated_secrets)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={'message': 'Git providers stored'},
        )
    except Exception as e:
        logger.warning(f'Something went wrong storing git providers: {e}')
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={'error': 'Something went wrong storing git providers'},
        )


@app.post('/unset-provider-tokens', response_model=dict[str, str])
async def unset_provider_tokens(
    secrets_store: SecretsStore = Depends(get_secrets_store),
) -> JSONResponse:
    try:
        user_secrets = await secrets_store.load()
        if user_secrets:
            updated_secrets = user_secrets.model_copy(update={'provider_tokens': {}})
            await secrets_store.store(updated_secrets)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={'message': 'Unset Git provider tokens'},
        )

    except Exception as e:
        logger.warning(f'Something went wrong unsetting tokens: {e}')
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={'error': 'Something went wrong unsetting tokens'},
        )


# =================================================
# SECTION: Handle custom secrets
# =================================================


@app.get('/secrets', response_model=GETCustomSecrets)
async def load_custom_secrets_names(
    user_secrets: UserSecrets | None = Depends(get_user_secrets),
) -> GETCustomSecrets | JSONResponse:
    try:
        if not user_secrets:
            return GETCustomSecrets(custom_secrets=[])

        custom_secrets: list[CustomSecretWithoutValueModel] = []
        if user_secrets.custom_secrets:
            for secret_name, secret_value in user_secrets.custom_secrets.items():
                custom_secret = CustomSecretWithoutValueModel(
                    name=secret_name,
                    description=secret_value.description,
                )
                custom_secrets.append(custom_secret)

        return GETCustomSecrets(custom_secrets=custom_secrets)

    except Exception as e:
        logger.warning(f'Failed to load secret names: {e}')
        logger.info('Returning 401 Unauthorized - Failed to get secret names')
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={'error': 'Failed to get secret names'},
        )


@app.post('/secrets', response_model=dict[str, str])
async def create_custom_secret(
    incoming_secret: CustomSecretModel,
    secrets_store: SecretsStore = Depends(get_secrets_store),
) -> JSONResponse:
    try:
        existing_secrets = await secrets_store.load()
        custom_secrets = (
            dict(existing_secrets.custom_secrets) if existing_secrets else {}
        )

        secret_name = incoming_secret.name
        secret_value = incoming_secret.value
        secret_description = incoming_secret.description

        if secret_name in custom_secrets:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={'message': f'Secret {secret_name} already exists'},
            )

        custom_secrets[secret_name] = CustomSecret(
            secret=secret_value,
            description=secret_description or '',
        )

        # Create a new UserSecrets that preserves provider tokens
        updated_user_secrets = UserSecrets(
            custom_secrets=custom_secrets,  # type: ignore[arg-type]
            provider_tokens=existing_secrets.provider_tokens
            if existing_secrets
            else {},  # type: ignore[arg-type]
        )

        await secrets_store.store(updated_user_secrets)

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={'message': 'Secret created successfully'},
        )
    except Exception as e:
        logger.warning(f'Something went wrong creating secret: {e}')
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={'error': 'Something went wrong creating secret'},
        )


@app.put('/secrets/{secret_id}', response_model=dict[str, str])
async def update_custom_secret(
    secret_id: str,
    incoming_secret: CustomSecretWithoutValueModel,
    secrets_store: SecretsStore = Depends(get_secrets_store),
) -> JSONResponse:
    try:
        existing_secrets = await secrets_store.load()
        if existing_secrets:
            # Check if the secret to update exists
            if secret_id not in existing_secrets.custom_secrets:
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={'error': f'Secret with ID {secret_id} not found'},
                )

            secret_name = incoming_secret.name
            secret_description = incoming_secret.description

            custom_secrets = dict(existing_secrets.custom_secrets)
            existing_secret = custom_secrets.pop(secret_id)

            if secret_name != secret_id and secret_name in custom_secrets:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={'message': f'Secret {secret_name} already exists'},
                )

            custom_secrets[secret_name] = CustomSecret(
                secret=existing_secret.secret,
                description=secret_description or '',
            )

            updated_secrets = UserSecrets(
                custom_secrets=custom_secrets,  # type: ignore[arg-type]
                provider_tokens=existing_secrets.provider_tokens,
            )

            await secrets_store.store(updated_secrets)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={'message': 'Secret updated successfully'},
        )
    except Exception as e:
        logger.warning(f'Something went wrong updating secret: {e}')
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={'error': 'Something went wrong updating secret'},
        )


@app.delete('/secrets/{secret_id}')
async def delete_custom_secret(
    secret_id: str,
    secrets_store: SecretsStore = Depends(get_secrets_store),
) -> JSONResponse:
    try:
        existing_secrets = await secrets_store.load()
        if existing_secrets:
            # Get existing custom secrets
            custom_secrets = dict(existing_secrets.custom_secrets)

            # Check if the secret to delete exists
            if secret_id not in custom_secrets:
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={'error': f'Secret with ID {secret_id} not found'},
                )

            # Remove the secret
            custom_secrets.pop(secret_id)

            # Create a new UserSecrets that preserves provider tokens and remaining secrets
            updated_secrets = UserSecrets(
                custom_secrets=custom_secrets,  # type: ignore[arg-type]
                provider_tokens=existing_secrets.provider_tokens,
            )

            await secrets_store.store(updated_secrets)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={'message': 'Secret deleted successfully'},
        )
    except Exception as e:
        logger.warning(f'Something went wrong deleting secret: {e}')
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={'error': 'Something went wrong deleting secret'},
        )


# =================================================
# SECTION: Handle integrations (new dynamic system)
# =================================================


@app.get('/integrations')
async def get_integrations(
    user_secrets: UserSecrets = Depends(get_user_secrets),
) -> JSONResponse:
    """Get all configured integrations"""
    try:
        integrations = user_secrets.integrations or []
        # Return integrations without sensitive data (tokens)
        safe_integrations = []
        for integration in integrations:
            safe_integration = {
                'id': integration.id,
                'provider_type': integration.provider_type,
                'name': integration.name,
                'host': integration.host,
                'user_id': integration.user_id,
                'has_token': integration.token is not None and integration.token.get_secret_value() != ''
            }
            safe_integrations.append(safe_integration)
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={'integrations': safe_integrations}
        )
    except Exception as e:
        logger.warning(f'Something went wrong getting integrations: {e}')
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={'error': 'Something went wrong getting integrations'},
        )


async def validate_integration_token(
    provider_type: str, token: SecretStr, host: str | None = None
) -> str:
    """Validate an integration token and return error message if invalid"""
    if not token or token.get_secret_value() == '':
        return ''
    
    # Try to validate the token
    confirmed_provider_type = await validate_provider_token(token, host)
    if not confirmed_provider_type or confirmed_provider_type.value != provider_type:
        return f'Invalid token. Please make sure it is a valid {provider_type} token.'
    
    return ''


@app.post('/integrations')
async def add_integration(
    integration_data: POSTIntegrationModel,
    secrets_store: SecretsStore = Depends(get_secrets_store),
) -> JSONResponse:
    """Add a new integration"""
    try:
        # Validate token if provided
        if integration_data.token:
            error_msg = await validate_integration_token(
                integration_data.provider_type, 
                integration_data.token, 
                integration_data.host
            )
            if error_msg:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={'error': error_msg},
                )
        
        user_secrets = await secrets_store.load()
        if not user_secrets:
            user_secrets = UserSecrets()
        
        # Check if integration ID already exists
        existing_integrations = list(user_secrets.integrations) if user_secrets.integrations else []
        for existing in existing_integrations:
            if existing.id == integration_data.id:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={'error': f'Integration with ID "{integration_data.id}" already exists'},
                )
        
        # Create new integration
        new_integration = Integration(
            id=integration_data.id,
            provider_type=integration_data.provider_type,
            name=integration_data.name,
            host=integration_data.host,
            token=integration_data.token,
            user_id=integration_data.user_id,
        )
        
        # Add to existing integrations
        updated_integrations = existing_integrations + [new_integration]
        
        # Update user secrets
        updated_secrets = user_secrets.model_copy(
            update={'integrations': updated_integrations}
        )
        await secrets_store.store(updated_secrets)
        
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={'message': f'Integration "{integration_data.name}" added successfully'},
        )
    except Exception as e:
        logger.warning(f'Something went wrong adding integration: {e}')
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={'error': 'Something went wrong adding integration'},
        )


@app.put('/integrations/{integration_id}')
async def update_integration(
    integration_id: str,
    integration_data: POSTIntegrationModel,
    secrets_store: SecretsStore = Depends(get_secrets_store),
) -> JSONResponse:
    """Update an existing integration"""
    try:
        # Validate token if provided
        if integration_data.token:
            error_msg = await validate_integration_token(
                integration_data.provider_type, 
                integration_data.token, 
                integration_data.host
            )
            if error_msg:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={'error': error_msg},
                )
        
        user_secrets = await secrets_store.load()
        if not user_secrets:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={'error': f'Integration with ID "{integration_id}" not found'},
            )
        
        # Find and update the integration
        existing_integrations = list(user_secrets.integrations) if user_secrets.integrations else []
        updated_integrations = []
        found = False
        
        for existing in existing_integrations:
            if existing.id == integration_id:
                # Update the existing integration, preserving token if not provided
                token = integration_data.token if integration_data.token else existing.token
                updated_integration = Integration(
                    id=integration_data.id,  # Allow ID changes
                    provider_type=integration_data.provider_type,
                    name=integration_data.name,
                    host=integration_data.host,
                    token=token,
                    user_id=integration_data.user_id,
                )
                updated_integrations.append(updated_integration)
                found = True
            else:
                updated_integrations.append(existing)
        
        if not found:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={'error': f'Integration with ID "{integration_id}" not found'},
            )
        
        # Check for ID conflicts if ID was changed
        if integration_data.id != integration_id:
            for integration in updated_integrations:
                if integration.id == integration_data.id and integration != updated_integrations[-1]:
                    return JSONResponse(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        content={'error': f'Integration with ID "{integration_data.id}" already exists'},
                    )
        
        # Update user secrets
        updated_secrets = user_secrets.model_copy(
            update={'integrations': updated_integrations}
        )
        await secrets_store.store(updated_secrets)
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={'message': f'Integration "{integration_data.name}" updated successfully'},
        )
    except Exception as e:
        logger.warning(f'Something went wrong updating integration: {e}')
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={'error': 'Something went wrong updating integration'},
        )


@app.delete('/integrations/{integration_id}')
async def delete_integration(
    integration_id: str,
    secrets_store: SecretsStore = Depends(get_secrets_store),
) -> JSONResponse:
    """Delete an integration"""
    try:
        user_secrets = await secrets_store.load()
        if not user_secrets:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={'error': f'Integration with ID "{integration_id}" not found'},
            )
        
        # Find and remove the integration
        existing_integrations = list(user_secrets.integrations) if user_secrets.integrations else []
        updated_integrations = []
        found = False
        
        for existing in existing_integrations:
            if existing.id == integration_id:
                found = True
                # Skip this integration (remove it)
            else:
                updated_integrations.append(existing)
        
        if not found:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={'error': f'Integration with ID "{integration_id}" not found'},
            )
        
        # Update user secrets
        updated_secrets = user_secrets.model_copy(
            update={'integrations': updated_integrations}
        )
        await secrets_store.store(updated_secrets)
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={'message': f'Integration "{integration_id}" deleted successfully'},
        )
    except Exception as e:
        logger.warning(f'Something went wrong deleting integration: {e}')
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={'error': 'Something went wrong deleting integration'},
        )
