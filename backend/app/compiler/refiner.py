from __future__ import annotations

import copy
import logging
from typing import Any, Optional
from app.schemas.models import UIIR, UIIRNode, Diagnostic, BoundingBox

logger = logging.getLogger("ui2code.refiner")

ALLOWED_STYLE_PROPERTIES = {
    "backgroundColor",
    "color",
    "fontSize",
    "fontWeight",
    "padding",
    "margin",
    "gap",
    "borderRadius",
    "textAlign",
    "border",
    "lineHeight",
    "boxShadow",
    "maxWidth",
    "width",
    "minHeight",
}

ALLOWED_FIELDS = {
    "text",
    "layout",
    "bbox",
}


def _find_node(root: dict | UIIRNode, target_id: str) -> Optional[dict | UIIRNode]:
    """Recursively locate a node by ID in an IR tree dictionary or UIIRNode."""
    current_id = root["id"] if isinstance(root, dict) else root.id
    if current_id == target_id:
        return root

    children = root.get("children", []) if isinstance(root, dict) else root.children
    for child in children:
        found = _find_node(child, target_id)
        if found is not None:
            return found
    return None


def validate_and_apply_patch(
    ir_dict: dict, patch: dict
) -> tuple[bool, str, Optional[dict]]:
    """Validate a single suggested refinement patch against the allowlist and apply it to ir_dict.
    
    Patch format:
    {
      "node_id": "el-1",
      "field": "style.backgroundColor" or "text" or "bbox" or "layout",
      "proposed_value": "#22223b",
      "rationale": "Improve contrast with background"
    }
    """
    node_id = patch.get("node_id")
    field = patch.get("field")
    proposed_value = patch.get("proposed_value")
    rationale = patch.get("rationale", "")

    if not node_id:
        return False, "Missing 'node_id' in patch", None

    root = ir_dict.get("root")
    if not root:
        return False, "Malformed IR: missing root node", None

    target_node = _find_node(root, node_id)
    if not target_node:
        return False, f"Target node '{node_id}' not found in IR tree", None

    # Check field allowlist
    if field.startswith("style."):
        prop_name = field[len("style.") :]
        if prop_name not in ALLOWED_STYLE_PROPERTIES:
            return False, f"Style property '{prop_name}' is not in allowlist", None

        # Clean and apply style
        str_val = str(proposed_value).strip()
        if ";" in str_val or "<" in str_val or ">" in str_val:
            return False, f"Potentially unsafe characters in style value '{str_val}'", None

        target_node.setdefault("style", {})[prop_name] = str_val
        applied_record = {
            "node_id": node_id,
            "field": field,
            "old_value": target_node.get("style", {}).get(prop_name),
            "new_value": str_val,
            "rationale": rationale,
        }
        return True, f"Updated {field} on node '{node_id}'", applied_record

    elif field == "text":
        str_val = str(proposed_value).strip() if proposed_value is not None else None
        old_val = target_node.get("text")
        target_node["text"] = str_val
        applied_record = {
            "node_id": node_id,
            "field": "text",
            "old_value": old_val,
            "new_value": str_val,
            "rationale": rationale,
        }
        return True, f"Updated text on node '{node_id}'", applied_record

    elif field == "layout":
        if proposed_value not in ("flow", "flex", "grid", "absolute"):
            return False, f"Invalid layout mode '{proposed_value}'", None
        old_val = target_node.get("layout", "flow")
        target_node["layout"] = proposed_value
        applied_record = {
            "node_id": node_id,
            "field": "layout",
            "old_value": old_val,
            "new_value": proposed_value,
            "rationale": rationale,
        }
        return True, f"Updated layout to '{proposed_value}' on node '{node_id}'", applied_record

    elif field == "bbox":
        if not isinstance(proposed_value, dict):
            return False, "Bbox must be a dictionary with x, y, width, height", None
        try:
            x = max(0.0, min(1.0, float(proposed_value.get("x", 0.0))))
            y = max(0.0, min(1.0, float(proposed_value.get("y", 0.0))))
            w = max(0.001, min(1.0 - x, float(proposed_value.get("width", 0.1))))
            h = max(0.001, min(1.0 - y, float(proposed_value.get("height", 0.05))))
            new_bbox = {"x": round(x, 4), "y": round(y, 4), "width": round(w, 4), "height": round(h, 4)}
            old_bbox = target_node.get("bbox")
            target_node["bbox"] = new_bbox
            applied_record = {
                "node_id": node_id,
                "field": "bbox",
                "old_value": old_bbox,
                "new_value": new_bbox,
                "rationale": rationale,
            }
            return True, f"Updated bbox on node '{node_id}'", applied_record
        except (ValueError, TypeError) as err:
            return False, f"Invalid numeric values in bbox: {err}", None

    return False, f"Unsupported field '{field}'. Allowed fields: style.*, text, layout, bbox", None


