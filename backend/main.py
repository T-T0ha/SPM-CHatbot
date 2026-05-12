from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from database import init_db, get_db, User, Conversation, ConversationSession
from auth import get_password_hash, authenticate_user, create_access_token, get_current_user
from schemas import (
    UserCreate,
    UserLogin,
    Token,
    ChatRequest,
    ChatHistoryResponse,
    ChatSessionCreate,
    ChatSessionResponse,
)
from datetime import timedelta
from typing import List

app = FastAPI()

# CORS for React frontend (running on port 3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize DB on startup
@app.on_event("startup")
def startup():
    init_db()

# ---------- AUTH ENDPOINTS ----------
@app.post("/api/register", response_model=Token)
def register(user: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == user.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already registered")
    hashed = get_password_hash(user.password)
    new_user = User(username=user.username, hashed_password=hashed)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/login", response_model=Token)
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = authenticate_user(db, user.username, user.password)
    if not db_user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

# ---------- CHAT HISTORY ENDPOINTS ----------
def ensure_default_session(db: Session, user_id: int) -> ConversationSession:
    session = (
        db.query(ConversationSession)
        .filter(ConversationSession.user_id == user_id)
        .order_by(ConversationSession.created_at)
        .first()
    )
    if session is None:
        session = ConversationSession(user_id=user_id, title="New conversation")
        db.add(session)
        db.commit()
        db.refresh(session)

    orphan_count = (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id, Conversation.session_id.is_(None))
        .count()
    )
    if orphan_count:
        db.query(Conversation).filter(
            Conversation.user_id == user_id, Conversation.session_id.is_(None)
        ).update({Conversation.session_id: session.id})
        db.commit()
    return session

@app.get("/api/sessions", response_model=List[ChatSessionResponse])
def list_sessions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ensure_default_session(db, current_user.id)

    stats_subq = (
        db.query(
            Conversation.session_id.label("session_id"),
            func.max(Conversation.timestamp).label("last_message_at"),
            func.count(Conversation.id).label("message_count"),
        )
        .filter(Conversation.user_id == current_user.id)
        .group_by(Conversation.session_id)
        .subquery()
    )

    rows = (
        db.query(
            ConversationSession,
            stats_subq.c.last_message_at,
            stats_subq.c.message_count,
        )
        .outerjoin(stats_subq, ConversationSession.id == stats_subq.c.session_id)
        .filter(ConversationSession.user_id == current_user.id)
        .order_by(desc(stats_subq.c.last_message_at).nullslast(), ConversationSession.created_at.desc())
        .all()
    )

    sessions = []
    for session, last_message_at, message_count in rows:
        sessions.append({
            "id": session.id,
            "title": session.title,
            "created_at": session.created_at,
            "last_message_at": last_message_at,
            "message_count": message_count or 0,
        })
    return sessions

@app.post("/api/sessions", response_model=ChatSessionResponse)
def create_session(payload: ChatSessionCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    title = (payload.title or "New conversation").strip() or "New conversation"
    session = ConversationSession(user_id=current_user.id, title=title)
    db.add(session)
    db.commit()
    db.refresh(session)
    return {
        "id": session.id,
        "title": session.title,
        "created_at": session.created_at,
        "last_message_at": None,
        "message_count": 0,
    }

@app.get("/api/sessions/{session_id}/messages", response_model=List[ChatHistoryResponse])
def get_session_messages(session_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    session = (
        db.query(ConversationSession)
        .filter(ConversationSession.id == session_id, ConversationSession.user_id == current_user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    messages = (
        db.query(Conversation)
        .filter(Conversation.user_id == current_user.id, Conversation.session_id == session_id)
        .order_by(Conversation.timestamp)
        .all()
    )
    return messages

@app.post("/api/chat")
def chat(request: ChatRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    session_id = request.session_id
    if session_id is None:
        title = request.message.strip()[:40] or "New conversation"
        session = ConversationSession(user_id=current_user.id, title=title)
        db.add(session)
        db.commit()
        db.refresh(session)
        session_id = session.id
    else:
        session = (
            db.query(ConversationSession)
            .filter(ConversationSession.id == session_id, ConversationSession.user_id == current_user.id)
            .first()
        )
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

    # Store user message
    user_msg = Conversation(
        user_id=current_user.id,
        session_id=session_id,
        role="user",
        content=request.message,
    )
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)
    
    # Placeholder LLM response (replace with real model later)
    assistant_reply = f"Echo: {request.message}"
    
    # Store assistant response
    assistant_msg = Conversation(
        user_id=current_user.id,
        session_id=session_id,
        role="assistant",
        content=assistant_reply,
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)
    
    return {
        "user_message": user_msg.content,
        "assistant_message": assistant_msg.content,
        "user_id": current_user.id,
        "session_id": session_id,
    }

@app.delete("/api/history")
def clear_history(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(Conversation).filter(Conversation.user_id == current_user.id).delete()
    db.query(ConversationSession).filter(ConversationSession.user_id == current_user.id).delete()
    db.commit()
    return {"status": "cleared"}