"""Tests for the integration management API endpoints."""
import os
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr

from openhands.integrations.provider import Integration
from openhands.server.routes.secrets import app as secrets_app
from openhands.storage import get_file_store
from openhands.storage.data_models.user_secrets import UserSecrets
from openhands.storage.secrets.file_secrets_store import FileSecretsStore


@pytest.fixture
def test_client():
    """Create a test client for the integration API."""
    app = FastAPI()
    app.include_router(secrets_app)

    # Mock SESSION_API_KEY to None to disable authentication in tests
    with patch.dict(os.environ, {'SESSION_API_KEY': ''}, clear=False):
        # Clear the SESSION_API_KEY to disable auth dependency
        with patch('openhands.server.dependencies._SESSION_API_KEY', None):
            yield TestClient(app)


@pytest.fixture
def temp_dir(tmp_path_factory: pytest.TempPathFactory) -> str:
    return str(tmp_path_factory.mktemp('integration_store'))


@pytest.fixture
def file_secrets_store(temp_dir):
    file_store = get_file_store('local', temp_dir)
    store = FileSecretsStore(file_store)
    with patch(
        'openhands.storage.secrets.file_secrets_store.FileSecretsStore.get_instance',
        AsyncMock(return_value=store),
    ):
        yield store


@pytest.mark.asyncio
async def test_get_integrations_empty(test_client, file_secrets_store):
    """Test getting integrations when none exist."""
    # No initial data - simulates new user
    response = test_client.get('/api/integrations')
    assert response.status_code == 200
    
    data = response.json()
    assert 'integrations' in data
    assert data['integrations'] == []


@pytest.mark.asyncio
async def test_get_integrations_with_data(test_client, file_secrets_store):
    """Test getting integrations when some exist."""
    # Create initial user secrets with integrations
    integrations = [
        Integration(
            id='github-personal',
            provider_type='github',
            name='Personal GitHub',
            host=None,
            token=SecretStr('test-token'),
            user_id=None
        ),
        Integration(
            id='gitlab-work',
            provider_type='gitlab',
            name='Work GitLab',
            host='gitlab.company.com',
            token=SecretStr('work-token'),
            user_id='johndoe'
        )
    ]
    
    user_secrets = UserSecrets(integrations=integrations)
    await file_secrets_store.store(user_secrets)
    
    response = test_client.get('/api/integrations')
    assert response.status_code == 200
    
    data = response.json()
    assert 'integrations' in data
    assert len(data['integrations']) == 2
    
    # Check that tokens are not included but has_token flag is set
    github_integration = next(i for i in data['integrations'] if i['id'] == 'github-personal')
    assert github_integration['name'] == 'Personal GitHub'
    assert github_integration['provider_type'] == 'github'
    assert github_integration['has_token'] is True
    assert 'token' not in github_integration
    
    gitlab_integration = next(i for i in data['integrations'] if i['id'] == 'gitlab-work')
    assert gitlab_integration['host'] == 'gitlab.company.com'
    assert gitlab_integration['user_id'] == 'johndoe'


@pytest.mark.asyncio
async def test_add_integration_success(test_client, file_secrets_store):
    """Test adding a new integration successfully."""
    # Mock token validation to succeed
    with patch(
        'openhands.server.routes.secrets.validate_integration_token',
        AsyncMock(return_value=None)  # None means no error
    ):
        integration_data = {
            'id': 'my-github',
            'provider_type': 'github',
            'name': 'My GitHub',
            'host': None,
            'token': 'ghp_test_token',
            'user_id': None
        }
        
        response = test_client.post('/api/integrations', json=integration_data)
        assert response.status_code == 201
        
        # Verify it was stored
        stored_secrets = await file_secrets_store.load()
        assert stored_secrets is not None
        assert len(stored_secrets.integrations) == 1
        assert stored_secrets.integrations[0].id == 'my-github'
        assert stored_secrets.integrations[0].name == 'My GitHub'


@pytest.mark.asyncio
async def test_add_integration_duplicate_id(test_client, file_secrets_store):
    """Test adding integration with duplicate ID fails."""
    # Create existing integration
    existing_integration = Integration(
        id='github-existing',
        provider_type='github',
        name='Existing GitHub',
        host=None,
        token=SecretStr('existing-token'),
        user_id=None
    )
    
    user_secrets = UserSecrets(integrations=[existing_integration])
    await file_secrets_store.store(user_secrets)
    
    # Try to add another integration with same ID
    with patch(
        'openhands.server.routes.secrets.validate_integration_token',
        AsyncMock(return_value=None)
    ):
        integration_data = {
            'id': 'github-existing',  # Same ID as existing
            'provider_type': 'gitlab',
            'name': 'New GitLab',
            'token': 'new-token'
        }
        
        response = test_client.post('/api/integrations', json=integration_data)
        assert response.status_code == 400
        assert 'already exists' in response.json()['error']


@pytest.mark.asyncio
async def test_add_integration_missing_id(test_client, file_secrets_store):
    """Test that missing ID in request fails."""
    integration_data = {
        # Missing 'id' field
        'provider_type': 'github',
        'name': 'Test GitHub',
        'token': 'test-token'
    }
    
    response = test_client.post('/api/integrations', json=integration_data)
    assert response.status_code == 422  # Validation error due to missing required field


@pytest.mark.asyncio 
async def test_add_integration_github_requires_token(test_client, file_secrets_store):
    """Test that GitHub integrations require a token."""
    integration_data = {
        'id': 'github-no-token',
        'provider_type': 'github',
        'name': 'GitHub No Token',
        # Missing token
    }
    
    response = test_client.post('/api/integrations', json=integration_data)
    assert response.status_code == 400
    assert 'Token is required for github' in response.json()['error']


@pytest.mark.asyncio
async def test_delete_integration(test_client, file_secrets_store):
    """Test deleting an integration."""
    # Create initial integration
    integration = Integration(
        id='test-integration',
        provider_type='github',
        name='Test Integration',
        host=None,
        token=SecretStr('test-token'),
        user_id=None
    )
    
    user_secrets = UserSecrets(integrations=[integration])
    await file_secrets_store.store(user_secrets)
    
    # Delete the integration
    response = test_client.delete('/api/integrations/test-integration')
    assert response.status_code == 200
    
    # Verify it was deleted
    stored_secrets = await file_secrets_store.load()
    assert stored_secrets is not None
    assert len(stored_secrets.integrations) == 0