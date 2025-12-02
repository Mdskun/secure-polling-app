import os
from cryptography.fernet import Fernet
from hashlib import sha256
from datetime import datetime
import json
from dotenv import load_dotenv
load_dotenv()

KEY_FILE_PATH = "/data/poll_encryption_key"
LEDGER_PATH = "/data/ledger.jsonl"

def load_key():
    """
    Load encryption key from (highest priority -> lowest):
    1. Kubernetes/Docker Secrets file
    2. Environment variable
    3. Create new key if none exists (only in dev)
    """

    # 1️⃣ Try Kubernetes/Docker Secrets file
    if os.path.exists(KEY_FILE_PATH):
        with open(KEY_FILE_PATH, "rb") as file:
            key = file.read().strip()
            return key

    # 2️⃣ Try environment variable
    key = os.getenv("POLL_ENCRYPTION_KEY")
    if key:
        return key.encode()

    # 3️⃣ Generate new key (only allowed in development)
    if os.getenv("FLASK_ENV") == "development":
        raise RuntimeError("Environment not configured")

    raise RuntimeError("❌ No encryption key found! Set a key via env var or secret file.")

CIPHER = Fernet(load_key())

def encrypt_vote(value: str) -> bytes:
    return CIPHER.encrypt(value.encode())


def decrypt_vote(value: bytes) -> str:
    return CIPHER.decrypt(value).decode()

def _hash_bytes(b: bytes) -> str:
    return sha256(b).hexdigest()

def _hash_str(s: str) -> str:
    return sha256(s.encode()).hexdigest()

def _last_block():
    """Return last block dict or None."""
    if not os.path.exists(LEDGER_PATH):
        return None
    with open(LEDGER_PATH, "rb") as f:
        try:
            f.seek(0, os.SEEK_END)
            if f.tell() == 0:
                return None
        except:
            pass
    # read last line (efficient)
    with open(LEDGER_PATH, "r", encoding="utf-8") as f:
        lines = f.read().strip().splitlines()
        if not lines:
            return None
        return json.loads(lines[-1])

def append_ledger_entry(encrypted_vote: bytes, poll_id: int, option_id: int, user_id: int | None, ip_address: str | None):
    """
    Create a ledger block for a vote and append to ledger.jsonl
    Block structure:
    {
      index: int,
      timestamp: ISO8601 UTC,
      poll_id: int,
      option_id: int,
      user_id: int | null,
      ip_address: str | null,
      vote_hash: sha256(encrypted_vote),
      prev_hash: str | null,
      block_hash: sha256(index + timestamp + vote_hash + prev_hash)
    }
    """
    last = _last_block()
    index = last["index"] + 1 if last else 1
    timestamp = datetime.utcnow().isoformat() + "Z"
    vote_hash = _hash_bytes(encrypted_vote)
    prev_hash = last["block_hash"] if last else None

    # Compose block string to sign/hash deterministically
    block_string = f"{index}|{timestamp}|{poll_id}|{option_id}|{user_id}|{ip_address}|{vote_hash}|{prev_hash}"
    block_hash = _hash_str(block_string)

    block = {
        "index": index,
        "timestamp": timestamp,
        "poll_id": poll_id,
        "option_id": option_id,
        "user_id": user_id,
        "ip_address": ip_address,
        "vote_hash": vote_hash,
        "prev_hash": prev_hash,
        "block_hash": block_hash
    }

    # Append as JSON line
    with open(LEDGER_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(block) + "\n")

    return block

def verify_ledger():
    """Verify chain integrity. Returns (True, None) if ok else (False, reason)."""
    if not os.path.exists(LEDGER_PATH):
        return True, None
    prev_hash = None
    index = 0
    with open(LEDGER_PATH, "r", encoding="utf-8") as f:
        for line in f:
            index += 1
            try:
                block = json.loads(line)
            except json.JSONDecodeError:
                return False, f"Invalid JSON at line {index}"
            # Recompute block_hash
            block_string = f"{block['index']}|{block['timestamp']}|{block['poll_id']}|{block['option_id']}|{block.get('user_id')}|{block.get('ip_address')}|{block['vote_hash']}|{block['prev_hash']}"
            expected_hash = _hash_str(block_string)
            if block["block_hash"] != expected_hash:
                return False, f"Block hash mismatch at index {block['index']}"
            if block["prev_hash"] != prev_hash:
                return False, f"Prev hash mismatch at index {block['index']}"
            prev_hash = block["block_hash"]
    return True, None