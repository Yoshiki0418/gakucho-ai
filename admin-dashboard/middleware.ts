// middleware.ts
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(req: NextRequest) {
  const isAdminPath = req.nextUrl.pathname.startsWith("/admin");

  if (!isAdminPath) return NextResponse.next();

  const isLoginPage = req.nextUrl.pathname === "/admin/login";
  const auth = req.cookies.get("admin-auth")?.value || req.headers.get("x-admin-auth");

  if (!auth && !isLoginPage) {
    return NextResponse.redirect(new URL("/admin/login", req.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/admin/:path*"],
};
