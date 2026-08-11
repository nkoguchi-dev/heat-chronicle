import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  output: 'export',
  experimental: {
    useTypeScriptCli: false,
  },
};

export default nextConfig;
