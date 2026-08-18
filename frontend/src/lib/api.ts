import type { ApiErrorBody, Page, SessionResponse, User } from '../types/api';

const API_ROOT = '/api/v1';

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly fields: Record<string, string[] | string>;

  constructor(status: number, body: ApiErrorBody) {
    super(body.error?.message ?? body.detail ?? `Request failed with status ${status}`);
    this.name = 'ApiError';
    this.status = status;
    this.code = body.error?.code ?? 'request_failed';
    this.fields = body.error?.fields ?? {};
  }
}

function getCookie(name: string): string | undefined {
  return document.cookie
    .split(';')
    .map((cookie) => cookie.trim())
    .find((cookie) => cookie.startsWith(`${name}=`))
    ?.slice(name.length + 1);
}

function isUnsafe(method: string): boolean {
  return !['GET', 'HEAD', 'OPTIONS', 'TRACE'].includes(method.toUpperCase());
}

async function parseError(response: Response): Promise<ApiErrorBody> {
  try {
    return (await response.json()) as ApiErrorBody;
  } catch {
    return { error: { code: 'invalid_response', message: response.statusText } };
  }
}

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = init.method ?? 'GET';
  const headers = new Headers(init.headers);
  if (!(init.body instanceof FormData) && init.body !== undefined) {
    headers.set('Content-Type', 'application/json');
  }
  headers.set('Accept', 'application/json');
  if (isUnsafe(method)) {
    const token = getCookie('tracynth_csrftoken') ?? getCookie('csrftoken');
    if (token) headers.set('X-CSRFToken', decodeURIComponent(token));
  }

  const response = await fetch(path.startsWith('/api/') ? path : `${API_ROOT}${path}`, {
    ...init,
    method,
    headers,
    credentials: 'same-origin',
  });
  if (!response.ok) throw new ApiError(response.status, await parseError(response));
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export async function ensureCsrf(): Promise<void> {
  await apiRequest<unknown>('/auth/csrf/');
}

export async function getSession(): Promise<SessionResponse> {
  try {
    const session = await apiRequest<{ user: User }>('/auth/me/');
    return { authenticated: true, user: session.user };
  } catch (error) {
    // DRF's SessionAuthentication returns 403 when no session authenticated the
    // request; both 401 and 403 mean "signed out" for this dedicated probe.
    if (
      error instanceof ApiError &&
      (error.status === 401 || (error.status === 403 && error.code === 'not_authenticated'))
    ) {
      return { authenticated: false };
    }
    throw error;
  }
}

export async function login(username: string, password: string): Promise<User> {
  await ensureCsrf();
  const result = await apiRequest<{ user?: User } & Partial<User>>('/auth/login/', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  });
  const user = result.user ?? (result.username ? { username: result.username } : undefined);
  if (!user) throw new Error('The server authenticated the session without returning a user.');
  return user;
}

export async function logout(): Promise<void> {
  await apiRequest('/auth/logout/', { method: 'POST' });
}

export function asPage<T>(value: Page<T> | T[]): Page<T> {
  if (Array.isArray(value)) {
    return { count: value.length, next: null, previous: null, results: value };
  }
  return value;
}

export function displayError(error: unknown): string {
  return error instanceof Error ? error.message : 'An unexpected error occurred.';
}
