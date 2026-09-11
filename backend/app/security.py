# Copyright (c) 2026 tro. Contributors
# SPDX-License-Identifier: MIT
"""Cryptographic security utilities, password hashing, and JWT token operations."""

import base64
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import os
import secrets
from typing import Any, Dict, Optional

# Secret key for JWT signing; defaults to secure development secret
SECRET_KEY: str = os.getenv(
    "SECRET_KEY", "tro-secret-key-super-secure-olp-pmnm-2026-minh-bach-dien-nuoc"
)
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours


def _get_secret_key() -> str:
    """Retrieve current SECRET_KEY dynamically from environment or default."""
    return os.getenv("SECRET_KEY", SECRET_KEY)



def _base64url_encode(data: bytes) -> str:
    """Encode bytes using URL-safe base64 without padding per RFC 7515."""
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _base64url_decode(data_str: str) -> bytes:
    """Decode URL-safe base64 string, adding padding as necessary."""
    rem = len(data_str) % 4
    if rem > 0:
        data_str += "=" * (4 - rem)
    return base64.urlsafe_b64decode(data_str.encode("ascii"))


def get_password_hash(password: str) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 with cryptographically secure random salt."""
    if not isinstance(password, str):
        raise TypeError("Password must be a string")
    salt = secrets.token_hex(16)
    iterations = 100_000
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
        dklen=32,
    )
    return f"pbkdf2_sha256${iterations}${salt}${derived.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against hashed password string."""
    if not isinstance(plain_password, str) or not isinstance(hashed_password, str):
        return False
    if not plain_password or not hashed_password:
        return False

    # 1. PBKDF2-SHA256 standard format: pbkdf2_sha256$iterations$salt$hash
    if hashed_password.startswith("pbkdf2_sha256$"):
        parts = hashed_password.split("$")
        if len(parts) == 4:
            try:
                iterations = int(parts[1])
                salt = parts[2]
                expected_hash = parts[3]
                derived = hashlib.pbkdf2_hmac(
                    "sha256",
                    plain_password.encode("utf-8"),
                    salt.encode("utf-8"),
                    iterations,
                    dklen=32,
                )
                return hmac.compare_digest(derived.hex(), expected_hash)
            except Exception:
                return False
        return False

    # 2. Bcrypt hash format ($2a$, $2b$, $2y$)
    if hashed_password.startswith(("$2a$", "$2b$", "$2y$")):
        try:
            import bcrypt
            return bcrypt.checkpw(
                plain_password.encode("utf-8"), hashed_password.encode("utf-8")
            )
        except Exception:
            pass
        try:
            from passlib.context import CryptContext
            pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            return pwd_context.verify(plain_password, hashed_password)
        except Exception:
            pass

    # 3. Simple salt$hash format fallback
    if "$" in hashed_password:
        parts = hashed_password.split("$", 1)
        if len(parts) == 2:
            salt, expected_hash = parts
            derived = hashlib.sha256((salt + plain_password).encode("utf-8")).hexdigest()
            return hmac.compare_digest(derived, expected_hash)

    return False


def create_access_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """Create a signed RFC 7519 compliant JWT access token with HS256 algorithm."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta is not None:
        expire = now + expires_delta
        to_encode["exp"] = int(expire.timestamp())
    elif "exp" not in to_encode:
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode["exp"] = int(expire.timestamp())
    elif isinstance(to_encode["exp"], datetime):
        to_encode["exp"] = int(to_encode["exp"].timestamp())
    else:
        to_encode["exp"] = int(to_encode["exp"])

    if "iat" not in to_encode:
        to_encode["iat"] = int(now.timestamp())

    header = {"alg": ALGORITHM, "typ": "JWT"}
    header_json = json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8")
    payload_json = json.dumps(to_encode, separators=(",", ":"), default=str, sort_keys=True).encode("utf-8")

    header_b64 = _base64url_encode(header_json)
    payload_b64 = _base64url_encode(payload_json)
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")

    secret_key = _get_secret_key()
    signature = hmac.new(secret_key.encode("utf-8"), signing_input, hashlib.sha256).digest()
    sig_b64 = _base64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{sig_b64}"


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a JWT access token.

    Returns the payload dictionary if token is valid and active.
    Returns None if token is invalid, expired, malformed, or forged.
    """
    if not isinstance(token, str):
        return None

    parts = token.strip().split(".")
    if len(parts) != 3:
        return None

    header_b64, payload_b64, sig_b64 = parts

    try:
        # Verify HMAC-SHA256 signature
        secret_key = _get_secret_key()
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        expected_sig = hmac.new(secret_key.encode("utf-8"), signing_input, hashlib.sha256).digest()
        provided_sig = _base64url_decode(sig_b64)

        if not hmac.compare_digest(expected_sig, provided_sig):
            return None

        # Parse header
        header_bytes = _base64url_decode(header_b64)
        header = json.loads(header_bytes.decode("utf-8"))
        if not isinstance(header, dict) or header.get("alg") != ALGORITHM:
            return None

        # Parse payload
        payload_bytes = _base64url_decode(payload_b64)
        payload = json.loads(payload_bytes.decode("utf-8"))
        if not isinstance(payload, dict):
            return None

        now_ts = datetime.now(timezone.utc).timestamp()

        # Check Not Before (nbf)
        nbf = payload.get("nbf")
        if nbf is not None:
            if now_ts < float(nbf):
                return None  # Token not yet active

        # Check expiration (exp)
        exp = payload.get("exp")
        if exp is not None:
            if now_ts >= float(exp):
                return None  # Token expired

        return payload
    except Exception:
        return None

