# Changelog

All notable changes to this project will be documented in this file.

## [1.1.0] - 2026-05-04

### Added
- **Security Enhancements:**
  - Password strength validation (8+ chars, uppercase, lowercase, digit)
  - Comprehensive input validation for poll questions, options, and user inputs
  - HTML escaping on all user inputs to prevent XSS attacks
  - Enhanced CSRF protection enabled by default
  - Thread-safe ledger operations with mutex lock
  - Admin authorization checks on all sensitive endpoints

- **Code Quality:**
  - Improved error handling and logging throughout application
  - User feedback messages (flash) for all operations
  - Better documentation in README and code comments

- **Testing:**
  - Unit test recommendations for security features
  - Load testing recommendations for concurrent operations

### Changed
- **app.py:**
  - Fixed SQL syntax error in `/ready` health check endpoint
  - Enabled CSRF protection by default (`WTF_CSRF_CHECK_DEFAULT = True`)
  - Added proper error handling for database connections

- **auth.py (Complete Rewrite):**
  - Added `validate_password_strength()` function
  - Added `validate_username()` function
  - Implemented input escaping with `markupsafe.escape()`
  - Added flash messages for user feedback
  - Improved login/register error handling with proper HTTP status codes
  - Username validation (3-80 chars, alphanumeric + dash/underscore)

- **admin.py (Full Refactor):**
  - Added `validate_poll_question()` function (5-300 chars)
  - Added `validate_poll_options()` function (2-10 options, 1-200 chars each)
  - Added `validate_poll_times()` function for datetime validation
  - Added missing `@admin_only` decorators to `export_poll()` and `download_ledger()`
  - Improved admin decorator with proper error messages and redirects
  - Added input sanitization on all poll fields
  - Enhanced error logging and user-facing error messages

- **poll_blueprint.py (Major Refactor):**
  - Fixed IndentationError on line 51 (critical syntax error)
  - Removed redundant database query (was querying twice for same option)
  - Refactored vote logic for clarity and correctness
  - Separated authenticated vs anonymous user voting logic
  - Fixed IP address tracking (only for anonymous users now)
  - Improved response handling (proper `make_response()` usage)
  - Added proper HTTP status codes (409 Conflict for duplicate votes)

- **utils.py (Enhanced Security):**
  - Added thread-safe ledger operations with `LEDGER_LOCK` mutex
  - Improved encryption error handling with detailed logging
  - Enhanced `load_key()` with better error messages
  - Improved `verify_ledger()` with field validation
  - Added InvalidToken exception handling for encryption

### Fixed
- **Critical Bugs:**
  - Fixed SQL syntax error: `SELECT *` → `SELECT 1` with proper text() wrapper
  - Fixed IndentationError preventing vote function from executing

- **Security Issues:**
  - CSRF protection was disabled by default (now enabled)
  - Weak password validation (now requires 8+ chars, uppercase, lowercase, digit)
  - Missing input validation on poll questions and options
  - Missing authorization checks on admin export/download endpoints
  - XSS vulnerability due to unescaped user inputs (now escaped)
  - Information disclosure in error messages (now generic + logged)

- **Logic Issues:**
  - Redundant database query in vote function (single query now)
  - Unreachable IP checking code (now properly scoped)
  - Race condition in vote processing (protected with DB constraint + mutex)
  - Inconsistent IP address tracking (only for anonymous users now)

### Removed
- Unused import statements in several files
- Redundant database queries

### Security
- ✅ CSRF token protection enabled by default on all POST endpoints
- ✅ Password strength requirements (8+ chars, uppercase, lowercase, digit)
- ✅ Input validation and HTML escaping on all user inputs
- ✅ Admin authorization checks on sensitive endpoints (`@admin_only`)
- ✅ Thread-safe ledger operations (mutex lock on file operations)
- ✅ Database unique constraints prevent duplicate votes
- ✅ Graceful encryption error handling
- ✅ Generic error messages to users, detailed logs for debugging
- ✅ XSS prevention through input escaping

### Breaking Changes
- None (backward compatible)

### Migration Notes
- Update `requirements.txt` to include `markupsafe>=2.1.3`
- CSRF tokens now required on all POST forms
- Admin endpoints now enforce `@admin_only` decorator

### Dependencies
- Added `markupsafe>=2.1.3` for input sanitization

---

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
