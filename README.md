# MindFlow Tutor

Proactive Multimodal AI Learning Assistant — FastAPI backend + React/Vite frontend.

Detects distraction and confusion via webcam in real time, then proactively helps the user refocus or clarifies confusing material using AI.

## Tech Stack

| Layer    | Tech                                                |
| -------- | --------------------------------------------------- |
| Frontend | React 18, TypeScript, Vite, shadcn/ui, Tailwind CSS |
| Backend  | FastAPI, Python 3.11, Uvicorn                       |
| Database | MongoDB (Motor async driver)                        |
| AI       | OpenAI GPT-4o, ElevenLabs TTS, Tavily Search        |
| RAG      | LlamaIndex + ChromaDB                               |
| Auth     | JWT + Email verification (SMTP/Gmail)               |
| Vision   | MediaPipe, OpenCV, hsemotion (EfficientNet-B0)      |

---

## Prerequisites

- **Conda** (recommended) or Python 3.11+
- **Node.js 18+**
- **Docker** (for MongoDB)
- API keys: OpenAI, ElevenLabs, Tavily, LlamaParse (see `.env` section below)

---

## 1. Start MongoDB

```bash
docker run -d -p 27017:27017 --name mongodb mongo
```

---

## 2. Backend Setup

### 2a. Create conda environment

```bash
conda create -n mind-tutor python=3.11 -y
conda activate mind-tutor
```

### 2b. Install dependencies

```bash
cd backend
pip install -r requirements-ai.txt
pip install -r requirements-web.txt
```

> **Note:** `requirements-ai.txt` must be installed first — it pins `numpy<2` and vision packages (torch, mediapipe, hsemotion) that web dependencies may conflict with if installed in the wrong order. Install may take a few minutes.


### 2dc Configure environment

```bash
cp .env.example .env
# Edit .env with your keys
```

Required `.env` values:

```env
# OpenAI
OPENAI_API_KEY=sk-...

# ElevenLabs (text-to-speech)
ELEVENLABS_API_KEY=...
ELEVENLABS_VOICE_ID=...

# Tavily (web search)
TAVILY_API_KEY=tvly-...

# LlamaParse (PDF parsing)
LLAMA_CLOUD_API_KEY=llx-...

# MongoDB
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=mindflow

# JWT
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Gmail SMTP (for email verification)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-gmail@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx   # Gmail App Password (16 chars)
EMAIL_FROM=your-gmail@gmail.com
FRONTEND_URL=http://localhost:5173
```


### 2e. Start backend server

```bash
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 3. Frontend Setup

```bash
cd client
npm install
npm run dev
```

App: [http://localhost:5173](http://localhost:5173)

The Vite dev server proxies `/api` → `http://localhost:8000` automatically.

---

## Project Structure

```
mindflow-tutor/
├── backend/
│   ├── core/               # Prompts, config
│   ├── engines/
│   │   ├── attention_system/   # Distraction detection (head pose + eye tracking)
│   │   ├── confusion_system/   # Confusion detection (emotion recognition)
│   │   └── combined_detector_engine.py
│   ├── persistence/        # Session memory (ChromaDB)
│   ├── providers/          # OpenAI, ElevenLabs, Tavily
│   ├── routers/            # API route handlers
│   ├── schemas/            # Pydantic models
│   ├── server.py           # FastAPI entrypoint
│   └── requirements.txt
├── client/
│   ├── src/
│   │   ├── components/     # UI components (shadcn/ui)
│   │   ├── contexts/       # Auth context
│   │   ├── hooks/          # Custom hooks
│   │   ├── lib/            # Auth utilities
│   │   └── pages/          # Login, Session, StartLearning, VerifyEmail
│   ├── vite.config.ts
│   └── package.json
└── backend_test.py         # API integration tests
```

---

## API Overview

| Method | Endpoint                        | Description                        |
| ------ | ------------------------------- | ---------------------------------- |
| GET    | `/api/health`                   | Health check                       |
| POST   | `/api/auth/register`            | Register new user                  |
| POST   | `/api/auth/login`               | Login, returns JWT                 |
| GET    | `/api/auth/verify-email`        | Verify email token                 |
| POST   | `/api/v1/ask`                   | Ask a question (RAG + AI)          |
| POST   | `/api/v1/process-trigger`       | Confusion trigger (screen + AI)    |
| POST   | `/api/v1/detect`                | Webcam frame analysis              |
| POST   | `/api/v1/utils/classify-intent` | Semantic intent classification     |
| POST   | `/api/v1/documents/upload`      | Upload PDF for RAG                 |
| WS     | `/api/v1/voice`                 | Real-time voice chat (WebSocket)   |

Full interactive docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---
## Scripts

```bash
# Run API integration tests
python backend_test.py

# Frontend production build
cd client && npm run build

# Frontend lint
cd client && npm run lint
```
