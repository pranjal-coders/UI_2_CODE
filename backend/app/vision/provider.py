from abc import ABC, abstractmethod
from app.schemas.models import DetectedElement, Viewport


class VisionProvider(ABC):
    @abstractmethod
    async def analyze(
        self, image_bytes: bytes, image_width: int, image_height: int
    ) -> tuple[Viewport, list[DetectedElement]]:
        """Analyze an image and return viewport with detected elements."""
        ...
