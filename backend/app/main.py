import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.routes import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ui2code")


@asynccontextmanager
async def lifespan(app: FastAPI):
    mode = "DEMO (Fixture)" if settings.demo_mode else f"LIVE ({settings.VISION_PROVIDER.upper()})"
    logger.info("==================================================")
    logger.info(" UI2Code Compiler Backend Starting Up")
    logger.info(f" Mode: {mode}")
    logger.info(f" Provider Configured: {settings.provider_configured}")
    logger.info(f" CORS Origins: {settings.cors_origins_list}")
    logger.info("==================================================")
    yield
    logger.info("UI2Code Compiler Backend shutting down.")


app = FastAPI(
    title="UI2Code Backend",
    version="1.0.0",
    description="Compiler-assisted visual-to-web code generation system.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
def root():
    return {
        "name": "UI2Code Backend API",
        "version": "1.0.0",
        "docs_url": "/docs",
        "demo_mode": settings.demo_mode,
    }
