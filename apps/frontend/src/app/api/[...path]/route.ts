import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const HOP_HEADERS = new Set([
  "connection", "transfer-encoding", "keep-alive", "proxy-authenticate",
  "proxy-authorization", "te", "trailers", "upgrade", "content-length",
]);

/**
 * Same-origin API bridge for direct Next.js usage on port 3000.
 * Nginx deployments may continue to proxy /api directly to FastAPI.
 *
 * The destination is a fixed server-only environment variable, NEVER a
 * client-supplied host. Cookies, Origin and X-CSRF-Token reach FastAPI intact.
 */
async function forward(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
): Promise<Response> {
  const { path } = await context.params;
  if (!path.length || path.some((part) => part === ".." || part === "." || part.includes("/"))) {
    return NextResponse.json({ detail: "Rota inválida" }, { status: 400 });
  }
  const base = process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000";
  let upstream: URL;
  try {
    const server = new URL(base);
    if (!["http:", "https:"].includes(server.protocol) || server.username || server.password) {
      throw new Error("Invalid backend URL");
    }
    upstream = new URL("/" + path.map(encodeURIComponent).join("/"), server);
    upstream.search = request.nextUrl.search;
  } catch {
    return NextResponse.json({ detail: "Backend não configurado" }, { status: 503 });
  }

  const headers = new Headers();
  for (const [key, value] of request.headers) {
    if (!HOP_HEADERS.has(key.toLowerCase()) && key.toLowerCase() !== "host") {
      headers.set(key, value);
    }
  }
  const publicHost = request.headers.get("host");
  if (publicHost) headers.set("host", publicHost);

  const init: RequestInit & { duplex?: "half" } = {
    method: request.method,
    headers,
    cache: "no-store",
    redirect: "manual",
  };
  if (!["GET", "HEAD"].includes(request.method)) {
    init.body = request.body;
    init.duplex = "half";
  }

  try {
    const result = await fetch(upstream, init);
    const responseHeaders = new Headers();
    for (const [key, value] of result.headers) {
      if (!HOP_HEADERS.has(key.toLowerCase()) && key.toLowerCase() !== "set-cookie") {
        responseHeaders.set(key, value);
      }
    }
    for (const cookie of result.headers.getSetCookie()) {
      responseHeaders.append("set-cookie", cookie);
    }
    responseHeaders.set("cache-control", "no-store");
    return new Response(result.body, { status: result.status, headers: responseHeaders });
  } catch {
    return NextResponse.json({ detail: "Backend indisponível" }, { status: 502 });
  }
}

export const GET = forward;
export const POST = forward;
export const PUT = forward;
export const PATCH = forward;
export const DELETE = forward;
