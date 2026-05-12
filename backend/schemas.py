from pydantic import BaseModel
from typing import List
from datetime import datetime

class UserCreate(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

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

class ChatRequest(BaseModel):
    message: str