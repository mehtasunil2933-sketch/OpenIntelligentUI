import { timingSafeEqual } from "node:crypto";

export function checkServerAuth(headers: Headers, env: Record<string, string | undefined> = process.env): "allow" | "unauthorized" | "unconfigured" {
  if (env.PROVIDER_KEYS_MODE !== "server") return "allow";
  const username = env.OIUI_AUTH_USERNAME?.trim() || "admin";
  const password = env.OIUI_AUTH_PASSWORD;
  if (!password || password.length < 12 || username.includes(":")) return "unconfigured";
  const supplied = headers.get("authorization") || "";
  const expected = `Basic ${Buffer.from(`${username}:${password}`, "utf8").toString("base64")}`;
  const a = Buffer.from(supplied);
  const b = Buffer.from(expected);
  return a.length === b.length && timingSafeEqual(a, b) ? "allow" : "unauthorized";
}
