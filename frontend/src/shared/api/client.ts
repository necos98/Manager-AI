const BASE = "/api";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 30_000);
  const { signal: callerSignal, ...restOptions } = options;
  const signal = callerSignal
    ? AbortSignal.any([controller.signal, callerSignal])
    : controller.signal;
  try {
    const res = await fetch(`${BASE}${path}`, {
      headers: { "Content-Type": "application/json", ...restOptions.headers },
      signal,
      ...restOptions,
    });
    if (res.status === 204) return null as T;
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Unknown error" }));
      throw new ApiError(err.detail || "Request failed", res.status);
    }
    return res.json();
  } finally {
    clearTimeout(timeoutId);
  }
}

export async function uploadRequest<T>(path: string, formData: FormData): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Unknown error" }));
    throw new ApiError(err.detail || "Upload failed", res.status);
  }
  return res.json();
}

export function buildUrl(path: string): string {
  return `${BASE}${path}`;
}
