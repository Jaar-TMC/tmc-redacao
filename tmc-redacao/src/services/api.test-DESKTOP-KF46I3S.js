/**
 * Unit tests for api.js auth retry and redirect guard logic.
 *
 * Tests the Phase 1 (Session Persistence) changes:
 * - Task 1.3: _isRedirecting fires _onUnauthorized exactly once
 * - Review fix: resetRedirectGuard() re-enables 401 handling after re-login
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// We need to test module-internal behavior, so we test via the public API.
// registerAuthHandlers sets up the callbacks, fetchApi triggers the 401 flow.

// Mock global fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

// Dynamic import to get a fresh module per test
let api;

beforeEach(async () => {
  vi.resetModules();
  mockFetch.mockReset();
  api = await import('./api.js');
});

describe('Concurrent 401 redirect guard', () => {
  it('fires _onUnauthorized exactly once on multiple 401s', async () => {
    const onUnauth = vi.fn();
    const getToken = () => 'fake-token';
    const refreshFn = vi.fn().mockResolvedValue(null); // refresh fails

    api.registerAuthHandlers(getToken, onUnauth, refreshFn);

    // Simulate two 401 responses
    mockFetch.mockResolvedValue({
      ok: false,
      status: 401,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: () => Promise.resolve({ error: 'Unauthorized' }),
    });

    // Fire two concurrent requests that both get 401
    const results = await Promise.allSettled([
      api.fetchApi('/test-1'),
      api.fetchApi('/test-2'),
    ]);

    // Both should reject (ApiError), but onUnauthorized should fire only ONCE
    expect(results.every(r => r.status === 'rejected')).toBe(true);
    expect(onUnauth).toHaveBeenCalledTimes(1);
  });

  it('does not fire _onUnauthorized for auth endpoints', async () => {
    const onUnauth = vi.fn();
    api.registerAuthHandlers(() => 'token', onUnauth, null);

    mockFetch.mockResolvedValue({
      ok: false,
      status: 401,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: () => Promise.resolve({ error: 'Unauthorized' }),
    });

    await expect(api.fetchApi('/auth/refresh', { method: 'POST' })).rejects.toThrow();
    expect(onUnauth).not.toHaveBeenCalled();
  });

  it('resetRedirectGuard re-enables 401 handling after re-login', async () => {
    const onUnauth = vi.fn();
    const refreshFn = vi.fn().mockResolvedValue(null);
    api.registerAuthHandlers(() => 'token', onUnauth, refreshFn);

    mockFetch.mockResolvedValue({
      ok: false,
      status: 401,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: () => Promise.resolve({ error: 'Unauthorized' }),
    });

    // First 401 fires onUnauthorized
    await expect(api.fetchApi('/test-1')).rejects.toThrow();
    expect(onUnauth).toHaveBeenCalledTimes(1);

    // Second 401 is suppressed (guard is active)
    await expect(api.fetchApi('/test-2')).rejects.toThrow();
    expect(onUnauth).toHaveBeenCalledTimes(1); // still 1

    // Simulate re-login: reset the guard
    api.resetRedirectGuard();

    // Third 401 should fire onUnauthorized again
    await expect(api.fetchApi('/test-3')).rejects.toThrow();
    expect(onUnauth).toHaveBeenCalledTimes(2);
  });

  it('registerAuthHandlers resets the redirect guard', async () => {
    const onUnauth = vi.fn();
    const refreshFn = vi.fn().mockResolvedValue(null);
    api.registerAuthHandlers(() => 'token', onUnauth, refreshFn);

    mockFetch.mockResolvedValue({
      ok: false,
      status: 401,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: () => Promise.resolve({ error: 'Unauthorized' }),
    });

    // Trigger first 401
    await expect(api.fetchApi('/test')).rejects.toThrow();
    expect(onUnauth).toHaveBeenCalledTimes(1);

    // Re-register handlers (simulates AuthProvider remount)
    api.registerAuthHandlers(() => 'new-token', onUnauth, refreshFn);

    // Next 401 should fire again
    await expect(api.fetchApi('/test')).rejects.toThrow();
    expect(onUnauth).toHaveBeenCalledTimes(2);
  });
});

describe('Token refresh on 401', () => {
  it('retries request with new token after successful refresh', async () => {
    const onUnauth = vi.fn();
    const refreshFn = vi.fn().mockResolvedValue('new-token');
    api.registerAuthHandlers(() => 'old-token', onUnauth, refreshFn);

    // First call returns 401, retry returns 200
    mockFetch
      .mockResolvedValueOnce({
        ok: false,
        status: 401,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: () => Promise.resolve({ error: 'Unauthorized' }),
      })
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: () => Promise.resolve({ data: 'success' }),
      });

    const result = await api.fetchApi('/protected');
    expect(result).toEqual({ data: 'success' });
    expect(refreshFn).toHaveBeenCalledTimes(1);
    expect(onUnauth).not.toHaveBeenCalled(); // refresh succeeded, no redirect
  });
});
