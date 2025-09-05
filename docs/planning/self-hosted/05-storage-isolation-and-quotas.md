# Storage Isolation & Quotas (Planning)

Goal
- Strengthen per-user isolation and optionally enforce quotas.

Current
- Settings, secrets, conversations scoped to users/{user_id}/ in File* stores. EventStore paths user-aware.

Planned Enhancements
- Add optional quotas (max conversations, total bytes) via config.
- Add S3 or other backends with per-user prefixing using existing FileStore abstraction.
- Background pruning jobs per user (age/size thresholds) aligned with conversation_max_age_seconds.

Security
- Ensure no cross-user list/read access at store layer; test path traversal and list boundaries.

Testing
- Unit tests for store list/search with multiple users.
- Integration tests for quota enforcement.
