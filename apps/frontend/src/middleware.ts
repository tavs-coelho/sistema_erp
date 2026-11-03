import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * Navigation convenience only. Actual authentication/authorization always
 * happens in FastAPI by checking the signed JWT and tenant-bound device row.
 */
export function middleware(request: NextRequest) {
  const path = request.nextUrl.pathname;
  const isPublic = path === "/login" || path === "/public"
    || path.startsWith("/public/") || path.startsWith("/_next/");
  const hasCookie = Boolean(request.cookies.get("erp_access")?.value
    || request.cookies.get("erp_refresh")?.value);
  if (!hasCookie && !isPublic) {
    const destination = new URL("/login", request.url);
    destination.searchParams.set("returnTo", path);
    return NextResponse.redirect(destination);
  }
  if (hasCookie && path === "/login") {
    // A stale cookie can be present. Browser login is still accessible when
    // the caller requests it explicitly after a session expires.
    if (request.nextUrl.searchParams.get("expired") !== "1") {
      return NextResponse.redirect(new URL("/", request.url));
    }
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
