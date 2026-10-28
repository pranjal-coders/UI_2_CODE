from __future__ import annotations

from app.schemas.models import (
    ElementType,
    BoundingBox,
    DetectedElement,
    Viewport,
)
from app.compiler.ast_builder import build_ast
from app.compiler.ir_builder import build_ir
from app.compiler.optimizations import run_optimizations
from app.compiler.code_generator import generate_code, camel_to_kebab


def test_camel_to_kebab_conversion() -> None:
    assert camel_to_kebab("backgroundColor") == "background-color"
    assert camel_to_kebab("fontSize") == "font-size"
    assert camel_to_kebab("borderRadius") == "border-radius"
    assert camel_to_kebab("boxShadow") == "box-shadow"
    assert camel_to_kebab("alignItems") == "align-items"
    assert camel_to_kebab("color") == "color"


def test_generated_html_structure(demo_viewport: Viewport, demo_elements: list[DetectedElement]) -> None:
    ast = build_ast(demo_viewport, demo_elements)
    ir = build_ir(ast, demo_viewport)
    opt_ir, _ = run_optimizations(ir)
    html_code, _, _ = generate_code(opt_ir)

    assert "<!DOCTYPE html>" in html_code
    assert '<link rel="stylesheet" href="style.css">' in html_code
    assert '<meta charset="UTF-8">' in html_code
    assert '<script src="script.js"></script>' in html_code
    assert 'data-ui2c-id="el-1"' in html_code
    assert "TechFlow" in html_code


def test_generated_css_contains_page_class(demo_viewport: Viewport, demo_elements: list[DetectedElement]) -> None:
    ast = build_ast(demo_viewport, demo_elements)
    ir = build_ir(ast, demo_viewport)
    opt_ir, _ = run_optimizations(ir)
    _, css_code, _ = generate_code(opt_ir)

    assert ".page {" in css_code
    assert f"max-width: {demo_viewport.width}px;" in css_code
    assert "box-sizing: border-box;" in css_code
    assert "overflow-x: hidden;" in css_code


def test_generated_js_contains_dom_content_loaded(demo_viewport: Viewport, demo_elements: list[DetectedElement]) -> None:
    ast = build_ast(demo_viewport, demo_elements)
    ir = build_ir(ast, demo_viewport)
    opt_ir, _ = run_optimizations(ir)
    _, _, js_code = generate_code(opt_ir)

    assert "DOMContentLoaded" in js_code
    assert "document.querySelectorAll" in js_code
    assert "addEventListener" in js_code


def test_code_generator_is_deterministic(demo_viewport: Viewport, demo_elements: list[DetectedElement]) -> None:
    ast = build_ast(demo_viewport, demo_elements)
    ir = build_ir(ast, demo_viewport)
    opt_ir, _ = run_optimizations(ir)

    html1, css1, js1 = generate_code(opt_ir)
    html2, css2, js2 = generate_code(opt_ir)

    assert html1 == html2
    assert css1 == css2
    assert js1 == js2
