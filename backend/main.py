from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import init_db, get_db, User, Conversation
from auth import get_password_hash, authenticate_user, create_access_token, get_current_user
from schemas import UserCreate, UserLogin, Token, ChatRequest, ChatHistoryResponse
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
@app.get("/api/history", response_model=List[ChatHistoryResponse])
def get_history(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    messages = db.query(Conversation).filter(Conversation.user_id == current_user.id).order_by(Conversation.timestamp).all()
    return messages

@app.post("/api/chat")
def chat(request: ChatRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Store user message
    user_msg = Conversation(user_id=current_user.id, role="user", content=request.message)
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)
    
    # Placeholder LLM response (replace with real model later)
    assistant_reply = f"Echo: {request.message}"
    
    # Store assistant response
    assistant_msg = Conversation(user_id=current_user.id, role="assistant", content=assistant_reply)
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)
    
    return {
        "user_message": user_msg.content,
        "assistant_message": assistant_msg.content,
        "user_id": current_user.id
    }

@app.delete("/api/history")
def clear_history(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(Conversation).filter(Conversation.user_id == current_user.id).delete()
    db.commit()
    return {"status": "cleared"}