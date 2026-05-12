from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://chatbot_user:chatbot_pass@localhost:5433/chatbot_db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Models
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default="user")

class ConversationSession(Base):
    __tablename__ = "conversation_sessions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(120), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    summary = Column(Text, nullable=True)
    summary_msg_count = Column(Integer, default=0)

class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_id = Column(Integer, ForeignKey("conversation_sessions.id"), nullable=True, index=True)
    role = Column(String(20), nullable=False)   # "user" or "assistant"
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

# Create tables
def init_db():
    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    if "conversations" in inspector.get_table_names():
        columns = {col["name"] for col in inspector.get_columns("conversations")}
        if "session_id" not in columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE conversations ADD COLUMN session_id INTEGER"))

    if "conversation_sessions" in inspector.get_table_names():
        sess_cols = {col["name"] for col in inspector.get_columns("conversation_sessions")}
        if "summary" not in sess_cols:
            with engine.begin() as conn:
                conn.execute(text(
                    "ALTER TABLE conversation_sessions "
                    "ADD COLUMN summary TEXT"
                ))
        if "summary_msg_count" not in sess_cols:
            with engine.begin() as conn:
                conn.execute(text(
                    "ALTER TABLE conversation_sessions "
                    "ADD COLUMN summary_msg_count INTEGER DEFAULT 0"
                ))

    if "users" in inspector.get_table_names():
        user_cols = {col["name"] for col in inspector.get_columns("users")}
        if "role" not in user_cols:
            with engine.begin() as conn:
                conn.execute(text(
                    "ALTER TABLE users "
                    "ADD COLUMN role VARCHAR(20) DEFAULT 'user'"
                ))

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()