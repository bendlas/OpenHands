import os

from pydantic import SecretStr

from openhands.integrations.gitea.base_service import BaseGiteaService
from openhands.integrations.service_types import ProviderType
from openhands.utils.import_utils import get_impl


class ForgejoService(BaseGiteaService):
    """Implementation of GitService for Forgejo integration."""

    def __init__(
        self,
        user_id: str | None = None,
        external_auth_id: str | None = None,
        external_auth_token: SecretStr | None = None,
        token: SecretStr | None = None,
        external_token_manager: bool = False,
        base_domain: str | None = None,
    ):
        # Set the base domain for Codeberg if not provided
        if not base_domain:
            base_domain = 'codeberg.org'
        
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
        return ProviderType.FORGEJO.value


forgejo_service_cls = os.environ.get(
    'OPENHANDS_FORGEJO_SERVICE_CLS',
    'openhands.integrations.forgejo.forgejo_service.ForgejoService',
)
ForgejoServiceImpl = get_impl(ForgejoService, forgejo_service_cls)