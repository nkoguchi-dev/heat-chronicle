import { describe, expect, it } from 'vitest';

import { parseApiOrigin, resolveViteApiConfig } from './vite-api-config';

describe('Vite API configuration', () => {
  it('uses same-origin API requests and the local FastAPI proxy in dev/preview', () => {
    expect(resolveViteApiConfig('serve', undefined, undefined)).toEqual({
      apiBaseUrl: '',
      proxyTarget: 'http://127.0.0.1:8000',
    });
  });

  it('requires a public API origin for production builds', () => {
    expect(() => resolveViteApiConfig('build', undefined, undefined)).toThrow('VITE_API_URL is required');
    expect(resolveViteApiConfig('build', 'https://api.example.com', 'http://127.0.0.1:9000')).toEqual({
      apiBaseUrl: 'https://api.example.com',
      proxyTarget: 'http://127.0.0.1:9000',
    });
  });

  it.each([
    'ftp://example.com',
    'https://user:pass@example.com',
    'https://example.com/api',
    'https://example.com?token=1',
    'https://example.com?',
    'https://example.com/#fragment',
    'https://example.com#',
    'example.com',
    ' https://example.com',
  ])('rejects an invalid origin: %s', (value) => {
    expect(() => parseApiOrigin(value, 'VITE_API_URL')).toThrow('VITE_API_URL must be an HTTP(S) origin');
    expect(() => resolveViteApiConfig('serve', undefined, value)).toThrow(
      'HEAT_CHRONICLE_API_PROXY_TARGET must be an HTTP(S) origin',
    );
  });
});
