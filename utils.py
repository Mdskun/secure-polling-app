import os
from cryptography.fernet import Fernet, InvalidToken
from hashlib import sha256
from datetime import datetime
import json
from dotenv import load_dotenv
import logging
from threading import Lock

load_dotenv()

logger = logging.getLogger(__name__)

KEY_FILE_PATH = "/data/poll_encryption_key"
LEDGER_PATH = "/data/ledger.jsonl"

# Thread lock for ledger file operations (prevent race conditions)
LEDGER_LOCK = Lock()

def load_key():
    """
    Load encryption key from (highest priority -> lowest):
    1. Kubernetes/Docker Secrets file
    2. Environment variable
    3. Fail with error (no generation)
    """
    # 1️⃣ Try Kubernetes/Docker Secrets file
    if os.path.exists(KEY_FILE_PATH):
        try:
            with open(KEY_FILE_PATH, "rb") as file:
                key = file.read().strip()
                if key:
                    return key
        except IOError as e:
            logger.error(f"Failed to read encryption key file: {e}")
            raise RuntimeError("Failed to read encryption key file.")

    # 2️⃣ Try environment variable
    key = os.getenv("POLL_ENCRYPTION_KEY")
    if key:
        try:
            return key.encode() if isinstance(key, str) else key
        except Exception as e:
            logger.error(f"Failed to encode encryption key: {e}")
            raise RuntimeError("Invalid encryption key format.")

    # 3️⃣ No key found - fail
    raise RuntimeError("❌ No encryption key found! Set POLL_ENCRYPTION_KEY env var or mount key file at /data/poll_encryption_key")

try:
    CIPHER = Fernet(load_key())
except Exception as e:
    logger.error(f"Failed to initialize cipher: {e}")
    CIPHER = None

def encrypt_vote(value: str) -> bytes:
    """
    Encrypt a vote value using Fernet symmetric encryption.
    
    Args:
        value: The vote value to encrypt (typically option ID)
    
    Returns:
        Encrypted bytes
    
    Raises:
        RuntimeError: If cipher is not initialized
    """
    if CIPHER is None:
        raise RuntimeError("Encryption cipher not initialized")
    
    try:
        return CIPHER.encrypt(value.encode())
    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        raise RuntimeError("Failed to encrypt vote")

def decrypt_vote(value: bytes) -> str:
    """
    Decrypt a vote value using Fernet symmetric encryption.
    
    Args:
        value: The encrypted vote bytes
    
    Returns:
        Decrypted string value
    
    Raises:
        RuntimeError: If cipher is not initialized or decryption fails
    """
    if CIPHER is None:
        raise RuntimeError("Encryption cipher not initialized")
    
    try:
        return CIPHER.decrypt(value).decode()
    except InvalidToken:
        logger.error("Invalid token during decryption - key may have changed")
        raise RuntimeError("Failed to decrypt vote - invalid token")
    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        raise RuntimeError("Failed to decrypt vote")

def _hash_bytes(b: bytes) -> str:
    """Generate SHA256 hash of bytes."""
    return sha256(b).hexdigest()

def _hash_str(s: str) -> str:
    """Generate SHA256 hash of string."""
    return sha256(s.encode()).hexdigest()

def _last_block():
    """
    Return last block dict from ledger or None if empty/missing.
    Thread-safe with LEDGER_LOCK.
    """
    if not os.path.exists(LEDGER_PATH):
        return None
    
    with LEDGER_LOCK:
        try:
            with open(LEDGER_PATH, "r", encoding="utf-8") as f:
                lines = f.read().strip().splitlines()
                if not lines:
                    return None
                return json.loads(lines[-1])
        except (IOError, json.JSONDecodeError) as e:
            logger.error(f"Error reading last ledger block: {e}")
            return None

def append_ledger_entry(
    encrypted_vote: bytes,
    poll_id: int,
    option_id: int,
    user_id: int | None,
    ip_address: str | None
) -> dict:
    """
    Create a ledger block for a vote and append to ledger.jsonl
    Thread-safe with LEDGER_LOCK to prevent race conditions.
    
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
    with LEDGER_LOCK:
        try:
            last = _last_block()
            index = last["index"] + 1 if last else 1
            timestamp = datetime.utcnow().isoformat() + "Z"
            vote_hash = _hash_bytes(encrypted_vote)
            prev_hash = last["block_hash"] if last else None

            # Compose block string to hash deterministically
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

            # Ensure directory exists
            os.makedirs(os.path.dirname(LEDGER_PATH) or "/data", exist_ok=True)

            # Append as JSON line
            with open(LEDGER_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(block) + "\n")

            return block
        except Exception as e:
            logger.error(f"Failed to append ledger entry: {e}")
            raise RuntimeError("Failed to record vote in ledger")

def verify_ledger() -> tuple[bool, str | None]:
    """
    Verify blockchain-style chain integrity.
    Returns (is_valid, error_reason)
    """
    if not os.path.exists(LEDGER_PATH):
        return True, None
    
    with LEDGER_LOCK:
        try:
            prev_hash = None
            index = 0
            
            with open(LEDGER_PATH, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    if not line.strip():  # Skip empty lines
                        continue
                    
                    try:
                        block = json.loads(line)
                    except json.JSONDecodeError:
                        return False, f"Invalid JSON at line {line_num}"
                    
                    # Validate required fields
                    required_fields = ["index", "timestamp", "poll_id", "option_id", "vote_hash", "block_hash"]
                    for field in required_fields:
                        if field not in block:
                            return False, f"Missing field '{field}' at line {line_num}"
                    
                    # Recompute block_hash
                    block_string = (
                        f"{block['index']}|{block['timestamp']}|{block['poll_id']}|"
                        f"{block['option_id']}|{block.get('user_id')}|{block.get('ip_address')}|"
                        f"{block['vote_hash']}|{block['prev_hash']}"
                    )
                    expected_hash = _hash_str(block_string)
                    
                    if block["block_hash"] != expected_hash:
                        return False, f"Block hash mismatch at index {block['index']}"
                    
                    if block["prev_hash"] != prev_hash:
                        return False, f"Chain broken at index {block['index']} - prev_hash mismatch"
                    
                    prev_hash = block["block_hash"]
                    index += 1
            
            return True, None
        except Exception as e:
            logger.error(f"Ledger verification error: {e}")
            return False, f"Verification error: {str(e)}"
