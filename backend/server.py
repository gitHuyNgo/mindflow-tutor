from pathlib import Path
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, APIRouter
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
from datetime import datetime, timezone
import os
import uuid
import logging

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env', override=True)

from routers.auth import router as auth_router
from routers.voice import router as voice_router
from routers.ai import router as ai_router
from routers.tts import router as tts_router
from routers.documents import router as documents_router
from routers.conversations import router as conversations_router
from routers.search import router as search_router
from routers.system import router as system_router

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def _seed_admin():
    """Create the admin account from ADMIN_EMAIL / ADMIN_PASSWORD, if both are set."""
    email = os.environ.get("ADMIN_EMAIL")
    password = os.environ.get("ADMIN_PASSWORD")
    if not email or not password:
        return
    existing = await db.users.find_one({"email": email})
    if existing:
        return
    doc = {
        "id":                     str(uuid.uuid4()),
        "email":                  email,
        "full_name":              "admin",
        "hashed_password":        _pwd_ctx.hash(password),
        "role":                   "admin",
        "is_verified":            True,
        "verification_token":     None,
        "verification_token_exp": None,
        "created_at":             datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(doc)
    logger.info(f"[seed] Admin account created: {email}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    from core.auth import validate_jwt_secret
    validate_jwt_secret()
    await _seed_admin()
    # Inject MongoDB into session memory so messages are persisted
    from persistence.session_memory import get_session_memory
    get_session_memory().set_db(db)
    yield
    client.close()


app = FastAPI(
    title="MindFlow Tutor API",
    description="Proactive Multimodal AI Learning Assistant with Voice",
    version="2.0.0",
    lifespan=lifespan
)

api_router = APIRouter(prefix="/api")
api_router.include_router(auth_router)
api_router.include_router(system_router)
api_router.include_router(voice_router)
api_router.include_router(ai_router)
api_router.include_router(tts_router)
api_router.include_router(documents_router)
api_router.include_router(conversations_router)
api_router.include_router(search_router)
app.include_router(api_router)

# Expose /metrics and /health at the root level for standard Prometheus/k8s scrapers
from monitoring.metrics import MetricsMiddleware, export_prometheus_text
from fastapi.responses import Response

@app.get("/metrics", include_in_schema=False)
async def prometheus_metrics():
    return Response(content=export_prometheus_text(), media_type="text/plain; version=0.0.4; charset=utf-8")

app.add_middleware(MetricsMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Serve React static files (production build) ──────────────────────────────
_STATIC_DIR = ROOT_DIR / "static"
if _STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(_STATIC_DIR / "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        """Catch-all: serve React index.html for any non-API route."""
        index = _STATIC_DIR / "index.html"
        return FileResponse(str(index))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
