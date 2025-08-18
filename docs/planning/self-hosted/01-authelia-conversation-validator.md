# Authelia Conversation Validator (Planning)

Goal
- Enforce per-conversation WebSocket access using Authelia’s session verification.
- Map connections to user_id deterministically; ensure only owner (or allowed users) can connect.

Approach
- Implement class AutheliaConversationValidator(ConversationValidator) with async validate(conversation_id, cookies_str, authorization_header) -> user_id.
- Use env to configure:
  - AUTHELIA_VERIFY_URL (e.g., http://authelia:9091/api/verify)
  - AUTHELIA_FORWARD_HEADERS (comma-separated list of headers to forward to Authelia)
  - AUTHELIA_TRUSTED_PROXY=1 (optional guard)
- Logic:
  1. Parse cookies_str; pass raw Cookie header to Authelia verify endpoint.
  2. On 200 OK + authenticated=true, read subject/email or forwarded username.
  3. If conversation metadata doesn’t exist, create with that user_id; else enforce ownership matches.
  4. Return user_id. On failure, raise ConnectionRefusedError.

Edge Cases
- Conversation created without user_id (legacy): allow adopting ownership on first verified connect.
- Multi-tenant: enforce exact match; optionally support collaborator list in metadata.

Testing
- Unit test with mocked HTTP calls to Authelia verify.
- Integration test with connect() handler path, ensuring EventStore uses the returned user_id.

Rollout
- Ship class and docs; allow opt-in via OPENHANDS_CONVERSATION_VALIDATOR_CLS.
