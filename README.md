# SPM Chatbot — Architecture & Workflow

## 1. Overview

SPM Chatbot is a full-stack AI chat application with a **FastAPI** backend and a **React** frontend. It uses **Ollama** (local LLM) for AI responses with a **Summarisation + Sliding Window** memory approach to manage context within the LLM's context window.

---

## 2. Directory Structure

```
SPM-Chatbot/
├── backend/
│   ├── .env                  # Environment variables
│   ├── .venv/                # Python virtual environment
│   ├── main.py               # FastAPI app, all HTTP endpoints
│   ├── database.py           # SQLAlchemy models, DB engine, migrations
│   ├── auth.py               # JWT auth, password hashing, RBAC
│   ├── llm.py                # Ollama API client
│   ├── context_builder.py    # Prompt assembly + summarisation logic
│   ├── schemas.py            # Pydantic request/response models
│   └── requirements.txt      # Python dependencies
├── frontend/
│   ├── .env                  # React environment variables
│   ├── src/
│   │   ├── App.js            # Root component, routing
│   │   ├── api.js            # Axios client for backend calls
│   │   ├── App.css           # All styles
│   │   └── components/
│   │       ├── auth.js       # Login/Register form
│   │       └── chat.js       # Chat UI (sidebar, messages, input)
│   └── package.json
├── docker-compose.yml        # PostgreSQL database
├── .gitignore
└── ARCHITECTURE.md
```

---

## 3. Backend Architecture

### 3.1 Technology Stack

| Component | Technology |
|---|---|
| Web framework | FastAPI |
| ORM | SQLAlchemy 2.0 |
| Database | PostgreSQL 15 (via Docker) |
| Auth | JWT (python-jose) + bcrypt (passlib) |
| LLM client | httpx (sync) |
| Validation | Pydantic v2 |

### 3.2 Database Models (`database.py`)

```
User
├── id            (PK)
├── username      (unique)
├── hashed_password
└── role          ("user" | "admin")

ConversationSession
├── id            (PK)
├── user_id       (FK → users.id)
├── title
├── created_at
├── summary           (LLM-generated summary, nullable)
└── summary_msg_count (tracks how many msgs are summarised)

Conversation
├── id            (PK)
├── user_id       (FK → users.id)
├── session_id    (FK → conversation_sessions.id)
├── role          ("user" | "assistant")
├── content
└── timestamp
```

### 3.3 Authentication (`auth.py`)

- Passwords hashed with **bcrypt** via passlib
- JWT tokens contain `sub` (username) and `role` claims
- `get_current_user` dependency validates Bearer token on every protected endpoint
- `require_role(role)` factory for RBAC (e.g., admin-only endpoints)

### 3.4 LLM Integration (`llm.py`)

- Sends `POST /api/chat` to local Ollama at `http://localhost:11434`
- Model: `llama3.2:3b` (configurable via `.env`)
- Sync HTTP client with 60s timeout
- Graceful error handling: `OllamaUnavailableError`, 404 model-not-found, generic HTTP errors

### 3.5 Context Management (`context_builder.py`)

Uses **Summarisation + Sliding Window** (Approach 3):

```
Prompt sent to LLM:
┌─ SYSTEM: "You are a helpful assistant..."
├─ ASSISTANT: "Here is a summary of our earlier conversation: ..."  ← if summary exists
├─ USER: msg N-9
├─ ASSISTANT: msg N-8                                                ← sliding window
├─ ...                                                                (last 10 messages)
├─ USER: msg N-1
└─ USER: new message (current)
```

**Summarisation trigger:**
- Total messages > 20 (`SUMMARY_THRESHOLD`)
- Messages outside window - already summarised >= 3 (`SUMMARY_REFRESH_GAP`)
- When triggered: LLM summarises all messages outside the window into 3-5 sentences
- Summary stored in `conversation_sessions.summary` and prepended to future prompts

### 3.6 API Endpoints (`main.py`)

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/register` | No | Register new user |
| POST | `/api/login` | No | Login, returns JWT + username + role |
| GET | `/api/me` | JWT | Get current user info |
| GET | `/api/sessions` | JWT | List user's sessions |
| POST | `/api/sessions` | JWT | Create new session |
| PUT | `/api/sessions/{id}` | JWT | Rename session |
| GET | `/api/sessions/{id}/messages` | JWT | Get messages for a session |
| POST | `/api/chat` | JWT | Send message, get AI response |
| DELETE | `/api/history` | JWT | Delete all user data |

---

## 4. Frontend Architecture

### 4.1 Technology Stack

| Component | Technology |
|---|---|
| Framework | React 19 |
| Routing | react-router-dom v7 |
| HTTP client | axios |
| Markdown | react-markdown + remark-gfm + rehype-highlight |

### 4.2 Routing

- `/` — Auth page (login/register)
- `/:username` — Chat page for a specific user
- Unauthenticated users are redirected to `/`
- URL username is validated against the stored username; mismatches auto-redirect

### 4.3 Components

**`App.js`** — Root component, manages auth state and routing.

```
App
├── Auth (at /)
│   ├── Login form
│   └── Register form
└── Chat (at /:username)
    ├── Sidebar
    │   ├── Session list (double-click to rename)
    │   └── "New conversation" button
    ├── Chat header
    │   ├── Session title (double-click to rename)
    │   └── User badge + Logout
    ├── Messages area
    │   ├── User messages (plain text)
    │   └── Assistant messages (Markdown rendered)
    └── Input form
