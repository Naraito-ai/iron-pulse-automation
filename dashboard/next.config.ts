import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  eslint: { ignoreDuringBuilds: true },
  images: {
    remotePatterns: [
      { protocol: 'http', hostname: 'localhost', port: '8000', pathname: '/images/**' },
      { protocol: 'http', hostname: 'localhost', port: '8888', pathname: '/generated/**' },
    ],
  },
  async rewrites() {
    return [
      { source: '/api/:path*', destination: 'https://backend-v2-production-32c5.up.railway.app/api/:path*' },
    ];
  },
};

export default nextConfig;
