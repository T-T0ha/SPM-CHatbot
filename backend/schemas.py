from pydantic import BaseModel, field_validator
from typing import List, Optional
from datetime import datetime

class UserCreate(BaseModel):
    username: str
    password: str

    @field_validator("password")
    @classmethod
    def password_max_72_bytes(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be 72 bytes or fewer.")
        return value

class UserLogin(BaseModel):
    username: str
    password: str

    @field_validator("password")
    @classmethod
    def password_max_72_bytes(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be 72 bytes or fewer.")
        return value

class Token(BaseModel):
    access_token: str
    token_type: str

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str

class ChatHistoryResponse(BaseModel):
    id: int
    role: str
    content: str
    timestamp: datetime

class ChatSessionCreate(BaseModel):
    title: Optional[str] = None

class ChatSessionResponse(BaseModel):
    id: int
    title: str
    created_at: datetime
    last_message_at: Optional[datetime] = None
    message_count: int

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[int] = None