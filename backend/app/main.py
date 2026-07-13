from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.database import init_db, close_db
from app.routers import auth, dataset, chat

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="AI-powered Business Intelligence - Chat with your data",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(dataset.router)
app.include_router(chat.router)


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "app": settings.APP_NAME, "version": settings.VERSION}
