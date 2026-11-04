import type { NextConfig } from "next";

// Browser and API must share one origin for HttpOnly cookies and CSRF.
// Nginx already proxies /api in Docker. This rewrite enables the same
// behavior when running Next.js directly (port 3000) during development.
const backend = process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000";
const nextConfig: NextConfig = {
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${backend}/:path*` }];
  },
};

export default nextConfig;
