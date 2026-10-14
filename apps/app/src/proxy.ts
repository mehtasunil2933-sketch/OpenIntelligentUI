import { NextRequest, NextResponse } from "next/server";
import { checkServerAuth } from "./lib/server-auth";

export function proxy(request: NextRequest) {
  if (request.nextUrl.pathname === "/api/health") return NextResponse.next();
  const result = checkServerAuth(request.headers);
  if (result === "allow") return NextResponse.next();
  const headers = { "Cache-Control": "no-store" };
  if (result === "unconfigured") {
    return new NextResponse("Set OIUI_AUTH_PASSWORD (at least 12 characters) on the web service before using server provider keys.", { status: 503, headers });
  }
  return new NextResponse("Authentication required.", {
    status: 401,
    headers: { ...headers, "WWW-Authenticate": 'Basic realm="Open Intelligent UI", charset="UTF-8"' },
  });
}

export const config = { matcher: ["/((?!_next/static|_next/image|favicon.ico|icon.svg).*)"] };
