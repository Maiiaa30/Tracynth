import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiError, apiRequest, asPage, getSession } from './api';

afterEach(() => {
  vi.unstubAllGlobals();
  document.cookie = 'csrftoken=; Max-Age=0; path=/';
});

describe('apiRequest', () => {
  it('uses same-origin credentials and adds CSRF to unsafe requests', async () => {
    document.cookie = 'csrftoken=test-token; path=/';
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ id: '1' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    vi.stubGlobal('fetch', fetchMock);

    await apiRequest('/targets/', {
      method: 'POST',
      body: JSON.stringify({ value: 'example.com' }),
    });

    expect(fetchMock).toHaveBeenCalledOnce();
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe('/api/v1/targets/');
    expect(init.credentials).toBe('same-origin');
    expect(new Headers(init.headers).get('X-CSRFToken')).toBe('test-token');
  });

  it('normalizes the stable API error envelope', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({ error: { code: 'invalid_target', message: 'Invalid target.' } }),
          {
            status: 400,
            headers: { 'Content-Type': 'application/json' },
          },
        ),
      ),
    );

    await expect(apiRequest('/targets/')).rejects.toMatchObject({
      status: 400,
      code: 'invalid_target',
      message: 'Invalid target.',
    } satisfies Partial<ApiError>);
  });
});

describe('asPage', () => {
  it('adapts direct arrays without inventing records', () => {
    expect(asPage([{ id: 'a' }])).toEqual({
      count: 1,
      next: null,
      previous: null,
      results: [{ id: 'a' }],
    });
  });
});

describe('getSession', () => {
  it('treats DRF unauthenticated 403 responses as signed out', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValue(
          new Response(
            JSON.stringify({ error: { code: 'not_authenticated', message: 'Sign in required.' } }),
            { status: 403, headers: { 'Content-Type': 'application/json' } },
          ),
        ),
    );

    await expect(getSession()).resolves.toEqual({ authenticated: false });
  });
});
