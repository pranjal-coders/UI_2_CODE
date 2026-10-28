import React from 'react';
import Editor from '@monaco-editor/react';
import './CodeWorkspace.css';

interface CodeWorkspaceProps {
  htmlCode: string;
  cssCode: string;
  jsCode: string;
  activeTab: 'html' | 'css' | 'js';
  onTabChange: (tab: 'html' | 'css' | 'js') => void;
  onHtmlChange: (val: string) => void;
  onCssChange: (val: string) => void;
  onJsChange: (val: string) => void;
  readOnly: boolean;
}

export const CodeWorkspace: React.FC<CodeWorkspaceProps> = ({
  htmlCode,
  cssCode,
  jsCode,
  activeTab,
  onTabChange,
  onHtmlChange,
  onCssChange,
  onJsChange,
  readOnly,
}) => {
  const commonOptions = {
    minimap: { enabled: false },
    fontSize: 13,
    wordWrap: 'on' as const,
    automaticLayout: true,
    readOnly,
    scrollBeyondLastLine: false,
    fontFamily: "'Fira Code', Menlo, Monaco, 'Courier New', monospace",
    lineNumbers: 'on' as const,
    tabSize: 2,
    renderLineHighlight: 'all' as const,
  };

  const getCodeStats = (code: string) => {
    const lines = code ? code.split('\n').length : 0;
    const chars = code ? code.length : 0;
    return `${lines} lines • ${chars} chars`;
  };

  const currentStats =
    activeTab === 'html'
      ? getCodeStats(htmlCode)
      : activeTab === 'css'
      ? getCodeStats(cssCode)
      : getCodeStats(jsCode);

  const hasAnyCode = !!(htmlCode || cssCode || jsCode);

  return (
    <div className="code-workspace">
      <div className="workspace-tabs">
        <div className="tab-group">
          <button
            className={`workspace-tab ${activeTab === 'html' ? 'active' : ''}`}
            onClick={() => onTabChange('html')}
          >
            <span className="tab-badge html">&lt;&gt;</span>
            index.html
          </button>
          <button
            className={`workspace-tab ${activeTab === 'css' ? 'active' : ''}`}
            onClick={() => onTabChange('css')}
          >
            <span className="tab-badge css">#</span>
            style.css
          </button>
          <button
            className={`workspace-tab ${activeTab === 'js' ? 'active' : ''}`}
            onClick={() => onTabChange('js')}
          >
            <span className="tab-badge js">JS</span>
            script.js
          </button>
        </div>

        <div className="workspace-meta">
          {hasAnyCode ? (
            <span>{currentStats}</span>
          ) : (
            <span>Ready for compiler output</span>
          )}
        </div>
      </div>

      <div className="editor-wrapper">
        {!hasAnyCode && (
          <div className="workspace-placeholder">
            <div className="placeholder-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="16 18 22 12 16 6" />
                <polyline points="8 6 2 12 8 18" />
              </svg>
            </div>
            <div className="placeholder-title">No Code Generated Yet</div>
            <div className="placeholder-text">
              Upload a screenshot and click "Generate Code" to start compilation.
            </div>
          </div>
        )}

        <div className={`editor-pane ${activeTab === 'html' ? '' : 'hidden'}`}>
          <Editor
            height="100%"
            language="html"
            theme="vs-dark"
            value={htmlCode}
            onChange={(val) => onHtmlChange(val || '')}
            options={commonOptions}
          />
        </div>

        <div className={`editor-pane ${activeTab === 'css' ? '' : 'hidden'}`}>
          <Editor
            height="100%"
            language="css"
            theme="vs-dark"
            value={cssCode}
            onChange={(val) => onCssChange(val || '')}
            options={commonOptions}
          />
        </div>

        <div className={`editor-pane ${activeTab === 'js' ? '' : 'hidden'}`}>
          <Editor
            height="100%"
            language="javascript"
            theme="vs-dark"
            value={jsCode}
            onChange={(val) => onJsChange(val || '')}
            options={commonOptions}
          />
        </div>
      </div>
    </div>
  );
};
