from fastapi import FastAPI
from app.auth import router as auth_router
from app.database import Base, engine
from starlette.middleware.sessions import SessionMiddleware
import os

app = FastAPI(title="Meet-Auth-Free Service")

# Add SessionMiddleware
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET_KEY", "fallback-session-secret"))

# Create database tables
Base.metadata.create_all(bind=engine)

app.include_router(auth_router, prefix="/auth", tags=["auth"])

@app.get("/")
async def root():
    return {"message": "Online Meet Auth Service"}