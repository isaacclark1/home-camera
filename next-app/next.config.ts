import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // URL re-writes
  async rewrites() {
    return [
      {
        source: "/py/:path*",
        destination: "http://localhost:8000/:path*",
      },
    ];
  },
};

export default nextConfig;
