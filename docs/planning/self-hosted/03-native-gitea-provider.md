# Native Forgejo/Gitea Provider (Planning)

Goal
- First-class Gitea provider parity with GitHub/GitLab/Bitbucket: repo listing/search, branches, PRs, comments, and authenticated clone/push.

Scope
- Add ProviderType.GITEA and a GiteaServiceImpl implementing GitService/InstallationsService facets used today.
- Token/host per user (ProviderToken.host), mapped to env key gitea_token when exporting to runtime.

API Endpoints
- Auth: personal access tokens (PAT) or OAuth tokens.
- Repos: list/search endpoints; pagination.
- Branches: list, default branch detection.
- PRs: create, list comments, detect checks if available (or minimal parity at first).

Runtime Git
- Update ProviderHandler.PROVIDER_DOMAINS to include default Gitea domain (none by default), prefer ProviderToken.host.
- get_authenticated_git_url: support Gitea auth patterns (https://<token>@host/owner/repo.git or OAuth2 schemes if required).

Migrations
- UI "Connect Gitea" entry and token storage flow (reuse Secrets API).

Testing
- Unit tests for service methods (happy paths + auth/404/rate-limit mapping).
- Integration tests for clone/push/PR creation on a test Gitea instance.

Incremental Plan
- Phase 1: read-only repo discovery + branch listing + authenticated clone URL.
- Phase 2: PR creation + comments + suggested tasks integration.
- Phase 3: advanced features (checks/events) as available.