def apply_refinements(
    ir_dict: dict, patches: list[dict]
) -> tuple[dict, list[dict], list[Diagnostic]]:
    """Apply a list of refinement patches to an IR dictionary, returning modified copy, change log, and diagnostics."""
    ir_copy = copy.deepcopy(ir_dict)
    applied_changes: list[dict] = []
    diagnostics: list[Diagnostic] = []

    for patch in patches:
        success, message, record = validate_and_apply_patch(ir_copy, patch)
        if success:
            if record:
                applied_changes.append(record)
            diagnostics.append(
                Diagnostic(
                    code="REFINE_APPLIED",
                    severity="info",
                    message=message,
                    node_id=patch.get("node_id"),
                )
            )
        else:
            diagnostics.append(
                Diagnostic(
                    code="REFINE_REJECTED",
                    severity="warning",
                    message=f"Refinement rejected: {message}",
                    node_id=patch.get("node_id"),
                )
            )

    return ir_copy, applied_changes, diagnostics


def _extract_heuristic_patches(ir_dict: dict, instruction: str) -> list[dict]:
    """Generate conservative rule-based patches from user keywords when offline/demo mode."""
    lower_inst = instruction.lower()
    patches: list[dict] = []
    root = ir_dict.get("root", {})

    def _walk_and_patch(node: dict):
        node_id = node.get("id", "")
        node_type = node.get("type", "")

        # Border radius adjustments
        if "round" in lower_inst or "border-radius" in lower_inst or "radius" in lower_inst:
            if node_type in ("card", "button", "container"):
                patches.append({
                    "node_id": node_id,
                    "field": "style.borderRadius",
                    "proposed_value": "12px" if node_type == "card" else "8px",
                    "rationale": f"Normalized border-radius on {node_type} per instruction",
                })

        # Padding / compact adjustments
        if "compact" in lower_inst or "reduce padding" in lower_inst:
            if node_type in ("card", "section", "header"):
                patches.append({
                    "node_id": node_id,
                    "field": "style.padding",
                    "proposed_value": "16px 20px" if node_type == "card" else "32px 24px",
                    "rationale": f"Compacted padding on {node_type} per instruction",
                })
        elif "spacious" in lower_inst or "increase padding" in lower_inst:
            if node_type in ("card", "section"):
                patches.append({
                    "node_id": node_id,
                    "field": "style.padding",
                    "proposed_value": "40px 32px",
                    "rationale": f"Expanded padding on {node_type} per instruction",
                })

        # Dark theme / background adjustment
        if "dark" in lower_inst and "light" not in lower_inst:
            if node_type == "page":
                patches.append({
                    "node_id": node_id,
                    "field": "style.backgroundColor",
                    "proposed_value": "#12121e",
                    "rationale": "Applied dark background to page",
                })
            elif node_type == "card":
                patches.append({
                    "node_id": node_id,
                    "field": "style.backgroundColor",
                    "proposed_value": "#1a1a2e",
                    "rationale": "Adapted card background for dark mode",
                })

        for child in node.get("children", []):
            _walk_and_patch(child)

    if root:
        _walk_and_patch(root)

    return patches


async def generate_and_apply_refinements(
    ir_dict: dict,
    instruction: str,
    api_key: Optional[str] = None,
    provider_name: str = "fixture",
) -> tuple[dict, list[dict], list[Diagnostic]]:
    """Process a refinement request, asking vision LLM if configured, or applying heuristic allowlisted patches."""
    import json
    import httpx
    from app.vision.gemini_provider import _clean_json_response

    patches: list[dict] = []

    # If LLM API key is configured, request structured patches from the model
    if api_key and provider_name == "gemini":
        prompt = f"""You are a UI refinement assistant for a compiler-assisted visual-to-web system.
Given the current UI IR (Intermediate Representation) and refinement instruction, propose specific, allowlisted IR edits.

CRITICAL RULES:
1. Output ONLY a JSON array of patch objects conforming to this schema:
   [
     {{
       "node_id": "<target node id from IR>",
       "field": "style.<propertyName>" (or "text" or "layout" or "bbox"),
       "proposed_value": "<value>",
       "rationale": "<brief reason>"
     }}
   ]
2. Allowed style properties: {', '.join(sorted(ALLOWED_STYLE_PROPERTIES))}.
3. Allowed non-style fields: text, layout, bbox.
4. ONLY modify nodes that exist in the provided IR. Do NOT invent new node IDs.
5. Do NOT return full HTML or CSS code.

Instruction: {instruction}
Current IR:
{json.dumps(ir_dict, indent=2)[:3000]}
"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "response_mime_type": "application/json"},
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    cand = resp.json().get("candidates", [])[0]["content"]["parts"][0]["text"]
                    parsed = json.loads(_clean_json_response(cand))
                    if isinstance(parsed, list):
                        patches = parsed
                    elif isinstance(parsed, dict) and "patches" in parsed:
                        patches = parsed["patches"]
        except Exception as e:
            logger.warning(f"LLM refinement suggestion failed: {e}; falling back to heuristics")

    if not patches:
        # Fallback to allowlisted heuristic patches based on instruction keywords
        patches = _extract_heuristic_patches(ir_dict, instruction)

    if not patches:
        return (
            ir_dict,
            [{
                "action": "noop",
                "description": f"No modifications required for instruction: '{instruction}'.",
            }],
            [Diagnostic(
                code="REFINE_NO_OP",
                severity="info",
                message="No matching allowlisted IR modifications were identified.",
            )],
        )

    # Validate and apply all patches through the strict allowlist validator
    return apply_refinements(ir_dict, patches)

