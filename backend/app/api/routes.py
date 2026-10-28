from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, File, UploadFile, HTTPException, Form
from app.config import settings
from app.analysis.image_processor import validate_image
from app.vision.factory import get_vision_provider
from app.compiler.refiner import generate_and_apply_refinements
from app.services.pipeline import run_pipeline
from app.verification.metrics import compute_verification
from app.schemas.models import (
    HealthResponse,
    AnalyzeResponse,
    CompileRequest,
    CompileResponse,
    VerificationResult,
    RefineRequest,
    RefineResponse,
    Viewport,
)

router = APIRouter(prefix="/api", tags=["ui2code"])


@router.get("/health", response_model=HealthResponse)
async def get_health() -> HealthResponse:
    """Return system status, demo mode flag, and API version."""
    return HealthResponse(
        status="ok",
        demo_mode=settings.demo_mode,
        provider_configured=settings.provider_configured,
        version="1.0.0",
        engine=settings.VISION_PROVIDER,
    )


@router.get("/demo-image")
async def get_demo_image():
    """Return the bundled demo screenshot image for quick testing and review."""
    from fastapi.responses import FileResponse
    from pathlib import Path

    candidate_paths = [
        Path.cwd() / "fixtures" / "demo_screenshot.png",
        Path.cwd().parent / "fixtures" / "demo_screenshot.png",
        Path(__file__).resolve().parent.parent.parent / "fixtures" / "demo_screenshot.png",
        Path(__file__).resolve().parent.parent.parent.parent / "fixtures" / "demo_screenshot.png",
    ]
    for p in candidate_paths:
        if p.is_file():
            return FileResponse(p, media_type="image/png", filename="demo_screenshot.png")

    raise HTTPException(status_code=404, detail="Demo screenshot fixture not found")


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_image(
    file: UploadFile = File(...),
    provider: Optional[str] = Form(None),
) -> AnalyzeResponse:
    """Validate and visually analyze an uploaded design image."""
    try:
        file_bytes = await file.read()
        width, height = validate_image(
            file_bytes=file_bytes,
            content_type=file.content_type,
            max_size_mb=settings.MAX_UPLOAD_SIZE_MB,
        )
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err

    try:
        active_provider = get_vision_provider(requested_provider=provider)
        _, elements = await active_provider.analyze(file_bytes, width, height)
    except Exception as err:
        raise HTTPException(
            status_code=502,
            detail=f"Visual analysis provider failed: {err}. You can verify your API key or use demo mode."
        ) from err

    active_engine = provider or settings.VISION_PROVIDER
    return AnalyzeResponse(
        viewport=Viewport(width=width, height=height),
        elements=elements,
        demo_mode=(active_engine == "fixture"),
        engine=active_engine,
    )


@router.post("/compile", response_model=CompileResponse)
async def compile_ui(
    request: CompileRequest,
) -> CompileResponse:
    """Run the complete compilation pipeline: AST -> IR -> Semantic -> Optimize -> Code."""
    try:
        response = await run_pipeline(
            viewport=request.viewport,
            elements=request.elements,
            image_width=request.image_width,
            image_height=request.image_height,
            ir=request.ir,
        )
        return response
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Compilation pipeline failed: {err}") from err


@router.post("/verify", response_model=VerificationResult)
async def verify_images(
    source_image: UploadFile = File(...),
    generated_image: UploadFile = File(...),
) -> VerificationResult:
    """Compare source image against rendered output and produce difference metrics."""
    try:
        src_bytes = await source_image.read()
        gen_bytes = await generated_image.read()

        validate_image(src_bytes, source_image.content_type, settings.MAX_UPLOAD_SIZE_MB)
        validate_image(gen_bytes, generated_image.content_type, settings.MAX_UPLOAD_SIZE_MB)

        result = compute_verification(src_bytes, gen_bytes)
        return result
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Verification failed: {err}") from err


@router.post("/refine", response_model=RefineResponse)
async def refine_ui(
    request: RefineRequest,
) -> RefineResponse:
    """Refine existing IR with natural language instructions using allowlisted patching."""
    try:
        instruction = request.source_description or "Optimize layout and styles"
        refined_ir, changes, diagnostics = await generate_and_apply_refinements(
            ir_dict=request.ir,
            instruction=instruction,
            api_key=settings.GEMINI_API_KEY if settings.VISION_PROVIDER == "gemini" else None,
            provider_name=settings.VISION_PROVIDER,
        )
        return RefineResponse(
            ir=refined_ir,
            changes=changes,
            diagnostics=diagnostics,
        )
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Refinement pass failed: {err}") from err

