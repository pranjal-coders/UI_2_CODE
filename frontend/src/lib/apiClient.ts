import {
  AnalyzeResponse,
  CompileRequest,
  CompileResponse,
  HealthResponse,
  RefineRequest,
  RefineResponse,
  VerificationResult,
} from '../types/api';

const API_BASE = (import.meta.env.VITE_API_URL || '').replace(/\/+$/, '');

async function handleResponse<T>(res: Response, endpoint: string): Promise<T> {
  if (!res.ok) {
    let message = `Request to ${endpoint} failed with status ${res.status} (${res.statusText})`;
    try {
      const data = await res.json();
      if (typeof data.detail === 'string') {
        message = data.detail;
      } else if (data.detail && typeof data.detail === 'object') {
        message = JSON.stringify(data.detail);
      } else if (typeof data.message === 'string') {
        message = data.message;
      } else if (typeof data.error === 'string') {
        message = data.error;
      }
    } catch {
      try {
        const text = await res.text();
        if (text && text.trim().length > 0) {
          message = text.trim();
        }
      } catch {
        // Fall back to default status text
      }
    }
    throw new Error(message);
  }

  return res.json() as Promise<T>;
}

export async function checkHealth(): Promise<HealthResponse> {
  try {
    const res = await fetch(`${API_BASE}/api/health`);
    return await handleResponse<HealthResponse>(res, '/api/health');
  } catch (err: any) {
    throw new Error(`Health check failed: ${err.message || err}`);
  }
}

export async function fetchDemoImage(): Promise<File> {
  const res = await fetch(`${API_BASE}/api/demo-image`);
  if (!res.ok) {
    throw new Error('Failed to load bundled demo screenshot fixture.');
  }
  const blob = await res.blob();
  return new File([blob], 'demo_screenshot.png', { type: 'image/png' });
}

export async function analyzeImage(file: File, provider?: string): Promise<AnalyzeResponse> {
  const formData = new FormData();
  formData.append('file', file);
  if (provider) {
    formData.append('provider', provider);
  }

  const res = await fetch(`${API_BASE}/api/analyze`, {
    method: 'POST',
    body: formData,
  });

  return handleResponse<AnalyzeResponse>(res, '/api/analyze');
}

export async function compileDetections(
  request: CompileRequest
): Promise<CompileResponse> {
  const res = await fetch(`${API_BASE}/api/compile`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  return handleResponse<CompileResponse>(res, '/api/compile');
}

export async function verifyOutput(
  sourceImage: Blob,
  generatedImage: Blob
): Promise<VerificationResult> {
  const formData = new FormData();
  formData.append('source_image', sourceImage, 'source.png');
  formData.append('generated_image', generatedImage, 'generated.png');

  const res = await fetch(`${API_BASE}/api/verify`, {
    method: 'POST',
    body: formData,
  });

  return handleResponse<VerificationResult>(res, '/api/verify');
}

export async function refineIR(request: RefineRequest): Promise<RefineResponse> {
  const res = await fetch(`${API_BASE}/api/refine`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  return handleResponse<RefineResponse>(res, '/api/refine');
}
