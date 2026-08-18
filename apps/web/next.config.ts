import path from "node:path"

import type { NextConfig } from "next"

// monorepo 根目录：Turbopack 需从此处解析 packages/ui 与 pnpm 依赖
const monorepoRoot = path.resolve(process.cwd(), "../..")
const apiUrl = process.env.API_URL ?? "http://127.0.0.1:8000"

const nextConfig: NextConfig = {
  transpilePackages: ["@workspace/ui"],
  turbopack: {
    root: monorepoRoot,
  },
  outputFileTracingRoot: monorepoRoot,
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
