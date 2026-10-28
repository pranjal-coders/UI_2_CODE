import React, { useRef } from 'react';
import { PipelineStage } from '../types/api';
import './TopBar.css';

interface TopBarProps {
  stage: PipelineStage;
  demoMode: boolean;
  engine?: string;
  hasImage: boolean;
  hasCode: boolean;
  isVerified?: boolean;
  onUpload: (file: File) => void;
  onGenerate: () => void;
  onVerify: () => void;
  onRefine: () => void;
  onReset: () => void;
  onDownload: () => void;
  onOpenCompilerDefense?: () => void;
}

export const TopBar: React.FC<TopBarProps> = ({
  stage,
  demoMode,
  engine = 'local_cv',
  hasImage,
  hasCode,
  isVerified = false,
  onUpload,
  onGenerate,
  onVerify,
  onRefine,
  onReset,
  onDownload,
  onOpenCompilerDefense,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      onUpload(file);
      // Reset input value so same file can be re-uploaded if desired
      e.target.value = '';
    }
  };

  const isGenerating = stage === 'analyzing' || stage === 'compiling';
  const isVerifying = stage === 'verifying';
  const isRefining = stage === 'refining';
  const isBusy = isGenerating || isVerifying || isRefining || stage === 'uploading';

  return (
    <header className="topbar">
      <div className="topbar-brand">
        <div className="topbar-logo">
          <span className="topbar-logo-icon">&lt;/&gt;</span>
          <span>UI2Code</span>
        </div>
        <span className="topbar-subtitle">Visual-to-Web Compiler</span>
        {engine === 'local_cv' && !demoMode && (
          <span
            className="badge-demo"
            style={{ backgroundColor: '#059669', color: '#ffffff' }}
            title="Running 100% free, local Computer Vision analysis using OpenCV and Pillow"
          >
            ● Local CV (Free)
          </span>
        )}
        {engine === 'gemini' && (
          <span
            className="badge-demo"
            style={{ backgroundColor: '#4f46e5', color: '#ffffff' }}
            title="Running Google Gemini Multimodal Vision API"
          >
            ● Gemini Vision
          </span>
        )}
        {demoMode && (
          <span className="badge-demo" title="Running in static fixture demo mode">
            ● Fixture Demo
          </span>
        )}
      </div>

      <div className="topbar-status">
        <span className={`badge-stage ${stage}`}>
          {isBusy && <span className="spinner" />}
          Stage: {stage.toUpperCase()}
        </span>
      </div>

      <div className="topbar-actions">
        <input
          type="file"
          ref={fileInputRef}
          style={{ display: 'none' }}
          accept="image/png,image/jpeg,image/webp"
          onChange={handleFileChange}
        />

        <button
          className="topbar-btn"
          onClick={() => fileInputRef.current?.click()}
          disabled={isBusy}
          title="Upload target UI screenshot"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
          Upload Screenshot
        </button>

        <button
          className="topbar-btn primary"
          onClick={onGenerate}
          disabled={!hasImage || isBusy}
          title={!hasImage ? 'Upload an image first' : 'Analyze elements & compile to HTML/CSS/JS'}
        >
          {isGenerating ? (
            <>
              <span className="spinner" />
              {stage === 'analyzing' ? 'Analyzing...' : 'Compiling...'}
            </>
          ) : (
            <>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polygon points="5 3 19 12 5 21 5 3" />
              </svg>
              Generate Code
            </>
          )}
        </button>

        <button
          className="topbar-btn accent"
          onClick={onVerify}
          disabled={!hasCode || isBusy}
          title={!hasCode ? 'Generate code first' : 'Run pixel verification against source image'}
        >
          {isVerifying ? (
            <>
              <span className="spinner" />
              Verifying...
            </>
          ) : (
            <>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                <polyline points="22 4 12 14.01 9 11.01" />
              </svg>
              Verify Visuals
            </>
          )}
        </button>

        <button
          className="topbar-btn"
          onClick={onRefine}
          disabled={!hasCode || isBusy}
          title="Apply bounded IR semantic optimization and refinements"
        >
          {isRefining ? (
            <>
              <span className="spinner" />
              Refining...
            </>
          ) : (
            <>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 20h9" />
                <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
              </svg>
              Refine IR
            </>
          )}
        </button>

        <button
          className="topbar-btn"
          onClick={onDownload}
          disabled={!hasCode || isBusy}
          title="Download generated website as a ZIP file"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="7 10 12 15 17 10" />
            <line x1="12" y1="15" x2="12" y2="3" />
          </svg>
          Download ZIP
        </button>

        <button
          className="topbar-btn"
          onClick={onOpenCompilerDefense}
          title="Inspect Compiler Pipeline Architecture & Academic Viva Defense (BCSE307P)"
          style={{ borderColor: 'rgba(56, 189, 248, 0.4)', color: '#38bdf8' }}
        >
          🎓 Compiler Defense
        </button>

        <button
          className="topbar-btn danger"
          onClick={onReset}
          disabled={isBusy || (!hasImage && !hasCode)}
          title="Reset entire workspace"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
            <path d="M3 3v5h5" />
          </svg>
          Reset
        </button>
      </div>
    </header>
  );
};
