from pathlib import Path
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, APIRouter
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

_ADMIN_SEED = {
    "full_name": "admin",
    "email":     "admin1234.test@gmail.com",
    "password":  "admin1234",
    "role":      "admin",
}


async def _seed_admin():
    existing = await db.users.find_one({"email": _ADMIN_SEED["email"]})
    if existing:
        return
    doc = {
        "id":                     str(uuid.uuid4()),
        "email":                  _ADMIN_SEED["email"],
        "full_name":              _ADMIN_SEED["full_name"],
        "hashed_password":        _pwd_ctx.hash(_ADMIN_SEED["password"]),
        "role":                   _ADMIN_SEED["role"],
        "is_verified":            True,
        "verification_token":     None,
        "verification_token_exp": None,
        "created_at":             datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(doc)
    logger.info(f"[seed] Admin account created: {_ADMIN_SEED['email']}")


@asynccontextmanager
async def lifespan(app: FastAPI):
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

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
