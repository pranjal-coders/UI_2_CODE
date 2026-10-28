from __future__ import annotations

import json
from pathlib import Path
from app.schemas.models import DetectedElement, Viewport
from app.vision.provider import VisionProvider


class FixtureVisionProvider(VisionProvider):
    def __init__(self, fixture_path: str | Path | None = None) -> None:
        if fixture_path:
            self.fixture_path = Path(fixture_path)
        else:
            # Look in standard locations: project root / fixtures or relative to current file
            candidate_paths = [
                Path(__file__).resolve().parent.parent.parent.parent / "fixtures" / "demo_detections.json",
                Path(__file__).resolve().parent.parent.parent / "fixtures" / "demo_detections.json",
                Path.cwd() / "fixtures" / "demo_detections.json",
                Path.cwd().parent / "fixtures" / "demo_detections.json",
            ]
            for p in candidate_paths:
                if p.is_file():
                    self.fixture_path = p
                    break
            else:
                self.fixture_path = candidate_paths[0]

    def _load_fixture(self) -> tuple[Viewport, list[DetectedElement]]:
        if not self.fixture_path.is_file():
            raise FileNotFoundError(f"Fixture file not found at: {self.fixture_path}")
        with open(self.fixture_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        viewport = Viewport(**data["viewport"])
        elements = [DetectedElement(**item) for item in data["elements"]]
        return viewport, elements

    async def analyze(
        self, image_bytes: bytes, image_width: int, image_height: int
    ) -> tuple[Viewport, list[DetectedElement]]:
        return self._load_fixture()
