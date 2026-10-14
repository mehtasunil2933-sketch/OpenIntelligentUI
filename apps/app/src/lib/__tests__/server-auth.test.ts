import { describe, expect, it } from "vitest";
import { checkServerAuth } from "../server-auth";

const config = { PROVIDER_KEYS_MODE: "server", OIUI_AUTH_USERNAME: "admin", OIUI_AUTH_PASSWORD: "test-password-long" };
describe("server provider authentication", () => {
  it("leaves BYOK unchanged", () => expect(checkServerAuth(new Headers(), {})).toBe("allow"));
  it("fails closed without a password", () => expect(checkServerAuth(new Headers(), { PROVIDER_KEYS_MODE: "server" })).toBe("unconfigured"));
  it("rejects short passwords", () => expect(checkServerAuth(new Headers(), { ...config, OIUI_AUTH_PASSWORD: "short" })).toBe("unconfigured"));
  it("requires authentication", () => expect(checkServerAuth(new Headers(), config)).toBe("unauthorized"));
  it("rejects incorrect credentials", () => expect(checkServerAuth(new Headers({ authorization: "Basic wrong" }), config)).toBe("unauthorized"));
  it("accepts correct credentials", () => {
    const header = `Basic ${Buffer.from("admin:test-password-long").toString("base64")}`;
    expect(checkServerAuth(new Headers({ authorization: header }), config)).toBe("allow");
  });
});
