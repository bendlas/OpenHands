import os

from pydantic import SecretStr

from openhands.integrations.gitea.base_service import BaseGiteaService
from openhands.integrations.service_types import ProviderType
from openhands.utils.import_utils import get_impl


class GiteaService(BaseGiteaService):
    """Implementation of GitService for Gitea integration."""

    def __init__(
        self,
        user_id: str | None = None,
        external_auth_id: str | None = None,
        external_auth_token: SecretStr | None = None,
        token: SecretStr | None = None,
        external_token_manager: bool = False,
        base_domain: str | None = None,
    ):
        # Set the base domain for Gitea.com if not provided
        if not base_domain:
            base_domain = 'gitea.com'
        
        super().__init__(
            user_id=user_id,
            external_auth_id=external_auth_id,
            external_auth_token=external_auth_token,
            token=token,
            external_token_manager=external_token_manager,
            base_domain=base_domain,
        )

    @property
    def provider(self) -> str:
        return ProviderType.GITEA.value


gitea_service_cls = os.environ.get(
    'OPENHANDS_GITEA_SERVICE_CLS',
    'openhands.integrations.gitea.gitea_service.GiteaService',
)
GiteaServiceImpl = get_impl(GiteaService, gitea_service_cls)