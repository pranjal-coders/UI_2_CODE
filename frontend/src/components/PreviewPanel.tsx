import React, { useState, useMemo } from 'react';
import './PreviewPanel.css';

interface PreviewPanelProps {
  htmlCode: string;
  cssCode: string;
  jsCode: string;
  viewportWidth?: number;
  viewportHeight?: number;
  onRefresh?: () => void;
  iframeRef?: React.RefObject<HTMLIFrameElement>;
}

export function buildSrcDoc(html: string, css: string, js: string): string {
  const csp = `<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; img-src data: blob:;">`;

  if (!html && !css && !js) {
    return '';
  }

  const safeHtml = html || '<div id="root"></div>';
  const styleBlock = `<style>\n${css || ''}\n</style>`;
  const scriptBlock = `<script>\nwindow.onerror = function(msg, url, line) {\n  console.warn('Preview JS Error:', msg, 'at line', line);\n  return true;\n};\ntry {\n${js || ''}\n} catch(e) { console.error(e); }\n</script>`;

  if (safeHtml.includes('<!DOCTYPE') || safeHtml.includes('<html')) {
    let doc = safeHtml;
    if (doc.includes('</head>')) {
      doc = doc.replace('</head>', `${csp}\n${styleBlock}\n</head>`);
    } else if (doc.includes('<body')) {
      doc = doc.replace('<body', `<head>${csp}\n${styleBlock}</head><body`);
    } else {
      doc = `${csp}\n${styleBlock}\n${doc}`;
    }

    if (doc.includes('</body>')) {
      doc = doc.replace('</body>', `${scriptBlock}\n</body>`);
    } else {
      doc = `${doc}\n${scriptBlock}`;
    }
    return doc;
  }

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  ${csp}
  ${styleBlock}
</head>
<body>
  ${safeHtml}
  ${scriptBlock}
</body>
</html>`;
}

export const PreviewPanel: React.FC<PreviewPanelProps> = ({
  htmlCode,
  cssCode,
  jsCode,
  viewportWidth = 1280,
  viewportHeight = 800,
  onRefresh,
  iframeRef,
}) => {
  const [refreshKey, setRefreshKey] = useState<number>(0);
  const [scale, setScale] = useState<number>(100);

  const hasCode = !!(htmlCode || cssCode || jsCode);

  const srcDoc = useMemo(() => {
    return buildSrcDoc(htmlCode, cssCode, jsCode);
  }, [htmlCode, cssCode, jsCode]);

  const handleRefreshClick = () => {
    setRefreshKey((prev) => prev + 1);
    if (onRefresh) {
      onRefresh();
    }
  };

  return (
    <section className="preview-panel">
      <div className="preview-header">
        <div className="preview-title">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
            <line x1="8" y1="21" x2="16" y2="21" />
            <line x1="12" y1="17" x2="12" y2="21" />
          </svg>
          Live Preview
        </div>

        <div className="preview-controls">
          <span className="viewport-badge" title="Source Viewport">
            {viewportWidth} × {viewportHeight} px
          </span>

          <select
            className="preview-icon-btn"
            value={scale}
            onChange={(e) => setScale(Number(e.target.value))}
            title="Scale Preview"
          >
            <option value={50}>50%</option>
            <option value={75}>75%</option>
            <option value={100}>100%</option>
            <option value={125}>125%</option>
          </select>

          <button
            className="preview-icon-btn"
            onClick={handleRefreshClick}
            title="Force refresh iframe sandbox"
            disabled={!hasCode}
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67" />
            </svg>
            Refresh
          </button>
        </div>
      </div>

      <div className="preview-canvas-wrapper">
        {!hasCode ? (
          <div className="preview-placeholder">
            <div className="preview-placeholder-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
                <line x1="8" y1="21" x2="16" y2="21" />
                <line x1="12" y1="17" x2="12" y2="21" />
              </svg>
            </div>
            <div style={{ fontWeight: 600, color: '#c0caf5' }}>
              Sandboxed Preview Idle
            </div>
            <div style={{ fontSize: 12, maxWidth: 300 }}>
              The rendered webpage with embedded styles and isolated scripts will appear here.
            </div>
          </div>
        ) : (
          <div
            className="preview-viewport-frame"
            style={{
              width: `${Math.round(viewportWidth * (scale / 100))}px`,
              height: `${Math.round(viewportHeight * (scale / 100))}px`,
              minHeight: '360px',
            }}
          >
            <iframe
              key={refreshKey}
              ref={iframeRef}
              title="Sandboxed Live Preview"
              srcDoc={srcDoc}
              sandbox="allow-scripts"
              className="preview-iframe"
            />
          </div>
        )}
      </div>
    </section>
  );
};
