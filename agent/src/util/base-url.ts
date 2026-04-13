export const PRODUCTION_BASE_URL = "https://api.otter.trade/v1";
export const STAGING_BASE_URL = "https://api.varsity.lol/v1";

export interface BaseUrlOverrideOptions {
  baseUrlOption?: string;
  envOption?: string;
  fallbackBaseUrl?: string;
}

function isLoopbackHostname(hostname: string): boolean {
  const normalized = hostname.trim().toLowerCase();
  return (
    normalized === "localhost" ||
    normalized === "127.0.0.1" ||
    normalized === "::1" ||
    normalized === "[::1]"
  );
}

export function validateBaseUrl(rawValue: string): string {
  const value = rawValue.trim();
  let parsed: URL;
  try {
    parsed = new URL(value);
  } catch {
    throw new Error("Arena API base URL must be a valid absolute URL.");
  }

  if (parsed.username || parsed.password) {
    throw new Error("Arena API base URL must not include embedded credentials.");
  }

  if (parsed.search || parsed.hash) {
    throw new Error("Arena API base URL must not include query parameters or fragments.");
  }

  if (parsed.protocol === "https:") {
    return value.replace(/\/+$/, "");
  }

  if (parsed.protocol === "http:" && isLoopbackHostname(parsed.hostname)) {
    return value.replace(/\/+$/, "");
  }

  throw new Error(
    "Arena API base URL must use HTTPS, or HTTP only for localhost/loopback."
  );
}

/**
 * Resolve the Arena API base URL override.
 *
 * Production remains the implicit default. The hidden `--env` flag is only
 * for local developer workflows and should not be surfaced in public UX.
 */
export function resolveBaseUrlOverride(
  options: BaseUrlOverrideOptions
): string | undefined {
  const baseUrl = options.baseUrlOption?.trim();
  if (baseUrl) {
    return validateBaseUrl(baseUrl);
  }

  const envOption = options.envOption?.trim().toLowerCase();
  if (envOption) {
    if (envOption === "prod") {
      return undefined;
    }
    if (envOption === "staging") {
      return STAGING_BASE_URL;
    }
    throw new Error("Internal arena environment must be `prod` or `staging`.");
  }

  const fallbackBaseUrl = options.fallbackBaseUrl?.trim();
  return fallbackBaseUrl ? validateBaseUrl(fallbackBaseUrl) : undefined;
}
