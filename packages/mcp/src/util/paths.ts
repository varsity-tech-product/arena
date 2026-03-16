import { existsSync } from "node:fs";
import { resolve, dirname } from "node:path";

/**
 * Find the arena project root by walking up from cwd or using ARENA_ROOT env.
 */
export function findArenaRoot(): string {
  const envRoot = process.env.ARENA_ROOT;
  if (envRoot && existsSync(resolve(envRoot, "arena_agent", "__init__.py"))) {
    return resolve(envRoot);
  }

  let dir = process.cwd();
  for (let i = 0; i < 10; i++) {
    if (existsSync(resolve(dir, "arena_agent", "__init__.py"))) {
      return dir;
    }
    const parent = dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }

  throw new Error(
    "Cannot find arena project root. Set ARENA_ROOT or run from inside the arena directory."
  );
}

/**
 * Resolve the Python binary inside the arena venv.
 */
export function findPython(arenaRoot: string): string {
  const candidates = [
    resolve(arenaRoot, ".venv", "bin", "python"),
    resolve(arenaRoot, ".venv", "bin", "python3"),
    resolve(arenaRoot, ".venv", "Scripts", "python.exe"), // Windows
  ];
  for (const p of candidates) {
    if (existsSync(p)) return p;
  }
  throw new Error(
    `No Python venv found at ${arenaRoot}/.venv. Run: python3 -m venv ${arenaRoot}/.venv && ${arenaRoot}/.venv/bin/pip install -e ${arenaRoot}`
  );
}
