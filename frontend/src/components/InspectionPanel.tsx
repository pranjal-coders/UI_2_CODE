import React, { useState } from 'react';
import {
  DetectedElement,
  Diagnostic,
  OptimizationEvent,
  VerificationResult,
} from '../types/api';
import './InspectionPanel.css';

interface InspectionPanelProps {
  elements?: DetectedElement[];
  ast?: any;
  ir?: any;
  diagnostics?: Diagnostic[];
  optimizationLog?: OptimizationEvent[];
  verificationResult?: VerificationResult | null;
  activeTab: string;
  onTabChange: (tab: string) => void;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
}

// Collapsible JSON Tree Viewer
export const JsonNodeViewer: React.FC<{ data: any; name?: string; depth?: number }> = ({
  data,
  name,
  depth = 0,
}) => {
  if (data === null) {
    return (
      <div className="json-node">
        {name && <span className="json-key">{name}: </span>}
        <span className="json-null">null</span>
      </div>
    );
  }

  if (data === undefined) {
    return (
      <div className="json-node">
        {name && <span className="json-key">{name}: </span>}
        <span className="json-null">undefined</span>
      </div>
    );
  }

  if (typeof data === 'string') {
    return (
      <div className="json-node">
        {name && <span className="json-key">{name}: </span>}
        <span className="json-string">"{data}"</span>
      </div>
    );
  }

  if (typeof data === 'number') {
    return (
      <div className="json-node">
        {name && <span className="json-key">{name}: </span>}
        <span className="json-number">{data}</span>
      </div>
    );
  }

  if (typeof data === 'boolean') {
    return (
      <div className="json-node">
        {name && <span className="json-key">{name}: </span>}
        <span className="json-boolean">{data ? 'true' : 'false'}</span>
      </div>
    );
  }

  if (Array.isArray(data)) {
    const defaultOpen = depth < 2;
    return (
      <div className="json-node">
        <details className="json-details" open={defaultOpen}>
          <summary className="json-summary">
            {name ? <span className="json-key">{name}: </span> : null}
            <span>[{data.length} items]</span>
          </summary>
          {data.map((item, idx) => (
            <JsonNodeViewer key={idx} data={item} name={String(idx)} depth={depth + 1} />
          ))}
        </details>
      </div>
    );
  }

  if (typeof data === 'object') {
    const keys = Object.keys(data);
    const defaultOpen = depth < 2;
    return (
      <div className="json-node">
        <details className="json-details" open={defaultOpen}>
          <summary className="json-summary">
            {name ? <span className="json-key">{name}: </span> : null}
            <span>{'{'}{keys.length} keys{'}'}</span>
          </summary>
          {keys.map((key) => (
            <JsonNodeViewer key={key} data={data[key]} name={key} depth={depth + 1} />
          ))}
        </details>
      </div>
    );
  }

  return (
    <div className="json-node">
      {name && <span className="json-key">{name}: </span>}
      <span>{String(data)}</span>
    </div>
  );
};

