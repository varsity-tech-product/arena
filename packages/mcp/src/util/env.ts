import { readFileSync, existsSync } from "node:fs";
import { resolve } from "node:path";

/**
 * Load .env.runtime.local from the arena root and return as a key-value map.
 */
export function loadEnvFile(arenaRoot: string): Record<string, string> {
  const envPath = resolve(arenaRoot, ".env.runtime.local");
  if (!existsSync(envPath)) return {};

  const env: Record<string, string> = {};
  const content = readFileSync(envPath, "utf-8");
  for (const line of content.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const eqIdx = trimmed.indexOf("=");
    if (eqIdx < 1) continue;
    const key = trimmed.slice(0, eqIdx).trim();
    let value = trimmed.slice(eqIdx + 1).trim();
    // Strip surrounding quotes
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    env[key] = value;
  }
  return env;
}

/**
 * Build process env for child Python processes.
 */
export function buildChildEnv(arenaRoot: string): Record<string, string> {
  const base = { ...process.env } as Record<string, string>;
  const local = loadEnvFile(arenaRoot);
  return { ...base, ...local };
}
