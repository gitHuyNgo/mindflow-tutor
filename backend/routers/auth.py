import os
import re
import uuid
import json
import base64
import smtplib
import asyncio
import logging
import unicodedata
from datetime import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jose import jwt, JWTError
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

# ── Crypto / JWT ──────────────────────────────────────────────────────────────

SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "change-me-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24 * 7      # 7 days
VERIFY_TOKEN_EXPIRE_HOURS = 1           # 1 hour

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _hash_password(plain: str) -> str:
    return pwd_ctx.hash(plain)


def _verify_password(plain: str, hashed: str) -> bool:
    return pwd_ctx.verify(plain, hashed)


def _create_jwt(data: dict, expire_hours: int) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(hours=expire_hours)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# ── Database helper ───────────────────────────────────────────────────────────

def _get_db():
    mongo_url = os.environ["MONGO_URL"]
    db_name   = os.environ["DB_NAME"]
    client    = AsyncIOMotorClient(mongo_url)
    return client[db_name]


# ── Email helper ──────────────────────────────────────────────────────────────


def _send_verification_email_sync(to_email: str, token: str):
    """Blocking SMTP call — run in thread pool."""
    # Read at call time so hot-reload / late env loading is never an issue
    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_pass = os.environ.get("SMTP_PASSWORD", "")
    app_url   = os.environ.get("APP_URL", "http://localhost:5173")

    if not smtp_user or not smtp_pass:
        logger.warning("SMTP not configured — skipping verification email")
        return

    logger.info(f"Sending verification email to {to_email} via {smtp_host}:{smtp_port}")

    verify_url = f"{app_url}/verify-email?token={token}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Verify your Mind Tutor account"
    msg["From"]    = f"Mind-Tutor support <{smtp_user}>"
    msg["To"]      = to_email

    html = f"""
    <div style="font-family:sans-serif;max-width:480px;margin:auto;padding:32px">
      <h2 style="color:#1a1a1a">Welcome to Mind Tutor!</h2>
      <p>Click the button below to verify your email address.</p>
      <a href="{verify_url}"
         style="display:inline-block;padding:12px 24px;background:#6c47ff;
                color:#fff;border-radius:8px;text-decoration:none;font-weight:600">
        Verify Email
      </a>
      <p style="margin-top:24px;font-size:13px;color:#666">
        Link expires in 1 hour. If you didn't sign up, ignore this email.
      </p>
    </div>
    """
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=15) as server:
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, to_email, msg.as_string())


async def _send_verification_email(to_email: str, token: str):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _send_verification_email_sync, to_email, token)


# ── Validation ────────────────────────────────────────────────────────────────

_BLOCKED_TLDS = {
    "test", "invalid", "example", "localhost", "local",
    "fake", "demo", "null", "undefined",
}

# Common one-char TLD typos people make (e.g. .con instead of .com)
_SUSPICIOUS_TLDS = {"con", "cmo", "ocm", "cpm", "vom", "cok"}


def _validate_full_name(name: str) -> str | None:
    """Return error message or None if valid."""
    if not name:
        return None  # optional field
    if len(name) > 50:
        return "Full name must be at most 50 characters"
    for ch in name:
        cat = unicodedata.category(ch)
        if not (cat.startswith("L") or ch in " '-"):
            return "Full name must contain only letters, spaces, hyphens, or apostrophes"
    return None


def _validate_email_tld(email: str) -> str | None:
    tld = email.rsplit(".", 1)[-1].lower()
    if len(tld) < 2:
        return "Email has an invalid domain extension"
    if tld in _BLOCKED_TLDS:
        return f"Email domain extension '.{tld}' is not allowed"
    if tld in _SUSPICIOUS_TLDS:
        return f"Email domain extension '.{tld}' looks like a typo — did you mean '.com'?"
    return None


