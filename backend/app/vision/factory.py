from __future__ import annotations

import logging
from app.config import settings
from app.vision.provider import VisionProvider
from app.vision.fixture_provider import FixtureVisionProvider
from app.vision.gemini_provider import GeminiVisionProvider
from app.vision.openai_provider import OpenAIVisionProvider

from typing import Optional
from app.vision.local_cv_provider import LocalCVVisionProvider

logger = logging.getLogger("ui2code.vision")


def get_vision_provider(requested_provider: Optional[str] = None) -> VisionProvider:
    """Instantiate the configured vision provider based on environment or request."""
    provider_name = (requested_provider or settings.VISION_PROVIDER).lower().strip()

    if provider_name == "gemini":
        if settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip():
            logger.info("Using Gemini Vision provider")
            return GeminiVisionProvider(api_key=settings.GEMINI_API_KEY)
        logger.info("GEMINI_API_KEY not configured; using free Local CV provider")
        return LocalCVVisionProvider()

    elif provider_name == "openai":
        if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.strip():
            logger.info("Using OpenAI Vision provider")
            return OpenAIVisionProvider(api_key=settings.OPENAI_API_KEY)
        logger.info("OPENAI_API_KEY not configured; using free Local CV provider")
        return LocalCVVisionProvider()

    elif provider_name == "fixture":
        logger.info("Using FixtureVisionProvider (Static Demo Fixture)")
        return FixtureVisionProvider()

    logger.info("Using LocalCVVisionProvider (100% Free Offline Computer Vision)")
    return LocalCVVisionProvider()

