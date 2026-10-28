from __future__ import annotations

from enum import Enum
from typing import Optional, Literal
from pydantic import BaseModel, Field


class ElementType(str, Enum):
    PAGE = 'page'
    HEADER = 'header'
    NAV = 'nav'
    SECTION = 'section'
    CONTAINER = 'container'
    HEADING = 'heading'
    TEXT = 'text'
    BUTTON = 'button'
    LINK = 'link'
    IMAGE = 'image'
    INPUT = 'input'
    FORM = 'form'
    CARD = 'card'
    LIST = 'list'
    TABLE = 'table'
    FOOTER = 'footer'
    ICON = 'icon'
    UNKNOWN = 'unknown'


class BoundingBox(BaseModel):
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    width: float = Field(ge=0, le=1)
    height: float = Field(ge=0, le=1)


class DetectedElement(BaseModel):
    id: str
    type: ElementType
    text: Optional[str] = None
    bbox: BoundingBox
    style: Optional[dict[str, str]] = None
    confidence: Optional[float] = Field(None, ge=0, le=1)
    relation_hints: Optional[list[str]] = None


class Viewport(BaseModel):
    width: int = Field(gt=0)
    height: int = Field(gt=0)


class UIASTNode(BaseModel):
    id: str
    type: ElementType
    text: Optional[str] = None
    attributes: dict[str, str] = Field(default_factory=dict)
    bbox: Optional[BoundingBox] = None
    style: Optional[dict[str, str]] = None
    children: list[UIASTNode] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class UIIRNode(BaseModel):
    id: str
    type: ElementType
    html_tag: str
    text: Optional[str] = None
    attributes: dict[str, str] = Field(default_factory=dict)
    bbox: Optional[BoundingBox] = None
    style: dict[str, str] = Field(default_factory=dict)
    css_classes: list[str] = Field(default_factory=list)
    layout: Literal['flow', 'flex', 'grid', 'absolute'] = 'flow'
    children: list[UIIRNode] = Field(default_factory=list)


class Diagnostic(BaseModel):
    code: str
    severity: Literal['error', 'warning', 'info']
    message: str
    node_id: Optional[str] = None
    suggestion: Optional[str] = None


class UIIR(BaseModel):
    version: str = '1.0.0'
    viewport: Viewport
    root: UIIRNode
    style_tokens: dict[str, dict[str, str]] = Field(default_factory=dict)
    assets: list[dict] = Field(default_factory=list)
    diagnostics: list[Diagnostic] = Field(default_factory=list)


class OptimizationEvent(BaseModel):
    pass_name: str
    description: str
    changed_count: int
    before_summary: str
    after_summary: str


class AnalyzeResponse(BaseModel):
    viewport: Viewport
    elements: list[DetectedElement]
    demo_mode: bool
    engine: Optional[str] = "local_cv"


class CompileRequest(BaseModel):
    viewport: Viewport
    elements: list[DetectedElement] = Field(default_factory=list)
    ir: Optional[dict] = None
    image_width: Optional[int] = None
    image_height: Optional[int] = None


class CompileResponse(BaseModel):
    html: str
    css: str
    js: str
    ast: dict
    ir: dict
    diagnostics: list[Diagnostic]
    optimization_log: list[OptimizationEvent]
    demo_mode: bool


class VerificationResult(BaseModel):
    width: int
    height: int
    mae: float
    changed_pixel_percent: float
    similarity_estimate: Optional[float] = None
    diff_image_base64: Optional[str] = None
    metric_explanation: str


class HealthResponse(BaseModel):
    status: str
    demo_mode: bool
    provider_configured: bool
    version: str
    engine: Optional[str] = "local_cv"


class RefineRequest(BaseModel):
    ir: dict
    source_description: Optional[str] = None
    diagnostics: list[Diagnostic] = Field(default_factory=list)


class RefineResponse(BaseModel):
    ir: dict
    changes: list[dict] = Field(default_factory=list)
    diagnostics: list[Diagnostic] = Field(default_factory=list)


UIASTNode.model_rebuild()
UIIRNode.model_rebuild()
UIIR.model_rebuild()
