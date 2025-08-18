# OIDC/JWT Bearer UserAuth (Planning)

Goal
- Allow API-first clients to authenticate via Authorization: Bearer <jwt>.
- Derive user_id/email from JWT claims and scope storage accordingly.

Approach
- Implement class OIDCUserAuth(UserAuth) that validates JWT using:
  - OIDC_ISSUER, OIDC_AUDIENCE, OIDC_JWKS_URL (optional if discoverable)
  - OIDC_ACCEPTED_ALGS (e.g., RS256)
- On validate:
  - Extract token from Authorization header.
  - Fetch JWKS & validate signature and claims (issuer, audience, exp, nbf).
  - Derive user_id from sub/email; set get_auth_type() -> BEARER.
- Provider tokens: use per-user SecretsStore as with other auth flows.

Edge Cases
- Clock skew; expired token; missing audience.
- Multi-tenant: ensure per-user scoping consistent with cookie/Authelia path.

Testing
- Unit tests with static JWKS; claims validation.
- E2E test on /api endpoints requiring bearer auth.

Docs
- Env variables and example reverse proxy setup.
- How to switch via OPENHANDS_USER_AUTH_CLS.