def _validate_password(password: str, email: str, full_name: str) -> str | None:
    """Return error message or None if valid."""
    if len(password) < 8:
        return "Password must be at least 8 characters"
    if not re.search(r"[A-Z]", password):
        return "Password must contain at least one uppercase letter"
    if not re.search(r"\d", password):
        return "Password must contain at least one number"
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?`~]", password):
        return "Password must contain at least one special character"

    pw_lower = password.lower()

    # Too similar to email (check the local part before @)
    email_local = email.split("@")[0].lower()
    if len(email_local) >= 4 and email_local in pw_lower:
        return "Password is too similar to your email address"

    # Too similar to full name (each word >= 3 chars)
    if full_name:
        for part in full_name.lower().split():
            if len(part) >= 3 and part in pw_lower:
                return "Password is too similar to your full name"

    return None


# ── Schemas ───────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str = ""


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest):
    """Register a new user and send a verification email."""
    if err := _validate_full_name(body.full_name):
        raise HTTPException(status_code=400, detail=err)
    if err := _validate_email_tld(body.email):
        raise HTTPException(status_code=400, detail=err)
    if err := _validate_password(body.password, body.email, body.full_name):
        raise HTTPException(status_code=400, detail=err)

    db = _get_db()

    existing = await db.users.find_one({"email": body.email})
    if existing:
        if existing.get("is_verified"):
            raise HTTPException(status_code=409, detail="Email already registered")
        # Registered but not verified — tell frontend to prompt the user
        return JSONResponse(
            status_code=200,
            content={"pending_verification": True, "email": body.email},
        )

    verification_token = str(uuid.uuid4())

    user_doc = {
        "id":                     str(uuid.uuid4()),
        "email":                  body.email,
        "full_name":              body.full_name,
        "hashed_password":        _hash_password(body.password),
        "is_verified":            False,
        "verification_token":     verification_token,
        "verification_token_exp": (
            datetime.now(timezone.utc) + timedelta(hours=VERIFY_TOKEN_EXPIRE_HOURS)
        ).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    await db.users.insert_one(user_doc)

    # Send email (fire-and-forget — don't block if SMTP fails)
    try:
        await _send_verification_email(body.email, verification_token)
    except Exception as exc:
        logger.error(f"Failed to send verification email: {exc}")
        logger.warning(
            f"[DEV] Verify manually → {os.environ.get('APP_URL','http://localhost:5173')}/verify-email?token={verification_token}"
        )

    return {
        "message": "Registration successful. Please check your email to verify your account.",
        "email": body.email,
    }


@router.get("/verify-email")
async def verify_email(token: str):
    """Verify email using the token sent to the user."""
    db = _get_db()

    user = await db.users.find_one({"verification_token": token})
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")

    exp = datetime.fromisoformat(user["verification_token_exp"])
    if datetime.now(timezone.utc) > exp:
        raise HTTPException(status_code=400, detail="Verification token has expired")

    await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"is_verified": True, "verification_token": None}},
    )

    return {"message": "Email verified successfully. You can now log in."}


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    """Login and receive a JWT access token."""
    db = _get_db()

    user = await db.users.find_one({"email": body.email})
    if not user or not _verify_password(body.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.get("is_verified"):
        raise HTTPException(
            status_code=403,
            detail="Email not verified. Please check your inbox.",
        )

    access_token = _create_jwt(
        {"sub": user["id"], "email": user["email"]},
        expire_hours=ACCESS_TOKEN_EXPIRE_HOURS,
    )

    return TokenResponse(
        access_token=access_token,
        user={
            "id":        user["id"],
            "email":     user["email"],
            "full_name": user.get("full_name", ""),
        },
    )


# ── OAuth providers ───────────────────────────────────────────────────────────

GOOGLE_CLIENT_ID     = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")

FACEBOOK_CLIENT_ID     = os.environ.get("FACEBOOK_CLIENT_ID", "")
FACEBOOK_CLIENT_SECRET = os.environ.get("FACEBOOK_CLIENT_SECRET", "")


def _oauth_redirect_uri(provider: str) -> str:
    app_url = os.environ.get("APP_URL", "http://localhost:5173")
    return f"{app_url}/api/auth/{provider}/callback"


def _oauth_success_redirect(app_url: str, user_id: str, email: str, full_name: str) -> str:
    access_token = _create_jwt(
        {"sub": user_id, "email": email},
        expire_hours=ACCESS_TOKEN_EXPIRE_HOURS,
    )
    user_b64 = base64.urlsafe_b64encode(
        json.dumps({"id": user_id, "email": email, "full_name": full_name}).encode()
    ).decode()
    return f"{app_url}/oauth-callback?token={access_token}&user={user_b64}"


async def _upsert_oauth_user(email: str, full_name: str, provider: str) -> dict:
    db = _get_db()
    user = await db.users.find_one({"email": email})
    if user:
        if not user.get("is_verified"):
            await db.users.update_one({"_id": user["_id"]}, {"$set": {"is_verified": True}})
        return user
    doc = {
        "id":              str(uuid.uuid4()),
        "email":           email,
        "full_name":       full_name,
        "hashed_password": None,
        "is_verified":     True,
        "provider":        provider,
        "created_at":      datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(doc)
    return doc


# ── Google OAuth ──────────────────────────────────────────────────────────────

@router.get("/google")
async def google_login():
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=501, detail="Google OAuth is not configured")
    state = _create_jwt({"purpose": "oauth_state"}, expire_hours=1)
    params = {
        "client_id":     GOOGLE_CLIENT_ID,
        "redirect_uri":  _oauth_redirect_uri("google"),
        "response_type": "code",
        "scope":         "openid email profile",
        "state":         state,
        "access_type":   "online",
    }
    return RedirectResponse("https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params))


@router.get("/google/callback")
async def google_callback(code: str = "", state: str = "", error: str = ""):
    app_url = os.environ.get("APP_URL", "http://localhost:5173")
    if error or not code:
        return RedirectResponse(f"{app_url}/login?error=google_denied")
    try:
        jwt.decode(state, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return RedirectResponse(f"{app_url}/login?error=invalid_state")

    async with httpx.AsyncClient(timeout=10) as client:
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code":          code,
                "client_id":     GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri":  _oauth_redirect_uri("google"),
                "grant_type":    "authorization_code",
            },
        )
        if token_resp.status_code != 200:
            logger.error(f"Google token exchange failed: {token_resp.text}")
            return RedirectResponse(f"{app_url}/login?error=oauth_failed")

        access_token = token_resp.json().get("access_token", "")
        info_resp = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if info_resp.status_code != 200:
            return RedirectResponse(f"{app_url}/login?error=oauth_failed")
        info = info_resp.json()

    email     = info.get("email", "")
    full_name = info.get("name", "")
    if not email:
        return RedirectResponse(f"{app_url}/login?error=no_email")

    user = await _upsert_oauth_user(email, full_name, "google")
    return RedirectResponse(_oauth_success_redirect(app_url, user["id"], email, full_name))


# ── Facebook OAuth ────────────────────────────────────────────────────────────

@router.get("/facebook")
async def facebook_login():
    if not FACEBOOK_CLIENT_ID:
        raise HTTPException(status_code=501, detail="Facebook OAuth is not configured")
    state = _create_jwt({"purpose": "oauth_state"}, expire_hours=1)
    params = {
        "client_id":     FACEBOOK_CLIENT_ID,
        "redirect_uri":  _oauth_redirect_uri("facebook"),
        "response_type": "code",
        "scope":         "email,public_profile",
        "state":         state,
    }
    return RedirectResponse("https://www.facebook.com/v18.0/dialog/oauth?" + urlencode(params))


@router.get("/facebook/callback")
async def facebook_callback(code: str = "", state: str = "", error: str = ""):
    app_url = os.environ.get("APP_URL", "http://localhost:5173")
    if error or not code:
        return RedirectResponse(f"{app_url}/login?error=facebook_denied")
    try:
        jwt.decode(state, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return RedirectResponse(f"{app_url}/login?error=invalid_state")

    async with httpx.AsyncClient(timeout=10) as client:
        token_resp = await client.get(
            "https://graph.facebook.com/v18.0/oauth/access_token",
            params={
                "client_id":     FACEBOOK_CLIENT_ID,
                "client_secret": FACEBOOK_CLIENT_SECRET,
                "redirect_uri":  _oauth_redirect_uri("facebook"),
                "code":          code,
            },
        )
        if token_resp.status_code != 200:
            logger.error(f"Facebook token exchange failed: {token_resp.text}")
            return RedirectResponse(f"{app_url}/login?error=oauth_failed")

        access_token = token_resp.json().get("access_token", "")
        info_resp = await client.get(
            "https://graph.facebook.com/me",
            params={"fields": "id,name,email", "access_token": access_token},
        )
        if info_resp.status_code != 200:
            return RedirectResponse(f"{app_url}/login?error=oauth_failed")
        info = info_resp.json()

    email     = info.get("email", "")
    full_name = info.get("name", "")
    if not email:
        # Facebook may withhold email if user hasn't confirmed it
        return RedirectResponse(f"{app_url}/login?error=no_email")

    user = await _upsert_oauth_user(email, full_name, "facebook")
    return RedirectResponse(_oauth_success_redirect(app_url, user["id"], email, full_name))


# ── Profile ───────────────────────────────────────────────────────────────────

from typing import Optional as _Opt

class ProfileUpdateRequest(BaseModel):
    full_name: _Opt[str] = None
    avatar_url: _Opt[str] = None   # base64 data-URL or external URL


@router.patch("/profile")
async def update_profile(
    body: ProfileUpdateRequest,
    authorization: str = "",
):
    """Update display name and/or avatar. Requires Authorization: Bearer <token>."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    if body.full_name is not None:
        if err := _validate_full_name(body.full_name):
            raise HTTPException(status_code=400, detail=err)

    db = _get_db()
    update: dict = {}
    if body.full_name is not None:
        update["full_name"] = body.full_name
    if body.avatar_url is not None:
        if len(body.avatar_url) > 700_000:
            raise HTTPException(status_code=400, detail="Avatar image too large (max 500 KB)")
        update["avatar_url"] = body.avatar_url

    if not update:
        raise HTTPException(status_code=400, detail="Nothing to update")

    result = await db.users.find_one_and_update(
        {"id": user_id},
        {"$set": update},
        return_document=True,
    )
    if not result:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "id":         result["id"],
        "email":      result["email"],
        "full_name":  result.get("full_name", ""),
        "avatar_url": result.get("avatar_url", ""),
    }


# ── Email/password endpoints (existing) ──────────────────────────────────────

class ResendRequest(BaseModel):
    email: EmailStr


RESEND_COOLDOWN_SECONDS = 60


@router.post("/resend-verification")
async def resend_verification(body: ResendRequest):
    """Resend the verification email."""
    email = body.email
    db = _get_db()

    user = await db.users.find_one({"email": email})
    if not user:
        return {"message": "If that email exists, a new verification link has been sent."}

    if user.get("is_verified"):
        raise HTTPException(status_code=400, detail="Email is already verified")

    # Cooldown check
    last_resend = user.get("last_resend_at")
    if last_resend:
        elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(last_resend)).total_seconds()
        if elapsed < RESEND_COOLDOWN_SECONDS:
            wait = int(RESEND_COOLDOWN_SECONDS - elapsed)
            raise HTTPException(
                status_code=429,
                detail=f"Please wait {wait} seconds before requesting another email.",
            )

    new_token = str(uuid.uuid4())
    new_exp   = (datetime.now(timezone.utc) + timedelta(hours=VERIFY_TOKEN_EXPIRE_HOURS)).isoformat()

    await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {
            "verification_token":     new_token,
            "verification_token_exp": new_exp,
            "last_resend_at":         datetime.now(timezone.utc).isoformat(),
        }},
    )

    try:
        await _send_verification_email(email, new_token)
    except Exception as exc:
        logger.error(f"Failed to resend verification email: {exc}")
        logger.warning(
            f"[DEV] Verify manually → {os.environ.get('APP_URL','http://localhost:5173')}/verify-email?token={new_token}"
        )

    return {"message": "If that email exists, a new verification link has been sent."}
