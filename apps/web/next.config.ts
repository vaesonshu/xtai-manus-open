import type { NextConfig } from "next"

const apiUrl = process.env.API_URL ?? "http://127.0.0.1:8000"

const nextConfig: NextConfig = {
  transpilePackages: ["@workspace/ui"],
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${apiUrl}/:path*`,
      },
    ]
  },
}

export default nextConfig
