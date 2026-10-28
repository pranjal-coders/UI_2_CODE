from __future__ import annotations

from typing import Optional
from app.config import settings
from app.schemas.models import (
    Viewport,
    DetectedElement,
    CompileResponse,
)
from app.compiler.ast_builder import build_ast
from app.compiler.ir_builder import build_ir
from app.compiler.semantic_analyzer import analyze_semantics
from app.compiler.optimizations import run_optimizations
from app.compiler.code_generator import generate_code


async def run_pipeline(
    viewport: Viewport,
    elements: list[DetectedElement],
    image_width: Optional[int] = None,
    image_height: Optional[int] = None,
    ir: Optional[dict] = None,
) -> CompileResponse:
    """Run full UI2Code compilation pipeline:
    Visual Analysis -> AST Construction -> IR Generation -> Semantic Analysis -> Optimizations -> Code Generation.
    """
    from app.schemas.models import UIIR

    if ir:
        # Re-compilation from refined/provided IR
        initial_ir = UIIR.model_validate(ir)
        ast_dict = {"id": "root", "type": "page", "children": []}
    else:
        # 1. Build AST from flat detections
        ast_root = build_ast(viewport, elements)
        ast_dict = ast_root.model_dump()

        # 2. Build initial IR
        initial_ir = build_ir(ast_root, viewport)

    # 3. Perform semantic analysis
    diagnostics = analyze_semantics(initial_ir)
    initial_ir.diagnostics = diagnostics

    # 4. Run optimization passes
    optimized_ir, optimization_events = run_optimizations(initial_ir)

    # 5. Generate target web assets
    html_code, css_code, js_code = generate_code(optimized_ir)

    # 6. Package result
    return CompileResponse(
        html=html_code,
        css=css_code,
        js=js_code,
        ast=ast_dict,
        ir=optimized_ir.model_dump(),
        diagnostics=diagnostics,
        optimization_log=optimization_events,
        demo_mode=settings.demo_mode,
    )
