import React, { useState, useEffect, useRef } from 'react';
import JSZip from 'jszip';
import { saveAs } from 'file-saver';

import {
  AnalyzeResponse,
  CompileResponse,
  PipelineStage,
  VerificationResult,
} from './types/api';
import {
  analyzeImage,
  checkHealth,
  compileDetections,
  fetchDemoImage,
  refineIR,
  verifyOutput,
} from './lib/apiClient';

import { TopBar } from './components/TopBar';
import { SourcePanel } from './components/SourcePanel';
import { CodeWorkspace } from './components/CodeWorkspace';
import { PreviewPanel } from './components/PreviewPanel';
import { InspectionPanel } from './components/InspectionPanel';

import './App.css';

async function renderHtmlToBlob(
  html: string,
  css: string,
  width: number,
  height: number
): Promise<Blob> {
  const canvas = document.createElement('canvas');
  canvas.width = Math.max(200, width);
  canvas.height = Math.max(200, height);
  const ctx = canvas.getContext('2d');

  if (!ctx) {
    throw new Error('Canvas 2D context is unavailable');
  }

  // Draw neutral background
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  // Strip script tags to prevent any SVG security violations
  const cleanHtml = (html || '').replace(
    /<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi,
    ''
  );

  const svgData = `
    <svg xmlns="http://www.w3.org/2000/svg" width="${canvas.width}" height="${canvas.height}">
      <foreignObject width="100%" height="100%">
        <div xmlns="http://www.w3.org/1999/xhtml" style="width: ${canvas.width}px; height: ${canvas.height}px; background-color: #ffffff; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; box-sizing: border-box;">
          <style>${css || ''}</style>
          ${cleanHtml}
        </div>
      </foreignObject>
    </svg>
  `;

  return new Promise((resolve) => {
    const img = new Image();
    const svgBlob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(svgBlob);

    img.onload = () => {
      try {
        ctx.drawImage(img, 0, 0);
        URL.revokeObjectURL(url);
        canvas.toBlob((blob) => {
          resolve(blob || svgBlob);
        }, 'image/png');
      } catch {
        URL.revokeObjectURL(url);
        canvas.toBlob((blob) => {
          resolve(blob || svgBlob);
        }, 'image/png');
      }
    };

    img.onerror = () => {
      URL.revokeObjectURL(url);
      canvas.toBlob((blob) => {
        resolve(blob || new Blob([], { type: 'image/png' }));
      }, 'image/png');
    };

    img.src = url;
  });
}

