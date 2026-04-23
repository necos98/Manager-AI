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
      // FastAPI 422 validation errors come back as an array of objects.
      // Flatten them to a human-readable string so toasts don't render "[object Object]".
      let message: string;
      if (Array.isArray(err.detail)) {
        message = err.detail
          .map((e: { loc?: unknown[]; msg?: string }) => {
            const where = Array.isArray(e.loc) ? e.loc.join(".") : "";
            return where ? `${where}: ${e.msg}` : e.msg ?? "invalid";
          })
          .join("; ");
      } else if (typeof err.detail === "string") {
        message = err.detail;
      } else {
        message = "Request failed";
      }
      throw new ApiError(message, res.status);
    }
    return res.json();
  } finally {
    clearTimeout(timeoutId);
  }
}

export async function uploadRequest<T>(path: string, formData: FormData): Promise<T> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 300_000); // 5 minutes for uploads
  try {
    const res = await fetch(`${BASE}${path}`, {
      method: "POST",
      body: formData,
      signal: controller.signal,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Unknown error" }));
      throw new ApiError(err.detail || "Upload failed", res.status);
    }
    return res.json();
  } finally {
    clearTimeout(timeoutId);
  }
}

export function buildUrl(path: string): string {
  return `${BASE}${path}`;
}

export const apiGet = <T>(path: string, signal?: AbortSignal) =>
  request<T>(path, { method: "GET", signal });

export const apiPost = <T>(path: string, body?: unknown, signal?: AbortSignal) =>
  request<T>(path, {
    method: "POST",
    signal,
    ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
  });

export const apiPatch = <T>(path: string, body?: unknown, signal?: AbortSignal) =>
  request<T>(path, {
    method: "PATCH",
    signal,
    ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
  });

export const apiPut = <T>(path: string, body?: unknown, signal?: AbortSignal) =>
  request<T>(path, {
    method: "PUT",
    signal,
    ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
  });

export const apiDelete = (path: string, signal?: AbortSignal) =>
  request<null>(path, { method: "DELETE", signal });