```

### 4.4 State Management

No external state library — uses React `useState` and `useEffect`:
- `sessions[]` — fetched from `GET /api/sessions`
- `messages[]` — fetched from `GET /api/sessions/{id}/messages`
- `activeSessionId` — currently selected session
- Optimistic message insertion: user message shown immediately on send

---

## 5. Workflow / Data Flow

### 5.1 Authentication Flow

```
User → / (Auth page)
  → Enter username + password
  → POST /api/login (or /register)
  → Backend verifies/creates user, returns { access_token, username, role }
  → Frontend stores token + username in localStorage
  → Navigate to /:username
```

### 5.2 Chat Message Flow

```
User types message → handleSend()
  │
  ├─ 1. Optimistically add user message to local state (immediate display)
  │
  ├─ 2. If no active session → POST /api/sessions → create session
  │
  ├─ 3. POST /api/chat
  │      ├─ Save user message to DB
  │      ├─ build_context(db, session_id, message)
  │      │     ├─ maybe_update_summary() — check & generate if needed
  │      │     ├─ Fetch last 10 messages (sliding window)
  │      │     ├─ Fetch session summary (if exists)
  │      │     └─ Assemble prompt array
  │      ├─ call_ollama(prompt) → POST localhost:11434/api/chat
  │      ├─ Save assistant response to DB
  │      ├─ If first exchange → background task generates title via LLM
  │      └─ Return { user_message, assistant_message, session_id }
  │
  ├─ 4. loadMessages(sessionId) — fetch full history from server
  │
  └─ 5. loadSessions() — refresh sidebar
```

### 5.3 Title Generation Flow

```
First message in a new session:
  → Background task (after response is returned)
  → call_ollama([system prompt + user message + AI response])
  → LLM returns concise title (max 6 words)
  → UPDATE conversation_sessions SET title = ...
```

### 5.4 Summarisation Flow

```
When total messages > 20 AND outside-window gap >= 3:
  → Fetch messages[0 .. total - 10] (outside sliding window)
  → Format as transcript
  → call_ollama(["Summarise in 3-5 sentences...", transcript])
  → Store summary in conversation_sessions.summary
  → Set summary_msg_count = total - 10
```

---

## 6. RBAC (Role-Based Access Control)

| Role | Permissions |
|---|---|
| `user` | Access own sessions & messages only |
| `admin` | Same (extendable via `require_role("admin")` factory) |

All data endpoints enforce ownership by filtering queries with `current_user.id`.

---

## 7. Environment Setup

### Prerequisites

- Python 3.12+
- Node.js 18+
- Docker & Docker Compose (for PostgreSQL)
- Ollama (with `llama3.2:3b` model)

### 7.1 Database

```bash
# Start PostgreSQL
docker compose up -d
```

### 7.2 Backend

```bash
cd backend

# Create and activate virtual environment (if not present)
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment (edit .env if your settings differ from defaults)

# Start the backend
.venv/bin/uvicorn main:app --reload --port 8000
```

### 7.3 Frontend

```bash
cd frontend

# Install dependencies
npm install

# Configure environment (optional — defaults work for local dev)
# Edit frontend/.env if needed

# Start the frontend
npm start
```

### 7.4 Ollama

```bash
# Start Ollama service
ollama serve

# In another terminal, pull the model
ollama pull llama3.2:3b

# Verify it's running
curl http://localhost:11434/api/tags
```

### 7.5 Verify Everything

```bash
# 1. Check database is up
docker ps | grep chatbot-db

# 2. Check Ollama is running
curl http://localhost:11434/api/tags

# 3. Start backend (port 8000)
cd backend && .venv/bin/uvicorn main:app --reload --port 8000

# 4. Start frontend (port 3000)
cd frontend && npm start

# 5. Open http://localhost:3000 in browser
# 6. Register a new account and start chatting
```

### 7.6 Environment Variables Reference

#### Backend (`backend/.env`)

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql://chatbot_user:chatbot_pass@localhost:5433/chatbot_db` | PostgreSQL connection string |
| `SECRET_KEY` | `your-secret-key-change-in-production` | JWT signing key |
| `ALGORITHM` | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | JWT token expiry |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `llama3.2:3b` | LLM model name |
| `OLLAMA_TIMEOUT` | `60.0` | HTTP timeout in seconds |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated allowed origins |

#### Frontend (`frontend/.env`)

| Variable | Default | Description |
|---|---|---|
| `REACT_APP_API_BASE` | `http://localhost:8000/api` | Backend API base URL |
