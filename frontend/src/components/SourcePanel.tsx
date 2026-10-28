import React, { useState, useRef } from 'react';
import './SourcePanel.css';

interface SourcePanelProps {
  imageUrl: string | null;
  dimensions: { width: number; height: number } | null;
  fileName: string | null;
  fileSize: number | null;
  elementCount?: number;
  onFileSelect?: (file: File) => void;
  onLoadDemo?: () => void;
}

export const SourcePanel: React.FC<SourcePanelProps> = ({
  imageUrl,
  dimensions,
  fileName,
  fileSize,
  elementCount,
  onFileSelect,
  onLoadDemo,
}) => {
  const [isDragActive, setIsDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);

    const files = e.dataTransfer.files;
    if (files && files.length > 0 && onFileSelect) {
      onFileSelect(files[0]);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0 && onFileSelect) {
      onFileSelect(files[0]);
      e.target.value = '';
    }
  };

  const formatFileSize = (bytes: number | null): string => {
    if (!bytes) return '0 KB';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  return (
    <aside className="source-panel">
      <div className="panel-header">
        <div className="panel-header-title">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
            <circle cx="8.5" cy="8.5" r="1.5" />
            <polyline points="21 15 16 10 5 21" />
          </svg>
          Source Screenshot
        </div>
        {elementCount !== undefined && (
          <span className="meta-badge-success">{elementCount} Detections</span>
        )}
      </div>

      <div className="panel-content">
        <input
          type="file"
          ref={fileInputRef}
          style={{ display: 'none' }}
          accept="image/png,image/jpeg,image/webp"
          onChange={handleFileInputChange}
        />

        {!imageUrl ? (
          <div>
            <div
              className={`dropzone ${isDragActive ? 'drag-active' : ''}`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <div className="dropzone-icon">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                  <polyline points="17 8 12 3 7 8" />
                  <line x1="12" y1="3" x2="12" y2="15" />
                </svg>
              </div>
              <div className="dropzone-title">Upload Screenshot</div>
              <div className="dropzone-subtitle">
                Drag & drop a web page screenshot here, or click to browse
              </div>
              <div className="dropzone-hint">PNG, JPEG, WEBP • Max 10MB</div>
            </div>

            {onLoadDemo && (
              <div style={{ marginTop: '16px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <div style={{ fontSize: '11px', color: '#888899', textAlign: 'center' }}>— or test with bundled sample —</div>
                <button
                  type="button"
                  className="replace-button"
                  style={{ justifyContent: 'center', width: '100%' }}
                  onClick={onLoadDemo}
                >
                  ⚡ Load Sample Landing Page
                </button>
              </div>
            )}
          </div>
        ) : (
          <div className="preview-container">
            <div className="image-frame">
              <img
                src={imageUrl}
                alt={fileName || 'Source UI screenshot'}
                className="source-image"
              />
            </div>

            <div className="meta-card">
              <div className="meta-row">
                <span className="meta-label">File Name</span>
                <span className="meta-value meta-filename" title={fileName || ''}>
                  {fileName || 'screenshot.png'}
                </span>
              </div>

              <div className="meta-row">
                <span className="meta-label">Dimensions</span>
                <span className="meta-value">
                  {dimensions ? `${dimensions.width} × ${dimensions.height} px` : 'Detecting...'}
                </span>
              </div>

              <div className="meta-row">
                <span className="meta-label">File Size</span>
                <span className="meta-value">{formatFileSize(fileSize)}</span>
              </div>

              <div className="meta-row">
                <span className="meta-label">Detections</span>
                <span className="meta-value">
                  {elementCount !== undefined ? (
                    <span className="meta-badge-success">{elementCount} elements</span>
                  ) : (
                    <span className="meta-badge-pending">Not analyzed</span>
                  )}
                </span>
              </div>
            </div>

            <button
              className="replace-button"
              onClick={() => fileInputRef.current?.click()}
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
              Replace Image
            </button>
          </div>
        )}
      </div>
    </aside>
  );
};
