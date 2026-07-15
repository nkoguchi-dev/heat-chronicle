import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '@/features/shared/libs/api-client';

const fetchMock = vi.fn<typeof fetch>();

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock);
});

describe('apiClient', () => {
  it('returns JSON and forwards an abort signal for GET requests', async () => {
    const controller = new AbortController();
    fetchMock.mockResolvedValueOnce(Response.json({ value: 1 }));

    await expect(apiClient.get<{ value: number }>('/resource', { signal: controller.signal })).resolves.toEqual({
      value: 1,
    });
    expect(fetchMock).toHaveBeenCalledWith('http://localhost:8000/resource', {
      headers: { 'Content-Type': 'application/json' },
      signal: controller.signal,
    });
  });

  it('uses a validated API error detail and falls back for non-JSON errors', async () => {
    fetchMock
      .mockResolvedValueOnce(Response.json({ detail: 'invalid request' }, { status: 400 }))
      .mockResolvedValueOnce(new Response('broken', { status: 500, statusText: 'Server Error' }));

    await expect(apiClient.get('/invalid')).rejects.toMatchObject({
      name: 'ApiError',
      status: 400,
      message: 'invalid request',
    });
    await expect(apiClient.get('/broken')).rejects.toMatchObject({ message: 'Server Error' });
  });

  it('ignores a non-string error detail and uses the generic fallback when status text is empty', async () => {
    fetchMock.mockResolvedValueOnce(Response.json({ detail: 123 }, { status: 400, statusText: '' }));

    await expect(apiClient.get('/invalid-detail')).rejects.toMatchObject({ message: 'An error occurred' });
  });

  it('rejects an empty successful GET response', async () => {
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }));

    await expect(apiClient.get('/empty')).rejects.toMatchObject({
      status: 204,
      message: 'Expected a JSON response body',
    });
  });

  it.each([
    ['post', false, 'false'],
    ['put', 0, '0'],
    ['post', null, 'null'],
  ] as const)('serializes %s bodies without dropping falsey values', async (method, data, expectedBody) => {
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }));

    await apiClient[method]('/resource', data);

    expect(fetchMock).toHaveBeenLastCalledWith(
      'http://localhost:8000/resource',
      expect.objectContaining({ body: expectedBody }),
    );
  });

  it('supports DELETE responses with no body', async () => {
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }));

    await expect(apiClient.delete('/resource')).resolves.toBeUndefined();
  });

  it('omits an undefined body and parses JSON mutation responses', async () => {
    fetchMock
      .mockResolvedValueOnce(Response.json({ created: true }))
      .mockResolvedValueOnce(Response.json({ updated: true }))
      .mockResolvedValueOnce(Response.json({ deleted: true }));

    await expect(apiClient.post('/resource')).resolves.toEqual({ created: true });
    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      'http://localhost:8000/resource',
      expect.objectContaining({ body: undefined }),
    );
    await expect(apiClient.put('/resource', { value: 1 })).resolves.toEqual({ updated: true });
    await expect(apiClient.delete('/resource')).resolves.toEqual({ deleted: true });
  });
});
