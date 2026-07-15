from fastapi import APIRouter
from pydantic import BaseModel
from app.ai.agent import chat_with_agent

router = APIRouter(prefix="/ai", tags=["AI"])

class ChatRequest(BaseModel):
    message: str

@router.post("/chat")
def chat(request: ChatRequest):
    return chat_with_agent(request.message)