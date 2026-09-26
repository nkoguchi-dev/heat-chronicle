export function parseApiOrigin(value: string, name: string): string {
  if (value !== value.trim()) throw new Error(`${name} must be an HTTP(S) origin`);

  let url: URL;
  try {
    url = new URL(value);
  } catch {
    throw new Error(`${name} must be an HTTP(S) origin`);
  }

  if (
    !['http:', 'https:'].includes(url.protocol) ||
    !url.hostname ||
    url.username ||
    url.password ||
    url.pathname !== '/' ||
    value.includes('?') ||
    value.includes('#') ||
    url.search ||
    url.hash
  ) {
    throw new Error(`${name} must be an HTTP(S) origin without credentials, path, query, or fragment`);
  }

  return url.origin;
}

export function resolveViteApiConfig(
  command: 'build' | 'serve',
  apiUrl: string | undefined,
  proxyTarget: string | undefined,
): { apiBaseUrl: string; proxyTarget: string } {
  if (command === 'build' && !apiUrl) throw new Error('VITE_API_URL is required for production builds');

  return {
    apiBaseUrl: apiUrl ? parseApiOrigin(apiUrl, 'VITE_API_URL') : '',
    proxyTarget: parseApiOrigin(proxyTarget ?? 'http://127.0.0.1:8000', 'HEAT_CHRONICLE_API_PROXY_TARGET'),
  };
}
