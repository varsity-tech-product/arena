import { describe, expect, it } from "vitest";

import {
  STAGING_BASE_URL,
  resolveBaseUrlOverride,
  validateBaseUrl,
} from "./base-url.js";

describe("resolveBaseUrlOverride", () => {
  it("prefers --base-url over the hidden --env flag and fallback", () => {
    expect(
      resolveBaseUrlOverride({
        baseUrlOption: "https://custom.example/v1",
        envOption: "staging",
        fallbackBaseUrl: "https://fallback.example/v1",
      })
    ).toBe("https://custom.example/v1");
  });

  it("maps staging to the staging API URL", () => {
    expect(resolveBaseUrlOverride({ envOption: "staging" })).toBe(
      STAGING_BASE_URL
    );
  });

  it("clears an existing override when prod is selected", () => {
    expect(
      resolveBaseUrlOverride({
        envOption: "prod",
        fallbackBaseUrl: STAGING_BASE_URL,
      })
    ).toBeUndefined();
  });

  it("falls back to an existing stored base URL when no override is provided", () => {
    expect(
      resolveBaseUrlOverride({
        fallbackBaseUrl: STAGING_BASE_URL,
      })
    ).toBe(STAGING_BASE_URL);
  });

  it("rejects unknown internal environments", () => {
    expect(() =>
      resolveBaseUrlOverride({ envOption: "qa" })
    ).toThrow("Internal arena environment must be `prod` or `staging`.");
  });

  it("rejects insecure remote http overrides", () => {
    expect(() =>
      resolveBaseUrlOverride({ baseUrlOption: "http://api.varsity.lol/v1" })
    ).toThrow(
      "Arena API base URL must use HTTPS, or HTTP only for localhost/loopback."
    );
  });
});

describe("validateBaseUrl", () => {
  it("normalizes trailing slashes for https URLs", () => {
    expect(validateBaseUrl("https://api.varsity.lol/v1/")).toBe(
      "https://api.varsity.lol/v1"
    );
  });

  it("allows localhost http for local testing", () => {
    expect(validateBaseUrl("http://127.0.0.1:8080/v1")).toBe(
      "http://127.0.0.1:8080/v1"
    );
  });

  it("rejects embedded credentials", () => {
    expect(() =>
      validateBaseUrl("https://user:pass@api.varsity.lol/v1")
    ).toThrow("Arena API base URL must not include embedded credentials.");
  });

  it("rejects query strings and fragments", () => {
    expect(() =>
      validateBaseUrl("https://api.varsity.lol/v1?token=x")
    ).toThrow(
      "Arena API base URL must not include query parameters or fragments."
    );
  });
});
