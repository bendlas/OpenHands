# Self-Hosted Setup Guide

This guide explains how to configure OpenHands for self-hosted environments with Authelia authentication and Gitea/Forgejo integration.

## Authentication with Authelia

Authelia is a popular authentication and authorization server for self-hosted environments. OpenHands can be configured to work with Authelia by using the `AutheliaUserAuth` class.

### Configuration

1. Set the user authentication class in your configuration:

```toml
[core]
user_auth_class = "openhands.server.user_auth.authelia_user_auth.AutheliaUserAuth"
```

2. Configure your reverse proxy (nginx, Traefik, etc.) to set the appropriate headers:

```nginx
# Example nginx configuration
proxy_set_header Remote-User $remote_user;
proxy_set_header Remote-Email $remote_email;
proxy_set_header Remote-Name $remote_name;
proxy_set_header Remote-Groups $remote_groups;
```

### Supported Headers

The Authelia integration supports the following headers:

- `Remote-User` or `X-Remote-User`: Username/user ID
- `Remote-Email` or `X-Remote-Email`: User email address
- `Remote-Name`: Display name
- `Remote-Groups`: User groups (comma-separated)
- `Authorization`: Bearer token (JWT support)
- `X-Access-Token`: Alternative access token header

## Gitea/Forgejo Integration

OpenHands now supports Gitea and Forgejo Git providers alongside GitHub, GitLab, and Bitbucket.

### Configuration

Add Gitea configuration to your user secrets or environment:

```bash
export GITEA_TOKEN="your-gitea-access-token"
```

Or configure it in the user interface by selecting "Gitea" as the provider type.

### MCP Server Integration

You can use the [Gitea MCP Server](https://about.gitea.com/resources/tutorials/gitea-mcp-server) to enhance OpenHands' integration with your Gitea instance.

#### Installing the Gitea MCP Server

```bash
npm install -g @gitea/mcp-server
```

#### Configuration

Create or update the MCP configuration file (`openhands/runtime/mcp/config.json`):

```json
{
  "mcpServers": {
    "gitea": {
      "command": "npx",
      "args": ["@gitea/mcp-server"],
      "env": {
        "GITEA_URL": "https://your-gitea-instance.com",
        "GITEA_TOKEN": "your-gitea-token"
      }
    }
  },
  "tools": []
}
```

#### Available MCP Tools

The Gitea MCP server provides tools for:

- Repository management
- Issue tracking
- Pull request operations
- Release management
- Organization/user management

### Custom Gitea Instance

For self-hosted Gitea instances, configure the base domain:

```python
from openhands.integrations.gitea.gitea_service import GiteaService

service = GiteaService(
    token=SecretStr("your-token"),
    base_domain="git.example.com"  # Your Gitea instance domain
)
```

## Example Configuration

Here's a complete example configuration for a self-hosted setup:

```toml
[core]
# Use Authelia for authentication
user_auth_class = "openhands.server.user_auth.authelia_user_auth.AutheliaUserAuth"

# JWT secret for session management
jwt_secret = "your-secret-key"

[llm]
# Configure your preferred LLM
model = "gpt-4o"
api_key = "your-api-key"

[sandbox]
# Configure for your environment
base_container_image = "nikolaik/python-nodejs:python3.12-nodejs22"
```

## Environment Variables

Set these environment variables for Gitea integration:

```bash
# Gitea Configuration
export GITEA_TOKEN="gta_xxxxxxxxxxxx"
export GITEA_URL="https://git.example.com"

# Optional: For MCP server
export GITEA_MCP_ENABLED="true"
```

## Security Considerations

1. **Token Security**: Store Gitea tokens securely and rotate them regularly
2. **Network Security**: Ensure secure communication between OpenHands and your Gitea instance
3. **Access Control**: Use Authelia's access control features to restrict access to OpenHands
4. **HTTPS**: Always use HTTPS for production deployments

## Troubleshooting

### Authentication Issues

- Verify Authelia headers are being passed correctly
- Check that the user authentication class is configured properly
- Ensure the JWT secret is consistent across restarts

### Gitea Connection Issues

- Verify the Gitea token has appropriate permissions
- Check that the base domain is configured correctly for self-hosted instances
- Ensure network connectivity between OpenHands and Gitea

### MCP Integration Issues

- Verify the Gitea MCP server is installed and accessible
- Check the MCP configuration file syntax
- Review OpenHands logs for MCP-related errors