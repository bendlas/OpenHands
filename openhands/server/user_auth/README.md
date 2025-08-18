# Authelia User Authentication

This module provides integration with [Authelia](https://www.authelia.com/), a popular authentication and authorization server for self-hosted environments.

## Features

- Header-based authentication (Remote-User, Remote-Email, etc.)
- JWT/Bearer token support
- Multi-tenancy support with per-user settings and secrets
- Seamless integration with reverse proxies

## Configuration

Set the user authentication class in your OpenHands configuration:

```toml
[core]
user_auth_class = "openhands.server.user_auth.authelia_user_auth.AutheliaUserAuth"
```

## Supported Headers

The Authelia integration extracts user information from the following headers:

| Header | Description | Example |
|--------|-------------|---------|
| `Remote-User` | Username/user ID | `testuser` |
| `X-Remote-User` | Alternative username header | `testuser` |
| `Remote-Email` | User email address | `test@example.com` |
| `X-Remote-Email` | Alternative email header | `test@example.com` |
| `Remote-Name` | Display name | `Test User` |
| `Remote-Groups` | User groups (comma-separated) | `admin,users` |
| `Authorization` | Bearer token (JWT) | `Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...` |
| `X-Access-Token` | Alternative access token header | `token123` |

## Reverse Proxy Configuration

### Nginx

```nginx
location / {
    proxy_pass http://openhands:3000;
    proxy_set_header Remote-User $remote_user;
    proxy_set_header Remote-Email $remote_email;
    proxy_set_header Remote-Name $remote_name;
    proxy_set_header Remote-Groups $remote_groups;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

### Traefik

```yaml
http:
  middlewares:
    authelia:
      forwardAuth:
        address: "http://authelia:9091/api/verify?rd=https://auth.example.com"
        trustForwardHeader: true
        authResponseHeaders:
          - "Remote-User"
          - "Remote-Groups"
          - "Remote-Name"
          - "Remote-Email"
```

## JWT Support

The integration can extract user information from JWT tokens in the `Authorization` header:

```
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

Supported JWT claims:
- `sub` or `preferred_username` or `email` for user ID
- `email` for email address

**Note**: JWT signature verification is not implemented in this basic integration. For production use, consider implementing proper JWT verification.

## Authentication Types

The integration supports two authentication types:

- `AuthType.BEARER`: When an `Authorization` header with a Bearer token is present
- `AuthType.COOKIE`: For header-based authentication without Bearer tokens

## Example Usage

```python
from fastapi import Request
from openhands.server.user_auth.authelia_user_auth import AutheliaUserAuth

# Create auth instance from request
auth = await AutheliaUserAuth.get_instance(request)

# Get user information
user_id = await auth.get_user_id()
email = await auth.get_user_email()
token = await auth.get_access_token()
```

## Security Considerations

1. **Header Spoofing**: Ensure your reverse proxy is properly configured to prevent header spoofing
2. **HTTPS**: Always use HTTPS in production to protect headers in transit
3. **JWT Verification**: Implement proper JWT signature verification for production use
4. **Token Storage**: Access tokens are handled securely using Pydantic's `SecretStr`

## Troubleshooting

### No User Information

If no user information is being extracted:

1. Verify that Authelia is setting the expected headers
2. Check your reverse proxy configuration
3. Ensure the headers are being passed to OpenHands
4. Review OpenHands logs for any errors

### Permission Issues

If users can't access their settings or secrets:

1. Verify the user ID is being extracted correctly
2. Check file permissions in the settings/secrets directories
3. Ensure the user authentication class is configured correctly