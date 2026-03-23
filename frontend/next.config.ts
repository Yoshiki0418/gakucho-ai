import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: '/lip-sync/:path*',
        destination: 'http://127.0.0.1:8080/:path*',
      },
    ]
  },
};

export default nextConfig;
