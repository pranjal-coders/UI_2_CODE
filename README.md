# UI2Code: A Compiler-Assisted Visual-to-Web Code Generation System

A desktop-first web application that accepts a screenshot of a web page and generates editable HTML, CSS, and JavaScript through a compiler-inspired pipeline with inspectable intermediate representations.

## Architecture

```
Screenshot → Visual Analysis → Structured Detections
    → UI AST → UI IR → Semantic Analysis → Optimization
    → Code Generation (HTML + CSS + JS) → Sandboxed Preview
    → Visual Verification → Bounded Refinement
```

### Pipeline Stages
1. **Screenshot Ingestion** — validates, normalizes, and retains original dimensions
2. **Visual Analysis** — produces structured JSON element detections (not raw HTML)
3. **UI AST Construction** — builds hierarchical tree from flat detections using bbox containment
4. **UI IR Generation** — normalizes AST into optimizable intermediate representation
5. **Semantic Analysis** — validates structure, nesting, IDs, types, and attributes
6. **Optimization Passes** — style normalization, dedup, pattern recognition, wrapper simplification
7. **Code Generation** — deterministic emission of HTML, CSS, and JS from optimized IR
8. **Visual Verification** — pixel comparison between source and rendered output
9. **Refinement** — bounded, schema-validated IR patching with revert support

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- npm or yarn

### Backend Setup

```bash
cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
# source venv/bin/activate

pip install -r requirements.txt
cp ../.env.example ../.env
# Edit .env to add API keys if desired

uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend runs at `http://localhost:5173` and proxies API calls to `http://localhost:8000`.

## Vision Processing Engines (100% Free & No-Cost Options)

UI2Code provides multiple processing engines:

1. **Local Computer Vision Engine (`VISION_PROVIDER=local_cv`, DEFAULT)**:
   - **100% Free, Offline, and Zero-Cost** — requires no API keys, accounts, or internet access.
   - Operates as a purely **data-driven Visual Scanner (Lexer)** using OpenCV, NumPy, and Pillow.
   - **No Hallucinated Boilerplate**: If an image contains only a single button, only that button is detected and generated. If an image contains a card with an input, only that card and input are generated. Headers and footers are emitted **only** when a top or bottom banner is visually present.
   - Extracts bounding boxes, contours, and real sampled colors from image pixels, feeding them into the formal compiler pipeline (AST &rarr; IR &rarr; Semantic Checks &rarr; Optimizer &rarr; CodeGen).

2. **Google Gemini Multimodal Vision (`VISION_PROVIDER=gemini`)**:
   - Google AI Studio offers a **100% Free API Tier** (no credit card or billing required).
   - You can get a free key instantly at [https://aistudio.google.com/apikey](https://aistudio.google.com/apikey).
   - Set `GEMINI_API_KEY=your-key` in `.env` to enable LLM-assisted vision and natural language refinement.

3. **Static Fixture Mode (`VISION_PROVIDER=fixture`)**:
   - Uses bundled sample detections for controlled offline benchmarks and demonstrations.

## Academic Viva & Faculty Defense Guide (BCSE307P)

For complete faculty defense notes, Dragon Book phase mappings, and viva Q&A explaining why UI2Code is a deterministic optimizing compiler and **not** a generative AI wrapper, see:
👉 **[`COMPILER_DEFENSE.md`](./COMPILER_DEFENSE.md)**

You can also view this interactive defense directly inside the application by clicking the **"🎓 Compiler Defense"** button in the top navigation bar or the "Compiler Defense" tab in the bottom inspection panel.

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `VISION_PROVIDER` | Vision provider: `local_cv` (free offline default), `gemini`, `openai`, or `fixture` | `local_cv` |
| `GEMINI_API_KEY` | Google Gemini API key (optional — free tier at aistudio.google.com) | — |
| `OPENAI_API_KEY` | OpenAI API key (optional) | — |
| `MAX_UPLOAD_SIZE_MB` | Maximum upload file size | `10` |
| `CORS_ORIGINS` | Allowed CORS origins | `http://localhost:5173` |

## Running Tests

```bash
cd backend
pytest -v
```

## Safety & Security
- Generated code runs in a sandboxed iframe (`sandbox="allow-scripts"` only)
- Content Security Policy blocks network requests from generated code
- API keys are only on the backend; never exposed to browser or generated code
- Uploaded files are validated for type, size, and decodability
- User-supplied filenames are never trusted

## Limitations
- Does not recover original source code — generates an approximation
- Optimized for the source screenshot viewport size; responsive behavior is approximate
- Image assets are placeholders unless cropped from the source screenshot
- Visual verification metrics are estimates affected by font rendering and antialiasing
- Interaction logic is placeholder-only unless clearly inferable from the screenshot

## Project Structure

```
ui2code/
  frontend/           # React + TypeScript + Vite
    src/
      components/     # Upload, editors, preview, diagnostics, verification
      types/          # TypeScript API/IR type definitions
      lib/            # API client, helpers
  backend/            # Python + FastAPI + Pydantic
    app/
      api/            # Route handlers
      schemas/        # Pydantic models
      vision/         # Provider interface + adapters
      analysis/       # Image processing
      compiler/       # AST, IR, semantic, optimization, codegen
      verification/   # Image comparison metrics
      services/       # Pipeline orchestration
    tests/            # pytest test suite
  fixtures/           # Demo screenshot and detection data
  .env.example        # Environment variable template
```

## License

Academic project — Compiler Design Lab.
