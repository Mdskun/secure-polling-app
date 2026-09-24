#!/bin/bash

KEY_PATH="/data/poll_encryption_key"
# Create directory if missing
mkdir -p $(dirname "$KEY_PATH")

# If a key is supplied via the POLL_ENCRYPTION_KEY env var (K8s Secret,
# secret managers, CI), prefer it and skip file generation so the env value
# is never shadowed by a stale file.
if [ -n "$POLL_ENCRYPTION_KEY" ]; then
    echo "Using POLL_ENCRYPTION_KEY from environment."
# If no key exists, generate a new one
elif [ ! -f "$KEY_PATH" ]; then
    echo "Generating new encryption key..."
    python3 - <<EOF
from cryptography.fernet import Fernet
key = Fernet.generate_key()
open("$KEY_PATH", "wb").write(key)
EOF
else
    echo "Using existing encryption key."
fi

# Initialize database tables (only once, before workers start)
echo "Initializing database tables..."
python init_db.py

# Create admin user if not exists
if [ ! -f "/data/admin_created" ]; then
    echo "Creating admin user..."
    python create_admin.py
    touch /data/admin_created
fi

echo "Starting Flask app..."
exec "$@"