export const App: React.FC = () => {
  // Pipeline & Artifacts State
  const [stage, setStage] = useState<PipelineStage>('idle');
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [imagePreviewUrl, setImagePreviewUrl] = useState<string | null>(null);
  const [imageDimensions, setImageDimensions] = useState<{
    width: number;
    height: number;
  } | null>(null);

  const [analyzeResponse, setAnalyzeResponse] = useState<AnalyzeResponse | null>(null);
  const [compileResponse, setCompileResponse] = useState<CompileResponse | null>(null);

  // Editable Code State
  const [htmlCode, setHtmlCode] = useState<string>('');
  const [cssCode, setCssCode] = useState<string>('');
  const [jsCode, setJsCode] = useState<string>('');

  // Debounced Code for Live Preview (400ms delay)
  const [debouncedHtml, setDebouncedHtml] = useState<string>('');
  const [debouncedCss, setDebouncedCss] = useState<string>('');
  const [debouncedJs, setDebouncedJs] = useState<string>('');

  // Inspection & Verification State
  const [verificationResult, setVerificationResult] = useState<VerificationResult | null>(
    null
  );
  const [error, setError] = useState<string | null>(null);
  const [demoMode, setDemoMode] = useState<boolean>(false);
  const [activeEngine, setActiveEngine] = useState<string>('local_cv');
  const [activeInspectorTab, setActiveInspectorTab] = useState<string>('elements');
  const [isInspectorCollapsed, setIsInspectorCollapsed] = useState<boolean>(false);
  const [activeEditorTab, setActiveEditorTab] = useState<'html' | 'css' | 'js'>('html');

  // Refine Modal
  const [isRefineModalOpen, setIsRefineModalOpen] = useState<boolean>(false);
  const [refineInstruction, setRefineInstruction] = useState<string>(
    'Optimize hierarchy, simplify wrappers, and normalize padding.'
  );

  const iframeRef = useRef<HTMLIFrameElement>(null);

  // Initial Health Check
  useEffect(() => {
    checkHealth()
      .then((health) => {
        setDemoMode(Boolean(health.demo_mode));
        if (health.engine) {
          setActiveEngine(health.engine);
        }
      })
      .catch((err) => {
        // Backend might still be starting
        console.warn('Initial backend health check:', err.message);
      });
  }, []);

  // Debounce preview updates (400ms)
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedHtml(htmlCode);
      setDebouncedCss(cssCode);
      setDebouncedJs(jsCode);
    }, 400);

    return () => clearTimeout(timer);
  }, [htmlCode, cssCode, jsCode]);

  // File Upload Handler with Validation
  const handleFileUpload = (file: File) => {
    setError(null);

    // Validate type
    const validTypes = ['image/png', 'image/jpeg', 'image/webp'];
    if (!validTypes.includes(file.type)) {
      setError(
        `Invalid file format: ${file.type || 'unknown'}. Please upload a PNG, JPEG, or WEBP image.`
      );
      return;
    }

    // Validate size (10MB max)
    const maxSize = 10 * 1024 * 1024;
    if (file.size > maxSize) {
      setError('File size exceeds the 10MB limit. Please upload a smaller screenshot.');
      return;
    }

    if (imagePreviewUrl) {
      URL.revokeObjectURL(imagePreviewUrl);
    }

    const objectUrl = URL.createObjectURL(file);
    setUploadedFile(file);
    setImagePreviewUrl(objectUrl);

    // Read natural dimensions
    const img = new Image();
    img.onload = () => {
      setImageDimensions({ width: img.naturalWidth, height: img.naturalHeight });
    };
    img.src = objectUrl;

    // Reset downstream state
    setAnalyzeResponse(null);
    setCompileResponse(null);
    setVerificationResult(null);
    setHtmlCode('');
    setCssCode('');
    setJsCode('');
    setDebouncedHtml('');
    setDebouncedCss('');
    setDebouncedJs('');
    setStage('idle');
  };

  const handleLoadDemo = async () => {
    try {
      const demoFile = await fetchDemoImage();
      handleFileUpload(demoFile);
    } catch (err: any) {
      setError(`Failed to load demo image: ${err.message || err}`);
    }
  };

  // Pipeline Execution: Visual Analysis -> Compilation
  const handleGenerate = async () => {
    if (!uploadedFile) {
      setError('Please upload a screenshot first.');
      return;
    }

    setError(null);

    try {
      // 1. Visual Analysis
      setStage('analyzing');
      const analyzeResult = await analyzeImage(uploadedFile);
      setAnalyzeResponse(analyzeResult);

      if (analyzeResult.engine) {
        setActiveEngine(analyzeResult.engine);
      }
      setDemoMode(Boolean(analyzeResult.demo_mode));

      // Update dimensions if returned from viewport
      if (analyzeResult.viewport) {
        setImageDimensions(analyzeResult.viewport);
      }

      // 2. Compilation
      setStage('compiling');
      const compileResult = await compileDetections({
        elements: analyzeResult.elements,
        viewport: analyzeResult.viewport || imageDimensions || { width: 1280, height: 800 },
      });

      setCompileResponse(compileResult);
      if (compileResult.demo_mode) {
        setDemoMode(true);
      }

      // Set generated code
      setHtmlCode(compileResult.html || '');
      setCssCode(compileResult.css || '');
      setJsCode(compileResult.js || '');

      setStage('ready');

      // Auto-open inspector tab
      const hasErrors = compileResult.diagnostics?.some((d) => d.severity === 'error');
      if (hasErrors) {
        setActiveInspectorTab('diagnostics');
      } else {
        setActiveInspectorTab('elements');
      }
      setIsInspectorCollapsed(false);
    } catch (err: any) {
      console.error('Generation pipeline error:', err);
      setStage('error');
      setError(err.message || 'Pipeline compilation failed. Please verify the backend service is running.');
    }
  };

  // Visual Verification Handler
  const handleVerify = async () => {
    if (!uploadedFile) {
      setError('Source image missing. Please upload a screenshot.');
      return;
    }

    const hasCode = !!(htmlCode || cssCode || jsCode);
    if (!hasCode) {
      setError('No generated code to verify. Click "Generate Code" first.');
      return;
    }

    setError(null);
    setStage('verifying');

    try {
      const width = imageDimensions?.width || 1280;
      const height = imageDimensions?.height || 800;

      // Render the current HTML + CSS to an image Blob
      const generatedBlob = await renderHtmlToBlob(htmlCode, cssCode, width, height);

      // Call Verification API
      const result = await verifyOutput(uploadedFile, generatedBlob);
      setVerificationResult(result);
      setActiveInspectorTab('verification');
      setIsInspectorCollapsed(false);
      setStage('ready');
    } catch (err: any) {
      console.error('Visual verification error:', err);
      setStage('ready');
      setError(`Visual verification failed: ${err.message || err}`);
    }
  };

  // Open Refine Modal
  const handleOpenRefine = () => {
    if (!compileResponse?.ir) {
      setError('No Intermediate Representation (IR) available to refine. Generate code first.');
      return;
    }
    setIsRefineModalOpen(true);
  };

  // Execute IR Refinement
  const handleExecuteRefine = async () => {
    setIsRefineModalOpen(false);
    if (!compileResponse?.ir) return;

    setError(null);
    setStage('refining');

    try {
      const refineRes = await refineIR({
        ir: compileResponse.ir,
        source_description: refineInstruction,
        diagnostics: compileResponse.diagnostics,
      });

      // Re-compile with refined IR
      const viewport = analyzeResponse?.viewport || imageDimensions || { width: 1280, height: 800 };
      const compileResult = await compileDetections({
        elements: analyzeResponse?.elements || [],
        viewport: viewport,
      });

      setCompileResponse(compileResult);
      setHtmlCode(compileResult.html || '');
      setCssCode(compileResult.css || '');
      setJsCode(compileResult.js || '');

      setActiveInspectorTab('ir');
      setIsInspectorCollapsed(false);
      setStage('ready');
    } catch (err: any) {
      console.error('Refinement error:', err);
      setStage('ready');
      setError(`IR Refinement failed: ${err.message || err}`);
    }
  };

  // ZIP Download Handler
  const handleDownloadZip = async () => {
    try {
      const zip = new JSZip();
      zip.file('index.html', htmlCode || '<!DOCTYPE html>\n<html><body></body></html>');
      zip.file('style.css', cssCode || '/* UI2Code generated styles */\n');
      zip.file('script.js', jsCode || '// UI2Code generated scripts\n');
      zip.file(
        'README.md',
        `# UI2Code Generated Web Project\n\nGenerated using UI2Code Visual-to-Web Compiler.\n\n## Quick Start\nOpen \`index.html\` in any modern browser to view the page.\n`
      );

      const blob = await zip.generateAsync({ type: 'blob' });
      saveAs(blob, 'ui2code-export.zip');
    } catch (err: any) {
      console.error('ZIP generation error:', err);
      setError(`Failed to create ZIP download: ${err.message || err}`);
    }
  };

  // Reset State Handler
  const handleReset = () => {
    if (imagePreviewUrl) {
      URL.revokeObjectURL(imagePreviewUrl);
    }
    setStage('idle');
    setUploadedFile(null);
    setImagePreviewUrl(null);
    setImageDimensions(null);
    setAnalyzeResponse(null);
    setCompileResponse(null);
    setHtmlCode('');
    setCssCode('');
    setJsCode('');
    setDebouncedHtml('');
    setDebouncedCss('');
    setDebouncedJs('');
    setVerificationResult(null);
    setError(null);
  };

  const hasImage = !!uploadedFile;
  const hasCode = !!(htmlCode || cssCode || jsCode);

  const handleOpenCompilerDefense = () => {
    setIsInspectorCollapsed(false);
    setActiveInspectorTab('compiler');
  };

  return (
    <div className="app-container">
      {/* Engine Status Banner */}
      {demoMode && (
        <div className="demo-banner">
          <div className="demo-banner-content">
            <span>ℹ️</span>
            <span>
              <strong>Static Fixture Mode:</strong> Using bundled sample detections. Upload your own screenshot to analyze it dynamically with the Local CV engine.
            </span>
          </div>
        </div>
      )}
      {!demoMode && activeEngine === 'local_cv' && (
        <div className="demo-banner" style={{ backgroundColor: 'rgba(5, 150, 105, 0.12)', borderColor: 'rgba(5, 150, 105, 0.35)' }}>
          <div className="demo-banner-content">
            <span>🟢</span>
            <span>
              <strong>Free Local Computer Vision Active:</strong> Directly analyzing pixel geometry, cards, buttons, sections, and colors without requiring any external paid API.
            </span>
          </div>
        </div>
      )}

      {/* Error Banner */}
      {error && (
        <div className="error-bar">
          <div className="error-bar-content">
            <span>⚠️</span>
            <span>{error}</span>
          </div>
          <div className="error-bar-actions">
            {uploadedFile && (
              <button className="error-bar-btn" onClick={handleGenerate}>
                Retry Generation
              </button>
            )}
            <button className="error-bar-btn" onClick={() => setError(null)}>
              Dismiss
            </button>
          </div>
        </div>
      )}

      {/* Top Application Bar */}
      <TopBar
        stage={stage}
        demoMode={demoMode}
        engine={activeEngine}
        hasImage={hasImage}
        hasCode={hasCode}
        isVerified={!!verificationResult}
        onUpload={handleFileUpload}
        onGenerate={handleGenerate}
        onVerify={handleVerify}
        onRefine={handleOpenRefine}
        onReset={handleReset}
        onDownload={handleDownloadZip}
        onOpenCompilerDefense={handleOpenCompilerDefense}
      />

      {/* Three-Column Main Workspace */}
      <main className="workspace-main">
        {/* Left: Source Image Panel */}
        <SourcePanel
          imageUrl={imagePreviewUrl}
          dimensions={imageDimensions}
          fileName={uploadedFile?.name || null}
          fileSize={uploadedFile?.size || null}
          elementCount={analyzeResponse?.elements?.length}
          onFileSelect={handleFileUpload}
          onLoadDemo={handleLoadDemo}
        />

        {/* Center: Monaco Code Workspace */}
        <CodeWorkspace
          htmlCode={htmlCode}
          cssCode={cssCode}
          jsCode={jsCode}
          activeTab={activeEditorTab}
          onTabChange={setActiveEditorTab}
          onHtmlChange={setHtmlCode}
          onCssChange={setCssCode}
          onJsChange={setJsCode}
          readOnly={false}
        />

        {/* Right: Sandboxed Live Preview */}
        <PreviewPanel
          iframeRef={iframeRef}
          htmlCode={debouncedHtml}
          cssCode={debouncedCss}
          jsCode={debouncedJs}
          viewportWidth={imageDimensions?.width || 1280}
          viewportHeight={imageDimensions?.height || 800}
        />
      </main>

      {/* Bottom Inspection Panel */}
      <InspectionPanel
        elements={analyzeResponse?.elements}
        ast={compileResponse?.ast}
        ir={compileResponse?.ir}
        diagnostics={compileResponse?.diagnostics}
        optimizationLog={compileResponse?.optimization_log}
        verificationResult={verificationResult}
        activeTab={activeInspectorTab}
        onTabChange={setActiveInspectorTab}
        isCollapsed={isInspectorCollapsed}
        onToggleCollapse={() => setIsInspectorCollapsed((prev) => !prev)}
      />

      {/* Refine IR Modal */}
      {isRefineModalOpen && (
        <div className="modal-overlay" onClick={() => setIsRefineModalOpen(false)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <span className="modal-title">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 20h9" />
                  <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
                </svg>
                Refine Intermediate Representation (IR)
              </span>
              <button
                className="modal-close"
                onClick={() => setIsRefineModalOpen(false)}
              >
                ✕
              </button>
            </div>
            <div className="modal-body">
              <label className="modal-label">
                Provide semantic optimization instructions or layout adjustments:
              </label>
              <textarea
                className="modal-input"
                value={refineInstruction}
                onChange={(e) => setRefineInstruction(e.target.value)}
                placeholder="e.g., Optimize card hierarchy, ensure responsive grid wrap, normalize button paddings..."
              />
            </div>
            <div className="modal-footer">
              <button
                className="topbar-btn"
                onClick={() => setIsRefineModalOpen(false)}
              >
                Cancel
              </button>
              <button
                className="topbar-btn primary"
                onClick={handleExecuteRefine}
              >
                Apply Refinement
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
export default App;
