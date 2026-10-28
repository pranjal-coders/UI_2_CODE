from __future__ import annotations

import html
import re
from app.schemas.models import UIIR, UIIRNode

VOID_ELEMENTS = {"img", "input", "br", "hr", "meta", "link"}


def camel_to_kebab(name: str) -> str:
    """Convert camelCase identifier to kebab-case."""
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1-\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", s1).lower()


def _render_html_node(node: UIIRNode, indent_level: int = 2) -> str:
    indent = " " * indent_level
    tag = node.html_tag

    # Classes and Attributes
    classes = list(node.css_classes)
    for k, v in node.attributes.items():
        if k.lower() == "class" and v:
            for cls in str(v).split():
                if cls not in classes:
                    classes.append(cls)

    attr_list: list[str] = []
    if classes:
        attr_list.append(f'class="{" ".join(classes)}"')
    attr_list.append(f'data-ui2c-id="{node.id}"')

    for k, v in sorted(node.attributes.items()):
        if k.lower() == "class":
            continue
        attr_list.append(f'{k}="{html.escape(str(v))}"')

    attrs_str = (" " + " ".join(attr_list)) if attr_list else ""

    if tag in VOID_ELEMENTS:
        return f"{indent}<{tag}{attrs_str} />\n"

    # Opening tag
    has_children = len(node.children) > 0
    text_content = html.escape(node.text) if node.text else ""

    if not has_children and not text_content:
        return f"{indent}<{tag}{attrs_str}></{tag}>\n"

    if not has_children:
        return f"{indent}<{tag}{attrs_str}>{text_content}</{tag}>\n"

    lines: list[str] = [f"{indent}<{tag}{attrs_str}>\n"]
    if text_content:
        lines.append(f"{indent}  {text_content}\n")

    for child in node.children:
        lines.append(_render_html_node(child, indent_level + 2))

    lines.append(f"{indent}</{tag}>\n")
    return "".join(lines)


def _generate_html(ir: UIIR) -> str:
    body_content = _render_html_node(ir.root, indent_level=4)

    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Generated UI - UI2Code</title>
    <link rel="stylesheet" href="style.css">
  </head>
  <body>
{body_content}    <script src="script.js"></script>
  </body>
</html>
"""


def _traverse_all(root: UIIRNode) -> list[UIIRNode]:
    nodes = [root]
    for child in root.children:
        nodes.extend(_traverse_all(child))
    return nodes


def _generate_css(ir: UIIR) -> str:
    viewport_width = ir.viewport.width

    css_lines: list[str] = [
        "/* UI2Code Auto-Generated Stylesheet */",
        "*, *::before, *::after {",
        "  box-sizing: border-box;",
        "  margin: 0;",
        "  padding: 0;",
        "}",
        "",
        "body {",
        '  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;',
        "  line-height: 1.5;",
        "  color: #1a1a1a;",
        "  background-color: #ffffff;",
        "  max-width: 100%;",
        "  overflow-x: hidden;",
        "}",
        "",
        ".page {",
        "  width: 100%;",
        f"  max-width: {viewport_width}px;",
        "  margin: 0 auto;",
        "  position: relative;",
        "}",
        "",
    ]

    # Shared tokens
    if ir.style_tokens:
        css_lines.append("/* Shared Design Tokens */")
        for token_class in sorted(ir.style_tokens.keys()):
            token_style = ir.style_tokens[token_class]
            css_lines.append(f".{token_class} {{")
            for prop in sorted(token_style.keys()):
                val = token_style[prop]
                kebab_prop = camel_to_kebab(prop)
                css_lines.append(f"  {kebab_prop}: {val};")
            css_lines.append("}")
            css_lines.append("")

    # Node-specific styles
    css_lines.append("/* Component & Element Styles */")
    all_nodes = _traverse_all(ir.root)
    emitted_selectors: set[str] = set()

    for node in all_nodes:
        # Choose primary selector class
        selector_class = node.css_classes[0] if node.css_classes else f"ui2c-{node.id}"
        if selector_class in emitted_selectors:
            continue
        emitted_selectors.add(selector_class)

        declarations: list[str] = []

        if node.layout == "flex" and "display" not in node.style:
            declarations.append("  display: flex;")
        elif node.layout == "grid" and "display" not in node.style:
            declarations.append("  display: grid;")
        elif node.layout == "absolute" and node.bbox:
            declarations.append("  position: absolute;")
            declarations.append(f"  left: {node.bbox.x * 100}%;")
            declarations.append(f"  top: {node.bbox.y * 100}%;")
            declarations.append(f"  width: {node.bbox.width * 100}%;")
            declarations.append(f"  height: {node.bbox.height * 100}%;")

        for prop in sorted(node.style.keys()):
            val = node.style[prop]
            kebab_prop = camel_to_kebab(prop)
            declarations.append(f"  {kebab_prop}: {val};")

        if declarations:
            css_lines.append(f".{selector_class} {{")
            css_lines.extend(declarations)
            css_lines.append("}")
            css_lines.append("")

    return "\n".join(css_lines)


def _generate_js(ir: UIIR) -> str:
    return """// UI2Code Interactive Handlers
document.addEventListener('DOMContentLoaded', () => {
  // Placeholder button interaction handler
  const buttons = document.querySelectorAll('button, .ui2c-button');
  buttons.forEach(button => {
    button.addEventListener('click', (event) => {
      const id = button.getAttribute('data-ui2c-id') || 'unknown';
      console.log(`[UI2Code] Clicked button [${id}]: "${button.textContent.trim()}"`);
    });
  });

  // Placeholder navigation link handler
  const links = document.querySelectorAll('a[href="#"]');
  links.forEach(link => {
    link.addEventListener('click', (event) => {
      event.preventDefault();
      const id = link.getAttribute('data-ui2c-id') || 'unknown';
      console.log(`[UI2Code] Navigation link clicked [${id}]: "${link.textContent.trim()}"`);
    });
  });
});
"""


def generate_code(ir: UIIR) -> tuple[str, str, str]:
    """Generate HTML5, CSS3, and JavaScript code from the optimized Intermediate Representation."""
    html_content = _generate_html(ir)
    css_content = _generate_css(ir)
    js_content = _generate_js(ir)
    return html_content, css_content, js_content
