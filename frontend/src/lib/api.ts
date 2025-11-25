import { ENV } from "./env";

type ApiParams = Record<string, string | number | boolean | null | undefined>;

type ApiRequestConfig = Omit<RequestInit, "body"> & {
  params?: ApiParams;
};

export interface ApiResponse<T = unknown> {
  data: T;
  status: number;
  statusText: string;
  headers: Headers;
  raw: Response;
}

export class ApiError<T = unknown> extends Error {
  status: number;
  statusText: string;
  data: T | null;
  headers?: Headers;
  raw?: Response;
  cause?: unknown;

  constructor(
    message: string,
    options: {
      status: number;
      statusText: string;
      data: T | null;
      headers?: Headers;
      raw?: Response;
      cause?: unknown;
    }
  ) {
    super(message);
    this.name = "ApiError";
    this.status = options.status;
    this.statusText = options.statusText;
    this.data = options.data;
    this.headers = options.headers;
    this.raw = options.raw;
    this.cause = options.cause;
  }
}

function withQuery(path: string, params?: ApiParams): string {
  if (!params || Object.keys(params).length === 0) return path;
  const search = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null) continue;
    search.append(k, String(v));
  }
  if (!search.toString()) return path;
  const [base, existing] = path.split("?");
  const prefix = existing ? `${existing}&${search.toString()}` : search.toString();
  return `${base}?${prefix}`;
}

function resolveUrl(path: string): string {
  if (path.startsWith("http")) return path;
  const base = ENV.apiBase || "";
  const isAbsoluteBase = /^https?:\/\//i.test(base);
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;

  if (isAbsoluteBase) {
    const baseUrl = new URL(base);
    const basePath = baseUrl.pathname.replace(/\/+$/, "");
    if (basePath && normalizedPath.startsWith(basePath)) {
      return `${baseUrl.origin}${normalizedPath}`;
    }
    return `${baseUrl.origin}${basePath}${normalizedPath}`;
  }

  const trimmedBase = base.replace(/\/+$/, "");
  if (!trimmedBase) return normalizedPath;
  if (normalizedPath.startsWith(trimmedBase)) return normalizedPath;
  return `${trimmedBase}${normalizedPath}`;
}

async function coreRequest<T = unknown>(path: string, init: RequestInit = {}): Promise<ApiResponse<T>> {
  const url = resolveUrl(path);
  const headers = new Headers(init.headers ?? {});

  if (!headers.has("X-API-Key") && ENV.uiKey) {
    headers.set("X-API-Key", ENV.uiKey);
  }

  const hasBody = init.body !== undefined && init.body !== null;
  if (hasBody && !headers.has("Content-Type") && !(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  let response: Response;
  try {
    response = await fetch(url, { ...init, headers });
  } catch (err) {
    // Network/CORS-level failure: no Response object
    throw new ApiError("Network request failed", {
      status: 0,
      statusText: "NETWORK_ERROR",
      data: null,
      cause: err,
    });
  }

  const contentType = response.headers.get("content-type") ?? "";
  const isJson = contentType.includes("application/json");

  if (!response.ok) {
    let errorData: unknown = null;
    let fallbackText = "";

    if (isJson) {
      try {
        errorData = await response.json();
        fallbackText = JSON.stringify(errorData);
      } catch {
        fallbackText = await response.text().catch(() => "");
      }
    } else {
      fallbackText = await response.text().catch(() => "");
      errorData = fallbackText;
    }

    const detail =
      typeof errorData === "object" &&
      errorData !== null &&
      "detail" in errorData
        ? // eslint-disable-next-line @typescript-eslint/no-explicit-any
          (errorData as any).detail
        : undefined;

    const message =
      typeof detail === "string" && detail.trim().length > 0
        ? detail
        : `HTTP ${response.status} ${response.statusText}: ${fallbackText}`;

    throw new ApiError(message, {
      status: response.status,
      statusText: response.statusText,
      data: (errorData as T | null) ?? null,
      headers: response.headers,
      raw: response,
    });
  }

  const data = (isJson
    ? await response.json()
    : await response.text()) as T;

  return {
    data,
    status: response.status,
    statusText: response.statusText,
    headers: response.headers,
    raw: response,
  };
}

type ApiFunction = {
  <T = unknown>(path: string, init?: RequestInit): Promise<ApiResponse<T>>;
  get<T = unknown>(path: string, config?: ApiRequestConfig): Promise<ApiResponse<T>>;
  delete<T = unknown>(path: string, config?: ApiRequestConfig): Promise<ApiResponse<T>>;
  post<T = unknown>(path: string, data?: unknown, config?: ApiRequestConfig): Promise<ApiResponse<T>>;
  patch<T = unknown>(path: string, data?: unknown, config?: ApiRequestConfig): Promise<ApiResponse<T>>;
  put<T = unknown>(path: string, data?: unknown, config?: ApiRequestConfig): Promise<ApiResponse<T>>;
};

const request = coreRequest as ApiFunction;

request.get = function get<T>(path: string, config: ApiRequestConfig = {}) {
  const { params, ...rest } = config;
  const withParams = withQuery(path, params);
  return coreRequest<T>(withParams, { ...rest, method: "GET" });
};

request.delete = function del<T>(path: string, config: ApiRequestConfig = {}) {
  const { params, ...rest } = config;
  const withParams = withQuery(path, params);
  return coreRequest<T>(withParams, { ...rest, method: "DELETE" });
};

function buildBody(data: unknown): BodyInit | undefined {
  if (data === undefined || data === null) return undefined;
  if (data instanceof FormData || data instanceof Blob || data instanceof ArrayBuffer) {
    return data as BodyInit;
  }
  if (typeof data === "string") return data;
  return JSON.stringify(data);
}

request.post = function post<T>(path: string, data?: unknown, config: ApiRequestConfig = {}) {
  const { params, ...rest } = config;
  const withParams = withQuery(path, params);
  return coreRequest<T>(withParams, { ...rest, method: "POST", body: buildBody(data) });
};

request.patch = function patch<T>(path: string, data?: unknown, config: ApiRequestConfig = {}) {
  const { params, ...rest } = config;
  const withParams = withQuery(path, params);
  return coreRequest<T>(withParams, { ...rest, method: "PATCH", body: buildBody(data) });
};

request.put = function put<T>(path: string, data?: unknown, config: ApiRequestConfig = {}) {
  const { params, ...rest } = config;
  const withParams = withQuery(path, params);
  return coreRequest<T>(withParams, { ...rest, method: "PUT", body: buildBody(data) });
};

export const api = request;
export default api;
