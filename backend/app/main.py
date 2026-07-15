from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base
import app.models

from app.routers import interaction
from app.routers import ai

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI First CRM - HCP Interaction API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://hcp-interaction-crm.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(interaction.router)
app.include_router(ai.router)

@app.get("/")
def root():
    return {
        "message": "AI CRM Backend Running Successfully 🚀"
    }