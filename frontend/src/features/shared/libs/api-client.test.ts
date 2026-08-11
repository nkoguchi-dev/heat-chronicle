import { delay, http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import { z } from 'zod';

import { apiClient } from '@/features/shared/libs/api-client';
import { server } from '@/test/server';

const API_URL = 'http://localhost:8000';
const valueSchema = z.object({ value: z.number() });

describe('apiClient', () => {
  it('sends a GET request with its URL and query and validates the JSON response', async () => {
    server.use(
      http.get(`${API_URL}/resource`, ({ request }) => {
        const url = new URL(request.url);
        expect(request.method).toBe('GET');
        expect(url.searchParams.get('page')).toBe('2');
        expect(request.headers.get('content-type')).toBe('application/json');
        return HttpResponse.json({ value: 1, future_field: true });
      }),
    );

    await expect(apiClient.get('/resource?page=2', { schema: valueSchema })).resolves.toEqual({ value: 1 });
  });

  it('classifies HTTP errors and uses a validated detail or status text', async () => {
    server.use(
      http.get(`${API_URL}/invalid`, () => HttpResponse.json({ detail: 'invalid request' }, { status: 400 })),
      http.get(`${API_URL}/broken`, () => new HttpResponse('broken', { status: 500, statusText: 'Server Error' })),
    );

    await expect(apiClient.get('/invalid', { schema: valueSchema })).rejects.toMatchObject({
      name: 'ApiError',
      kind: 'http',
      status: 400,
      message: 'invalid request',
    });
    await expect(apiClient.get('/broken', { schema: valueSchema })).rejects.toMatchObject({
      kind: 'http',
      message: 'Server Error',
    });
  });

  it('ignores a non-string error detail and falls back to the HTTP status text', async () => {
    server.use(
      http.get(`${API_URL}/invalid-detail`, () => HttpResponse.json({ detail: 123 }, { status: 400, statusText: '' })),
    );

    await expect(apiClient.get('/invalid-detail', { schema: valueSchema })).rejects.toMatchObject({
      kind: 'http',
      message: 'Bad Request',
    });
  });

  it.each([
    ['invalid JSON', '/invalid-json', () => new HttpResponse('{', { headers: { 'Content-Type': 'application/json' } })],
    ['an invalid schema', '/invalid-schema', () => HttpResponse.json({ value: 'one' })],
    ['an empty GET body', '/empty', () => new HttpResponse(null, { status: 204 })],
  ] as const)('classifies %s as an invalid response', async (_label, path, resolver) => {
    server.use(http.get(`${API_URL}${path}`, resolver));

    await expect(apiClient.get(path, { schema: valueSchema })).rejects.toMatchObject({
      name: 'ApiError',
      kind: 'invalid-response',
    });
  });

  it('preserves a network error', async () => {
    server.use(http.get(`${API_URL}/offline`, () => HttpResponse.error()));

    await expect(apiClient.get('/offline', { schema: valueSchema })).rejects.toBeInstanceOf(TypeError);
  });

  it('forwards cancellation as an AbortError', async () => {
    server.use(
      http.get(`${API_URL}/slow`, async () => {
        await delay('infinite');
        return HttpResponse.json({ value: 1 });
      }),
    );
    const controller = new AbortController();
    const request = apiClient.get('/slow', { signal: controller.signal, schema: valueSchema });

    controller.abort();

    await expect(request).rejects.toMatchObject({ name: 'AbortError' });
  });

  it.each([
    ['post', false, 'false'],
    ['put', 0, '0'],
    ['post', null, 'null'],
  ] as const)('sends %s JSON bodies without dropping falsey values', async (method, data, expectedBody) => {
    const registerHandler = method === 'post' ? http.post : http.put;
    server.use(
      registerHandler(`${API_URL}/resource`, async ({ request }) => {
        expect(await request.text()).toBe(expectedBody);
        return new HttpResponse(null, { status: 204 });
      }),
    );

    await expect(apiClient[method]('/resource', data)).resolves.toBeUndefined();
  });

  it('supports mutation JSON responses, undefined bodies, and empty DELETE responses', async () => {
    server.use(
      http.post(`${API_URL}/resource`, async ({ request }) => {
        expect(await request.text()).toBe('');
        return HttpResponse.json({ created: true });
      }),
      http.put(`${API_URL}/resource`, async ({ request }) => {
        expect(await request.json()).toEqual({ value: 1 });
        return HttpResponse.json({ updated: true });
      }),
      http.delete(`${API_URL}/resource`, () => new HttpResponse(null, { status: 204 })),
    );

    await expect(apiClient.post('/resource')).resolves.toEqual({ created: true });
    await expect(apiClient.put('/resource', { value: 1 })).resolves.toEqual({ updated: true });
    await expect(apiClient.delete('/resource')).resolves.toBeUndefined();
  });
});
