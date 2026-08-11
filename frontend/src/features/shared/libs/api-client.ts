import type { ZodType } from 'zod';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export type ApiErrorKind = 'http' | 'invalid-response';

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public kind: ApiErrorKind = 'http',
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

interface RequestOptions<T> {
  signal?: AbortSignal;
  schema: ZodType<T>;
}

interface ApiClient {
  get: <T>(path: string, options: RequestOptions<T>) => Promise<T>;
  post: <T>(path: string, data?: unknown) => Promise<T | undefined>;
  put: <T>(path: string, data?: unknown) => Promise<T | undefined>;
  delete: <T>(path: string) => Promise<T | undefined>;
}

function getErrorDetail(payload: unknown): string | null {
  if (typeof payload !== 'object' || payload === null || !('detail' in payload)) return null;
  return typeof payload.detail === 'string' ? payload.detail : null;
}

async function handleResponse<T>(response: Response, schema?: ZodType<T>): Promise<T | undefined> {
  if (!response.ok) {
    const payload: unknown = await response.json().catch(() => null);
    throw new ApiError(response.status, (getErrorDetail(payload) ?? response.statusText) || 'An error occurred');
  }

  if (response.status === 204) return undefined;

  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    throw new ApiError(response.status, 'Expected a valid JSON response body', 'invalid-response');
  }

  if (!schema) return payload as T;

  const result = schema.safeParse(payload);
  if (!result.success) {
    throw new ApiError(response.status, 'Response body did not match the expected schema', 'invalid-response');
  }
  return result.data;
}

export const apiClient: ApiClient = {
  get: async <T>(path: string, options: RequestOptions<T>): Promise<T> => {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      headers: {
        'Content-Type': 'application/json',
      },
      signal: options.signal,
    });
    const data = await handleResponse<T>(response, options.schema);
    if (data === undefined) {
      throw new ApiError(response.status, 'Expected a JSON response body', 'invalid-response');
    }
    return data;
  },

  post: async <T>(path: string, data?: unknown): Promise<T | undefined> => {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: data === undefined ? undefined : JSON.stringify(data),
    });
    return handleResponse<T>(response);
  },

  put: async <T>(path: string, data?: unknown): Promise<T | undefined> => {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: data === undefined ? undefined : JSON.stringify(data),
    });
    return handleResponse<T>(response);
  },

  delete: async <T>(path: string): Promise<T | undefined> => {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    return handleResponse<T>(response);
  },
};

export { ApiError };