export const JsonTree: React.FC<{ data: any; title?: string }> = ({ data, title }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(JSON.stringify(data, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!data) {
    return (
      <div className="empty-inspection-state">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="8" x2="12" y2="12" />
          <line x1="12" y1="16" x2="12.01" y2="16" />
        </svg>
        <span>No {title || 'data'} generated. Run pipeline to inspect representation.</span>
      </div>
    );
  }

  return (
    <div className="json-tree-container">
      <div className="json-actions">
        <button className="json-copy-btn" onClick={handleCopy}>
          {copied ? '✓ Copied' : 'Copy JSON'}
        </button>
      </div>
      <JsonNodeViewer data={data} />
    </div>
  );
};

export const InspectionPanel: React.FC<InspectionPanelProps> = ({
  elements,
  ast,
  ir,
  diagnostics = [],
  optimizationLog = [],
  verificationResult,
  activeTab,
  onTabChange,
  isCollapsed,
  onToggleCollapse,
}) => {
  const errorCount = diagnostics.filter((d) => d.severity === 'error').length;
  const warningCount = diagnostics.filter((d) => d.severity === 'warning').length;

  return (
    <footer
      className={`inspection-panel ${isCollapsed ? 'collapsed' : ''}`}
      style={{ height: isCollapsed ? '38px' : '280px' }}
    >
      <div className="inspection-header">
        <div className="inspection-tabs">
          <button
            className={`inspection-tab ${activeTab === 'elements' ? 'active' : ''}`}
            onClick={() => onTabChange('elements')}
          >
            Elements
            {elements && elements.length > 0 && (
              <span className="tab-count-badge">{elements.length}</span>
            )}
          </button>

          <button
            className={`inspection-tab ${activeTab === 'ast' ? 'active' : ''}`}
            onClick={() => onTabChange('ast')}
          >
            UI AST
          </button>

          <button
            className={`inspection-tab ${activeTab === 'ir' ? 'active' : ''}`}
            onClick={() => onTabChange('ir')}
          >
            UI IR
          </button>

          <button
            className={`inspection-tab ${activeTab === 'diagnostics' ? 'active' : ''}`}
            onClick={() => onTabChange('diagnostics')}
          >
            Diagnostics
            {diagnostics.length > 0 && (
              <span className={`tab-count-badge ${errorCount > 0 ? 'error' : ''}`}>
                {diagnostics.length}
              </span>
            )}
          </button>

          <button
            className={`inspection-tab ${activeTab === 'optimization' ? 'active' : ''}`}
            onClick={() => onTabChange('optimization')}
          >
            Optimization
            {optimizationLog.length > 0 && (
              <span className="tab-count-badge">{optimizationLog.length}</span>
            )}
          </button>

          <button
            className={`inspection-tab ${activeTab === 'verification' ? 'active' : ''}`}
            onClick={() => onTabChange('verification')}
          >
            Verification
            {verificationResult && (
              <span className="tab-count-badge">✓</span>
            )}
          </button>

          <button
            className={`inspection-tab compiler-tab ${activeTab === 'compiler' ? 'active' : ''}`}
            onClick={() => onTabChange('compiler')}
            title="Compiler Design Principles & Academic Viva Defense"
          >
            🎓 Compiler Defense
          </button>
        </div>

        <div className="inspection-controls">
          <button
            className="collapse-btn"
            onClick={onToggleCollapse}
            title={isCollapsed ? 'Expand inspector' : 'Collapse inspector'}
            aria-label={isCollapsed ? 'Expand inspector' : 'Collapse inspector'}
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              style={{
                transform: isCollapsed ? 'rotate(180deg)' : 'rotate(0deg)',
                transition: 'transform 0.2s ease',
              }}
            >
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </button>
        </div>
      </div>

      {!isCollapsed && (
        <div className="inspection-body">
          {activeTab === 'elements' && (
            <>
              {!elements || elements.length === 0 ? (
                <div className="empty-inspection-state">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                    <line x1="9" y1="9" x2="15" y2="15" />
                    <line x1="15" y1="9" x2="9" y2="15" />
                  </svg>
                  <span>No elements detected yet. Upload a screenshot and run analysis.</span>
                </div>
              ) : (
                <div className="elements-table-wrapper">
                  <table className="elements-table">
                    <thead>
                      <tr>
                        <th>ID</th>
                        <th>Type</th>
                        <th>Text Content</th>
                        <th>Bounding Box</th>
                        <th>Confidence</th>
                        <th>Hints</th>
                      </tr>
                    </thead>
                    <tbody>
                      {elements.map((el) => {
                        const confPercent = el.confidence
                          ? Math.round(el.confidence * 100)
                          : 100;
                        const confClass =
                          confPercent >= 80
                            ? 'confidence-high'
                            : confPercent >= 50
                            ? 'confidence-med'
                            : 'confidence-low';

                        return (
                          <tr key={el.id}>
                            <td className="elem-id">{el.id}</td>
                            <td>
                              <span className="elem-type-pill">{el.type}</span>
                            </td>
                            <td>{el.text || <span style={{ color: '#565f89' }}>—</span>}</td>
                            <td className="elem-bbox">
                              [{el.bbox.x}, {el.bbox.y}, {el.bbox.width} × {el.bbox.height}]
                            </td>
                            <td className={`elem-confidence ${confClass}`}>
                              {confPercent}%
                            </td>
                            <td style={{ color: '#7982a9', fontSize: '11px' }}>
                              {el.relation_hints && el.relation_hints.length > 0
                                ? el.relation_hints.join(', ')
                                : '—'}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          )}

          {activeTab === 'ast' && <JsonTree data={ast} title="UI AST" />}

          {activeTab === 'ir' && <JsonTree data={ir} title="UI Intermediate Representation" />}

          {activeTab === 'diagnostics' && (
            <>
              {diagnostics.length === 0 ? (
                <div className="empty-inspection-state">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                    <polyline points="22 4 12 14.01 9 11.01" />
                  </svg>
                  <span>No semantic issues or diagnostics reported. Clean compilation!</span>
                </div>
              ) : (
                <div className="diagnostics-list">
                  {diagnostics.map((diag, index) => {
                    const icon =
                      diag.severity === 'error'
                        ? '🔴'
                        : diag.severity === 'warning'
                        ? '🟡'
                        : '🔵';

                    return (
                      <div key={index} className={`diagnostic-item ${diag.severity}`}>
                        <div className="diagnostic-icon">{icon}</div>
                        <div className="diagnostic-content">
                          <div className="diagnostic-header">
                            <span className="diagnostic-code">{diag.code}</span>
                            {diag.node_id && (
                              <span className="diagnostic-node">Node: {diag.node_id}</span>
                            )}
                          </div>
                          <div className="diagnostic-message">{diag.message}</div>
                          {diag.suggestion && (
                            <div className="diagnostic-suggestion">
                              💡 Suggestion: {diag.suggestion}
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </>
          )}

          {activeTab === 'optimization' && (
            <>
              {optimizationLog.length === 0 ? (
                <div className="empty-inspection-state">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="3" />
                    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
                  </svg>
                  <span>No optimization passes recorded yet. Run compiler pipeline to view passes.</span>
                </div>
              ) : (
                <div className="opt-list">
                  {optimizationLog.map((opt, idx) => (
                    <div key={idx} className="opt-card">
                      <div className="opt-header">
                        <span className="opt-pass-name">{opt.pass_name}</span>
                        <span className="opt-badge">{opt.changed_count} changed</span>
                      </div>
                      <div className="opt-desc">{opt.description}</div>
                      {(opt.before_summary || opt.after_summary) && (
                        <div className="opt-summary-grid">
                          <div className="opt-summary-item">
                            Before: <span className="opt-summary-val">{opt.before_summary}</span>
                          </div>
                          <div className="opt-summary-item">
                            After: <span className="opt-summary-val">{opt.after_summary}</span>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </>
          )}

          {activeTab === 'verification' && (
            <>
              {!verificationResult ? (
                <div className="empty-inspection-state">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="11" cy="11" r="8" />
                    <line x1="21" y1="21" x2="16.65" y2="16.65" />
                  </svg>
                  <span>Verification not run yet. Click "Verify Visuals" in the top bar.</span>
                </div>
              ) : (
                <div>
                  <div className="verif-grid">
                    <div className="verif-card">
                      <span className="verif-card-label">Mean Absolute Error (MAE)</span>
                      <span className="verif-card-value">
                        {verificationResult.mae.toFixed(2)}
                      </span>
                    </div>

                    <div className="verif-card">
                      <span className="verif-card-label">Changed Pixel %</span>
                      <span className="verif-card-value">
                        {verificationResult.changed_pixel_percent.toFixed(2)}%
                      </span>
                    </div>

                    {verificationResult.similarity_estimate !== undefined && (
                      <div className="verif-card">
                        <span className="verif-card-label">Similarity Score</span>
                        <span className="verif-card-value">
                          {(verificationResult.similarity_estimate * 100).toFixed(1)}%
                        </span>
                      </div>
                    )}

                    <div className="verif-card">
                      <span className="verif-card-label">Comparison Dimensions</span>
                      <span className="verif-card-value" style={{ fontSize: '15px' }}>
                        {verificationResult.width} × {verificationResult.height} px
                      </span>
                    </div>
                  </div>

                  {verificationResult.metric_explanation && (
                    <div className="verif-explanation">
                      <strong>Analysis:</strong> {verificationResult.metric_explanation}
                    </div>
                  )}

                  {verificationResult.diff_image_base64 && (
                    <div className="diff-image-wrapper">
                      <div style={{ fontSize: 11, color: '#7982a9', textTransform: 'uppercase' }}>
                        Pixel Diff Visualization
                      </div>
                      <img
                        src={`data:image/png;base64,${verificationResult.diff_image_base64}`}
                        alt="Pixel difference heatmap"
                        className="diff-image"
                      />
                    </div>
                  )}
                </div>
              )}
            </>
          )}

          {activeTab === 'compiler' && (
            <div className="compiler-defense-view">
              <div className="defense-banner">
                <div className="defense-banner-title">
                  <span className="defense-badge">BCSE307P Lab Defense</span>
                  <h3>Why UI2Code is a Deterministic Compiler, NOT Generative AI</h3>
                </div>
                <p className="defense-banner-desc">
                  This system implements the classical 6-phase compiler pipeline from the Dragon Book (Aho, Lam, Sethi, Ullman).
                  Rather than using an opaque black-box LLM that hallucinates non-existent elements, UI2Code utilizes computer vision
                  as a formal visual scanner to extract discrete tokens, builds a typed AST, lowers to an inspectable IR, executes 5 optimization
                  passes, and deterministically generates standard web code.
                </p>
              </div>

              <div className="defense-section-title">
                <span>Phase-by-Phase Compiler Design Architecture</span>
              </div>

              <div className="phases-grid">
                <div className="phase-card">
                  <div className="phase-num">PHASE 1</div>
                  <h4>Lexical Analysis (Scanner)</h4>
                  <p className="phase-module">Module: <code>app/vision/local_cv_provider.py</code></p>
                  <p className="phase-desc">
                    Scans the 2D pixel matrix <em>I &isin; &Ropf;<sup>H&times;W&times;3</sup></em> using OpenCV contour detection,
                    color quantization, and Sobel edge energy. Transforms continuous pixels into a stream of discrete <strong>Visual Tokens</strong>
                    (<code>DetectedElement</code>) with bounding boxes, dominant colors, and element types.
                  </p>
                  <div className="phase-token">Token = &lang;Type, BBox, StyleAttributes, Confidence&rang;</div>
                </div>

                <div className="phase-card">
                  <div className="phase-num">PHASE 2</div>
                  <h4>Syntax Analysis (Parser)</h4>
                  <p className="phase-module">Module: <code>app/compiler/ast_builder.py</code></p>
                  <p className="phase-desc">
                    Parses the flat visual token stream into a hierarchical <strong>UI AST</strong> (<code>UIASTNode</code>)
                    using a formal 2D Spatial Containment Grammar. Resolves parent-child relationships via bounding box inclusion
                    <em>bbox(child) &sube; bbox(parent)</em> and enforces type nesting grammar rules (e.g. <em>Button &nsub; Button</em>).
                  </p>
                  <div className="phase-token">Grammar: 2D Spatial Containment &amp; Type Rules</div>
                </div>

                <div className="phase-card">
                  <div className="phase-num">PHASE 3</div>
                  <h4>Intermediate Representation</h4>
                  <p className="phase-module">Module: <code>app/compiler/ir_builder.py</code></p>
                  <p className="phase-desc">
                    Lowers the UI AST into canonical <strong>UI IR</strong> (<code>UIIRNode</code> / <code>UIIR</code>).
                    Infers target-independent layout strategies (Flexbox Row, Flexbox Column, Grid, Flow), normalizes
                    coordinates, and generates tokenized atomic CSS class identifiers.
                  </p>
                  <div className="phase-token">IR: Canonical Layout Tree + Style Tokens</div>
                </div>

                <div className="phase-card">
                  <div className="phase-num">PHASE 4</div>
                  <h4>Semantic Analysis</h4>
                  <p className="phase-module">Module: <code>app/compiler/semantic_analyzer.py</code></p>
                  <p className="phase-desc">
                    Static analysis pass that checks DOM accessibility and structural semantics: cyclic containment prevention,
                    duplicate ID detection, invalid element nesting, interactive element text presence, and noise bbox pruning.
                  </p>
                  <div className="phase-token">Output: Diagnostic Warnings, Errors &amp; Hints</div>
                </div>

                <div className="phase-card">
                  <div className="phase-num">PHASE 5</div>
                  <h4>Compiler Optimization Passes</h4>
                  <p className="phase-module">Module: <code>app/compiler/optimizations.py</code></p>
                  <p className="phase-desc">
                    Executes 5 deterministic IR-to-IR optimization passes:
                  </p>
                  <ul className="opt-list">
                    <li><strong>Style Normalization:</strong> Canonicalizes hex colors and measurement units.</li>
                    <li><strong>CSS Common Subexpression Elimination:</strong> Hoists identical style dicts into shared token classes.</li>
                    <li><strong>Repeated Pattern Consolidation:</strong> Identifies isomorphic card/item structures.</li>
                    <li><strong>Dead Wrapper Elimination:</strong> Prunes redundant single-child container nodes.</li>
                    <li><strong>Layout Simplification:</strong> Hoists uniform flex gaps to parents.</li>
                  </ul>
                </div>

                <div className="phase-card">
                  <div className="phase-num">PHASE 6</div>
                  <h4>Target Code Generation</h4>
                  <p className="phase-module">Module: <code>app/compiler/code_generator.py</code></p>
                  <p className="phase-desc">
                    Deterministic code emitter translating optimized IR into clean, W3C-compliant target code:
                    semantic HTML5 with data traceability attributes (<code>data-ui2c-id</code>), organized CSS3 with shared tokens,
                    and structured vanilla JavaScript.
                  </p>
                  <div className="phase-token">Targets: HTML5 + CSS3 + Vanilla JavaScript</div>
                </div>
              </div>

              <div className="defense-section-title">
                <span>Direct Comparison: Compiler Architecture vs. Generative AI</span>
              </div>

              <div className="comparison-table-wrapper">
                <table className="comparison-table">
                  <thead>
                    <tr>
                      <th>Compiler Metric</th>
                      <th>UI2Code (Compiler + Computer Vision)</th>
                      <th>Generative AI (LLMs / Vision API)</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td><strong>Execution Model</strong></td>
                      <td>Deterministic multi-pass pipeline (finite-state lexer, AST parser, IR optimizations).</td>
                      <td>Probabilistic next-token sampling with non-deterministic temperature.</td>
                    </tr>
                    <tr>
                      <td><strong>Hallucination Risk</strong></td>
                      <td><span className="badge-pass">ZERO</span> &mdash; Only outputs elements visually proven by contours/pixels.</td>
                      <td><span className="badge-fail">HIGH</span> &mdash; Frequently invents synthetic text, fake navbars, and headers.</td>
                    </tr>
                    <tr>
                      <td><strong>Intermediate Representation</strong></td>
                      <td>Explicit, typed, inspectable <code>UIIR</code> (visible in inspection tabs).</td>
                      <td>Black-box latent space (uninterpretable vector weights).</td>
                    </tr>
                    <tr>
                      <td><strong>Optimization Guarantees</strong></td>
                      <td>Formal Common Subexpression Elimination (CSE) &amp; dead-code pruning.</td>
                      <td>Unverifiable rewrites with possible semantic drift.</td>
                    </tr>
                    <tr>
                      <td><strong>Cost &amp; Availability</strong></td>
                      <td>100% Free, offline, runnable locally on CPU with OpenCV &amp; Python.</td>
                      <td>Requires paid cloud API keys ($$$ per image), network latency, rate limits.</td>
                    </tr>
                    <tr>
                      <td><strong>Formal Verification</strong></td>
                      <td>Built-in Mean Absolute Error (MAE) and pixel difference verification.</td>
                      <td>None &mdash; relies purely on visual eyeballing by human.</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <div className="defense-section-title">
                <span>Viva Examination Q&amp;A (Cheat Sheet for Faculty Review)</span>
              </div>

              <div className="viva-faq-list">
                <div className="viva-faq-item">
                  <div className="viva-q">Q1: "Why does a screenshot count as compiler source code?"</div>
                  <div className="viva-a">
                    In traditional compilers, source code is a 1D sequence of characters. In visual compilation, source code is a 2D matrix of RGB pixel values
                    <em>I &isin; &Ropf;<sup>H&times;W&times;3</sup></em>. Our Lexer (the Computer Vision scanner) extracts tokens based on spatial contours and color gradients,
                    just as a character-based lexer matches regular expressions to produce tokens.
                  </div>
                </div>

                <div className="viva-faq-item">
                  <div className="viva-q">Q2: "What is your grammar and parser?"</div>
                  <div className="viva-a">
                    Our grammar is a 2D Spatial Containment Grammar: <code>Page &rarr; (Header | Section | Card | Button | Text)*</code>.
                    A parent node derives child elements based on bounding box inclusion (<em>child.bbox &sube; parent.bbox</em>).
                    The AST Builder applies type constraint rules (for instance, a Button is a leaf node and cannot contain a Header or Page).
                  </div>
                </div>

                <div className="viva-faq-item">
                  <div className="viva-q">Q3: "Why use an Intermediate Representation (IR) instead of outputting HTML directly?"</div>
                  <div className="viva-a">
                    Emitting HTML directly tightly couples visual scanning to target syntax, preventing layout inference and optimization.
                    With UIIR, the pipeline is modular: we can perform Common Subexpression Elimination on CSS styles, dead wrapper pruning,
                    and easily retarget the backend to emit React, Vue, or Flutter without changing the visual scanner or parser.
                  </div>
                </div>

                <div className="viva-faq-item">
                  <div className="viva-q">Q4: "What optimizations have you implemented?"</div>
                  <div className="viva-a">
                    We implemented 5 deterministic passes: (1) Style Normalization (value canonicalization), (2) CSS Deduplication (CSE for identical styles),
                    (3) Repeated Pattern Recognition (clustering isomorphic items), (4) Safe Wrapper Simplification (dead-node elimination),
                    and (5) Layout Simplification (hoisting flex gaps to parents).
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </footer>
  );
};
