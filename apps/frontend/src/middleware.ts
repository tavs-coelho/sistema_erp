import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const DEFAULT_AUTHENTICATED_ROUTE = "/";

export function middleware(request: NextRequest) {
  const token = request.cookies.get("session")?.value;
  const publicPrefixes = ["/public", "/login", "/_next"];
  const isPublic = publicPrefixes.some((prefix) => request.nextUrl.pathname.startsWith(prefix));

  if (!token && !isPublic) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  if (token && request.nextUrl.pathname === "/login") {
    return NextResponse.redirect(new URL(DEFAULT_AUTHENTICATED_ROUTE, request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
