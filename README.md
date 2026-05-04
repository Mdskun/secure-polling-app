# 🔐 Secure Polling App — Flask + SQLAlchemy + Encryption + Docker


[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)](https://flask.palletsprojects.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)
[![Security](https://img.shields.io/badge/Security-Enhanced-green.svg)](#-security-features)

---

This application allows users to vote once per poll, with encrypted vote storage and admin management, including poll creation and expiration logic.

## 🛠️ Tech Stack

**Backend:**
- Flask (Python Web Framework)
- SQLAlchemy (ORM)
- Flask-Login (Authentication)
- Flask-WTF (CSRF Protection)
- Gunicorn (WSGI Server)

**Security:**
- Fernet Encryption (Vote Privacy)
- CSRF Protection
- Password Hashing (Werkzeug)
- Input Validation & Sanitization (markupsafe)
- Blockchain-style Vote Ledger

**DevOps:**
- Docker & Docker Compose
- Kubernetes-ready
- Volume-based Persistence
- Health Check Endpoints

## 📸 Screenshots

   ### Homepage
   ![Homepage](screenshots/homepage.png)

   ### Voting Interface
   ![Voting](screenshots/voting.png)

   ### Admin Dashboard
   ![Admin Dashboard](screenshots/admin-dashboard.png)


---

## 🚀 Features

| Feature | Status |
|--------|--------|
| Create polls (admin only) | ✅ |
| Vote once per poll (authenticated user ID or anonymous IP/cookie) | ✅ |
| SQLAlchemy database model (SQLite volume) | ✅ |
| Encrypted voting using Fernet | ✅ |
| Secret stored outside codebase | ✅ |
| Key changes when container is re-created (unless same volumes are used) | ✅ |
| WSGI (Gunicorn) for production | ✅ |
| Docker & Docker Compose setup | ✅ |
| Kubernetes-ready deployment flow | ✅ |
|CSRF protection on all endpoints | ✅ |
|Password strength validation | ✅ |
|Input validation & sanitization | ✅ |
|Thread-safe vote ledger | ✅ |

---

## 📂 Project Structure

```
secure-polling-app/
│
├── app.py                      # Flask app initialization
├── wsgi.py                     # WSGI entry point
├── models.py                   # Database models
├── utils.py                    # Encryption & ledger utilities
├── admin.py                    # Admin dashboard blueprint
├── auth.py                     # Authentication blueprint
├── poll_blueprint.py           # Poll voting blueprint
├── requirements.txt            # Python dependencies
│
├── entrypoint.sh              # Docker entrypoint
├── Dockerfile                 # Container image
├── docker-compose.yml         # Docker Compose configuration
├── gunicorn.conf.py           # Gunicorn configuration
│
├── templates/                 # HTML templates
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── poll_detail.html
│   ├── admin_dashboard.html
│   ├── admin_poll_list.html
│   ├── admin_edit_poll.html
│   └── new_poll.html
│
├── static/                    # CSS & assets
│   └── style.css
│
└── data/                      # Docker volume mount (created at runtime)
    ├── poll_encryption_key    # Fernet encryption key
    ├── polls.db               # SQLite database
    └── ledger.jsonl           # Audit trail (blockchain-style)
```

---

## 🔐 Security Model

### ✔ Vote Encryption

Votes are encrypted using **Fernet symmetric encryption**.
The encryption key:

- Is **not stored in code**
- Is mounted at runtime via secrets
- Can rotate safely if using MultiFernet mode

### ✔ One-Vote Enforcement

**Authenticated Users:**
- Vote tracked by `user_id`
- Database unique constraint prevents duplicates
- Cannot re-vote on same poll

**Anonymous Users:**
- Vote tracked by `ip_address` + browser cookie
- IP address checked to prevent multiple votes from same network
- Browser cookie prevents re-voting from same browser
- Both checks must pass for anonymous users to vote

### ✔ Admin Authentication

Admin credentials are set through environment variables:

```bash
ADMINU=admin
ADMINP=adminpass
```

All admin endpoints require both authentication and admin privileges.

### ✔ CSRF Protection

- Enabled by default on all POST endpoints
- Flask-WTF CSRF tokens required
- Prevents cross-site forgery attacks

### ✔ Password Security

All user passwords must meet minimum requirements:
- **Minimum 8 characters**
- **At least one uppercase letter (A-Z)**
- **At least one lowercase letter (a-z)**
- **At least one digit (0-9)**

Passwords are hashed using Werkzeug's secure hashing algorithm.

---

## 🧰 Installation (Local)

### 1. Create venv

```sh
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Generate Encryption Key (Local Development Only)

For local development, create a data directory:
```sh
mkdir -p data
python - <<EOF
from cryptography.fernet import Fernet
with open('data/poll_encryption_key', 'wb') as f:
    f.write(Fernet.generate_key())
EOF
```

### 3. Set Environment Variables

```bash
export SECRET_KEY="your-secret-key-here"
export ADMINU="admin"
export ADMINP="admin_password"
export FLASK_ENV="development"
```

### 4. Run the application

```sh
python app.py
```

**Note:** When running with Docker, encryption key generation is handled automatically by `entrypoint.sh`

---

## 🐳 Running With Docker

### Build & Run

```sh
docker-compose up --build
```

App runs at:

➡ [http://localhost:5000](http://localhost:5000)

### Persistent Data

* SQLite DB stored in a Docker volume
* Encryption key stored in mounted volume
* Ledger (audit trail) stored in mounted volume

### Environment Setup

Create a `.env` file in the project root:

```env
SECRET_KEY=your-secret-key-change-me
ADMINU=admin
ADMINP=yourSecurePassword123
FLASK_ENV=production
```

---

## 🛠 Dockerfile (Production-ready)

* Uses **python:3.11-slim**
* Runs under **Gunicorn WSGI**
* `entrypoint.sh` creates or loads the encryption key
* Automatically creates admin account on first run
* Non-root user for security

---

## 🔧 Entrypoint Behavior

**On first run:**
* Generates a new encryption key if none exists
* Creates admin account with credentials from environment variables
* Saves encryption key to mounted volume for persistence

**On subsequent restarts:**
* Reuses the persisted encryption key
* Admin account already exists (not recreated)

**Volume persistence:**

| Scenario | Result |
|----------|--------|
| Restart container with same volume | Same key & database retained ✅ |
| Restart with new volume | New key generated ⚠️ |
| Migrate to new container | Mount same volume to retain key ✅ |

---

## ☸ Kubernetes Deployment (Optional)

Workflow:

1. Build and push image to registry:
```bash
docker build -t your-registry/polling-app:1.0 .
docker push your-registry/polling-app:1.0
```

2. Create Kubernetes Secret:
```bash
kubectl create secret generic poll-encryption-key \
  --from-file=poll_encryption_key=secrets/poll_encryption_key
```

3. Apply Deployment + PVC + Service manifests

4. Expose via Ingress with HTTPS

---

## 🧪 Environment Variables

| Variable | Purpose | Required | Example |
|----------|---------|----------|---------|
| `SECRET_KEY` | Flask session secret key | Yes | `your-secret-key` |
| `ADMINU` | Built-in admin username | Yes | `admin` |
| `ADMINP` | Built-in admin password | Yes | `SecurePass123` |
| `FLASK_ENV` | Environment mode | No | `production` or `development` |
| `POLL_ENCRYPTION_KEY` | Encryption key (alternative to file) | No | `<fernet-key>` |

---

## 🔐 Security Features

### Authentication & Validation

✅ **Password Strength Requirements**
- Minimum 8 characters
- Must include uppercase letter
- Must include lowercase letter
- Must include digit

✅ **Username Validation**
- 3-80 characters long
- Alphanumeric, dash, and underscore only
- Duplicate username prevention

✅ **CSRF Protection**
- Enabled by default on all POST endpoints
- Flask-WTF CSRF tokens required
- Prevents cross-site request forgery attacks

✅ **Input Sanitization**
- All user inputs HTML-escaped using `markupsafe.escape()`
- Prevents XSS (Cross-Site Scripting) attacks
- Applied to poll questions, options, and usernames

### One-Vote Enforcement

✅ **Authenticated Users**
- Vote tracked by `user_id`
- Database unique constraint prevents duplicates
- Cannot re-vote on same poll

✅ **Anonymous Users**
- Vote tracked by `ip_address` + browser cookie
- IP address checked to prevent multiple votes
- Browser cookie prevents re-voting from same browser

✅ **Thread-Safe Operations**
- Ledger file operations protected with mutex lock
- Prevents race conditions in concurrent environments
- Database-level unique constraints ensure data integrity

### Poll Validation

✅ **Question Validation**
- 5-300 characters long
- HTML-escaped for security

✅ **Options Validation**
- 2-10 options per poll
- 1-200 characters per option
- HTML-escaped for security

✅ **DateTime Validation**
- Start/end times validated
- End time must be after start time
- Invalid formats rejected

### Admin Security

✅ **Authorization Checks**
- `@admin_only` decorator on all sensitive endpoints
- Requires both authentication and admin privileges
- Redirects unauthorized users with error message

✅ **Error Handling**
- Sensitive errors logged server-side only
- Generic error messages shown to users
- No information disclosure in responses

✅ **Audit Trail**
- All votes recorded in blockchain-style ledger
- SHA256 hashing ensures integrity
- Previous hash links create chain (cannot tamper with past votes)

### Encryption

✅ **Vote Privacy**
- Votes encrypted using Fernet symmetric encryption
- Only readable with correct encryption key

✅ **Key Management**
- Encryption key stored outside codebase
- Can be provided via environment variable or mounted file
- Supports secure key rotation

✅ **Error Recovery**
- Graceful error handling if key becomes invalid
- Clear error messages for troubleshooting

---

## 🔧 WSGI

Application entry point is:

```
wsgi:app
```

This makes the app compatible with:

* Gunicorn
* uWSGI
* Nginx reverse proxy stacks

---

## 📦 Requirements

```
Flask==3.0.0
Flask-SQLAlchemy==3.1.1
Flask-Login==0.6.3
Flask-Migrate==4.0.5
Flask-WTF==1.2.1
WTForms==3.1.1
cryptography==41.0.7
markupsafe==2.1.3
python-dotenv==1.0.0
gunicorn==21.2.0
Werkzeug==3.0.1
```

---

## 👥 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

**PRs should follow:**
- Secure coding practices
- Stateless container principles
- Configurable secrets — **never committed keys**
- Input validation on all endpoints
- CSRF protection on state-changing operations

---

## 🔧 Troubleshooting

### Container fails to start
- Check Docker logs: `docker-compose logs -f`
- Ensure `/data` directory has proper permissions
- Verify environment variables are set in `.env` file
- Check that `SECRET_KEY` is set

### Admin login not working
- Verify `ADMINU` and `ADMINP` environment variables match your login
- Check database isn't corrupted: `docker-compose down && docker-compose up --build`
- Ensure admin account was created (check logs for "Admin account created")

### Votes not being encrypted
- Check if encryption key exists: `docker-compose exec poll-app ls -la /data/poll_encryption_key`
- Verify file permissions on `/data` directory
- Check `POLL_ENCRYPTION_KEY` environment variable is set (if using env var instead of file)
- Review application logs for encryption errors

### Database errors
- Reset database by removing volume: `docker volume rm secure-polling-app_poll_data`
- Recreate container: `docker-compose up --build`
- **WARNING:** This deletes all data

### CSRF token errors
- Ensure all POST forms include CSRF token: `{{ csrf_token() }}`
- Check Flask-WTF is properly initialized
- Verify `SECRET_KEY` environment variable is set

### Password validation errors
- Password must be at least 8 characters
- Must include uppercase (A-Z), lowercase (a-z), and digit (0-9)
- Use the registration page to see validation errors

---

## 🚀 Quick Start Guide

### 1. Start the application
```bash
docker-compose up --build
```

### 2. Access the application
Open your browser to [http://localhost:5000](http://localhost:5000)

### 3. Create a user account
1. Click "Register"
2. Enter username (3+ characters)
3. Enter password (8+ characters with uppercase, lowercase, and digit)
4. Click "Register"

### 4. Login
- Enter your credentials
- Click "Login"

### 5. Create your first poll (admin only)
1. Click "Admin Dashboard"
2. Click "Create New Poll"
3. Enter question (5-300 characters)
4. Add 2-10 options
5. Set start/end times (optional)
6. Click "Create Poll"

### 6. Vote on a poll
1. Navigate to homepage
2. Click on a poll
3. Select your choice
4. Submit vote
5. Cannot vote twice on same poll

---

## 📊 Recent Changes (v1.1.0)

See [CHANGELOG.md](CHANGELOG.md) for detailed version history.

**Security Improvements:**
- ✅ CSRF protection enabled by default
- ✅ Password strength validation added
- ✅ Input validation and sanitization on all endpoints
- ✅ Admin authorization checks added to sensitive endpoints
- ✅ Thread-safe ledger operations
- ✅ Better error handling and logging

**Code Quality:**
- ✅ Removed redundant database queries
- ✅ Fixed race conditions in vote processing
- ✅ Improved IP address tracking logic
- ✅ Enhanced encryption error handling

---

## 🛡 License

MIT License

---

## 🙌 Credits

Built and iterated via architectural planning including:

* Encryption key security best practices
* Dockerized deployment
* Kubernetes-ready secret management
* Poll expiration logic
* Secure one-vote enforcement
* CSRF protection
* Input validation and sanitization

---

> Ready to deploy. Secure by design. Cloud-scalable.
