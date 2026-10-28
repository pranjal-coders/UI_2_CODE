from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

# Search for .env in current working directory, backend dir, or parent project root
env_paths = [
    Path.cwd() / ".env",
    Path(__file__).resolve().parent.parent / ".env",
    Path(__file__).resolve().parent.parent.parent / ".env",
]
for env_path in env_paths:
    if env_path.is_file():
        load_dotenv(dotenv_path=env_path)
        break
else:
    load_dotenv()


class Settings:
    def __init__(self) -> None:
        self.VISION_PROVIDER: str = os.getenv("VISION_PROVIDER", "local_cv").strip().lower()
        self.GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")
        self.OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
        self.MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10"))
        self.CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "http://localhost:5173")

    @property
    def cors_origins_list(self) -> list[str]:
        if not self.CORS_ORIGINS:
            return ["http://localhost:5173"]
        origins = [orig.strip() for orig in self.CORS_ORIGINS.split(",") if orig.strip()]
        return origins if origins else ["*"]

    @property
    def provider_configured(self) -> bool:
        if self.VISION_PROVIDER in ("local_cv", "cv", "local"):
            return True
        elif self.VISION_PROVIDER == "gemini":
            return bool(self.GEMINI_API_KEY and self.GEMINI_API_KEY.strip())
        elif self.VISION_PROVIDER == "openai":
            return bool(self.OPENAI_API_KEY and self.OPENAI_API_KEY.strip())
        return False

    @property
    def demo_mode(self) -> bool:
        return self.VISION_PROVIDER == "fixture"


settings = Settings()
