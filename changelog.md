# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] - 2024-12-29

### Added
- Initial release
- Encrypted voting system with Fernet encryption
- Blockchain-style vote ledger
- Admin dashboard with poll management
- User authentication and registration
- CSRF protection
- Docker and Docker Compose support
- Kubernetes deployment configuration
- Health check endpoints
- Volume-based data persistence
- One-vote-per-user enforcement
- Poll expiration logic with countdown
- CSV export for poll results

### Security
- Password hashing with Werkzeug
- CSRF token protection
- Encrypted vote storage
- IP-based duplicate vote prevention
- Environment-based secret management
