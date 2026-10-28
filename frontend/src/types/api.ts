export type ElementType =
  | 'page'
  | 'header'
  | 'nav'
  | 'section'
  | 'container'
  | 'heading'
  | 'text'
  | 'button'
  | 'link'
  | 'image'
  | 'input'
  | 'form'
  | 'card'
  | 'list'
  | 'table'
  | 'footer'
  | 'icon'
  | 'unknown';

export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface DetectedElement {
  id: string;
  type: ElementType;
  text?: string;
  bbox: BoundingBox;
  style?: Record<string, string>;
  confidence?: number;
  relation_hints?: string[];
}

export interface Viewport {
  width: number;
  height: number;
}

export interface Diagnostic {
  code: string;
  severity: 'error' | 'warning' | 'info';
  message: string;
  node_id?: string;
  suggestion?: string;
}

export interface OptimizationEvent {
  pass_name: string;
  description: string;
  changed_count: number;
  before_summary: string;
  after_summary: string;
}

export interface AnalyzeResponse {
  viewport: Viewport;
  elements: DetectedElement[];
  demo_mode: boolean;
  engine?: string;
}

export interface CompileRequest {
  viewport: Viewport;
  elements: DetectedElement[];
  image_width?: number;
  image_height?: number;
}

export interface CompileResponse {
  html: string;
  css: string;
  js: string;
  ast: any;
  ir: any;
  diagnostics: Diagnostic[];
  optimization_log: OptimizationEvent[];
  demo_mode: boolean;
}

export interface VerificationResult {
  width: number;
  height: number;
  mae: number;
  changed_pixel_percent: number;
  similarity_estimate?: number;
  diff_image_base64?: string;
  metric_explanation: string;
}

export interface HealthResponse {
  status: string;
  demo_mode: boolean;
  provider_configured: boolean;
  version: string;
  engine?: string;
}

export interface RefineRequest {
  ir: any;
  source_description?: string;
  diagnostics?: Diagnostic[];
}

export interface RefineResponse {
  ir: any;
  changes: any[];
  diagnostics: Diagnostic[];
}

export type PipelineStage =
  | 'idle'
  | 'uploading'
  | 'analyzing'
  | 'compiling'
  | 'ready'
  | 'verifying'
  | 'refining'
  | 'error';
