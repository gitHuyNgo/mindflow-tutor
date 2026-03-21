import os
import re
import uuid
import smtplib
import asyncio
import logging
import unicodedata
from datetime import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
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
