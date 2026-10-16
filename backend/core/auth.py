import os
import logging
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

logger = logging.getLogger(__name__)
_INSECURE_SECRETS = {"change-me-in-production", "secret", "default", "password", "123456", ""}

def validate_jwt_secret():
    """Verify that JWT_SECRET_KEY is safe. Raises RuntimeError if missing or insecure in production/staging."""
    secret = os.environ.get("JWT_SECRET_KEY", "")
    env = os.environ.get("ENVIRONMENT", os.environ.get("ENV", "development")).lower()
    is_prod = env in ("production", "prod", "staging")
    fail_on_default = os.environ.get("FAIL_ON_DEFAULT_SECRET", "").lower() in ("1", "true", "yes")

    if is_prod or fail_on_default:
        if not secret or secret.strip() in _INSECURE_SECRETS or len(secret.strip()) < 32:
            raise RuntimeError(
                "FATAL: Insecure or missing JWT_SECRET_KEY in production/staging environment. "
                "Set a cryptographically strong secret (>= 32 chars) in the JWT_SECRET_KEY environment variable."
            )
    elif not secret or secret.strip() in _INSECURE_SECRETS:
        logger.warning("JWT_SECRET_KEY is not set or uses default; tokens are signed with an insecure key in dev")

_DEFAULT_SECRET = "change-me-in-production"
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", _DEFAULT_SECRET)
ALGORITHM = "HS256"

# Validate at module load if fail-fast is explicitly requested or in production
if os.environ.get("FAIL_ON_DEFAULT_SECRET", "").lower() in ("1", "true", "yes") or os.environ.get("ENVIRONMENT", "").lower() in ("production", "prod"):
    validate_jwt_secret()

security = HTTPBearer(auto_error=False)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing subject claim",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Strictly reject non-access tokens (e.g. exchange codes or state tokens)
        purpose = payload.get("purpose")
        token_type = payload.get("type", "access")
        if purpose in ("oauth_exchange", "oauth_state") or token_type != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type: exchange codes or state tokens cannot be used as access tokens",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return {
            "id": user_id,
            "email": payload.get("email", ""),
            "raw": payload,
        }
    except JWTError as e:
        logger.warning(f"JWT verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """Enforce authentication via Authorization: Bearer <token>."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return decode_token(credentials.credentials)


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[dict]:
    """Extract user if bearer token is present and valid; otherwise None."""
    if not credentials or not credentials.credentials:
        return None
    try:
        return decode_token(credentials.credentials)
    except HTTPException:
        return None
