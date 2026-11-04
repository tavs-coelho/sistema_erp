import type { NextConfig } from "next";

// Same-origin /api is implemented by the route handler at
// src/app/api/[...path]/route.ts (retains the original public Host/Origin for
// signed CSRF validation). Nginx proxies /api directly in Docker.
// Do not duplicate this with a rewrite: the rewritten upstream Host may
// invalidate CSRF and confuse tenant resolution.
const nextConfig: NextConfig = {};

export default nextConfig;
