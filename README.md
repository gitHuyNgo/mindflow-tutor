# 🧠 MindFlow Tutor

> Proactive Multimodal AI Learning Assistant with Voice — FastAPI backend + React/Vite frontend.

## 🛠 Tech Stack

| Layer       | Tech                                                |
| ----------- | --------------------------------------------------- |
| 🎨 Frontend | React 18, TypeScript, Vite, shadcn/ui, Tailwind CSS |
| ⚙️ Backend  | FastAPI, Python 3.11+, Uvicorn                      |
| 🗄️ Database | MongoDB (Motor async driver)                        |
| 🤖 AI       | OpenAI GPT-4o, ElevenLabs TTS, Tavily Search        |
| 📚 RAG      | LlamaIndex + ChromaDB                               |
| 🔐 Auth     | JWT + Email verification (SMTP)                     |
| 🎙️ Voice    | WebSocket real-time audio streaming                 |

## 📋 Prerequisites

- Python 3.11+
- Node.js 18+
- Docker (for MongoDB)

---

## 🚀 Quick Start

### 1. Start MongoDB

```bash
docker run -d -p 27017:27017 --name mongodb mongo
```

### 2. Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate        # Linux/macOS
# venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Start server (port 8000)
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

API docs available at: http://localhost:8000/docs

### 3. Frontend

```bash
cd client

# Install dependencies
npm install

# Start dev server (port 5173, proxies /api → localhost:8000)
npm run dev
```

App available at: http://localhost:5173

---

## 📁 Project Structure

```
mindflow-tutor/
├── backend/
│   ├── core/           # Prompts, config
│   ├── engines/        # Orchestrator, RAG, audio, vision
│   ├── persistence/    # Session memory
│   ├── providers/      # ElevenLabs, Tavily, Voice AI
│   ├── routers/        # Auth router
│   ├── schemas/        # Pydantic models
│   ├── server.py       # FastAPI app entrypoint
│   └── requirements.txt
├── client/
│   ├── src/
│   │   ├── components/ # UI components (shadcn)
│   │   ├── contexts/   # React context (auth, etc.)
│   │   ├── hooks/      # Custom hooks
│   │   ├── lib/        # Auth utilities
│   │   └── pages/      # Login, Index, StartLearning, VerifyEmail
│   ├── vite.config.ts
│   └── package.json
└── backend_test.py     # API integration tests
```

---

## 📡 API Overview

| Method | Endpoint                 | Description                      |
| ------ | ------------------------ | -------------------------------- |
| GET    | `/api/health`            | Health check                     |
| POST   | `/api/auth/register`     | Register new user                |
| POST   | `/api/auth/login`        | Login, returns JWT               |
| GET    | `/api/auth/verify-email` | Verify email token               |
| WS     | `/api/v1/voice`          | Real-time voice chat (WebSocket) |

Full interactive docs: http://localhost:8000/docs

---

## 🧪 Scripts

```bash
# Run API integration tests
python backend_test.py

# Frontend build for production
cd client && npm run build

# Frontend lint
cd client && npm run lint
```
