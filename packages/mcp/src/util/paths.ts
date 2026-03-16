import { existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { defaultArenaHome, isArenaHome, localPythonSourcePath } from "./home.js";

/**
 * Find the arena project root by walking up from cwd or using ARENA_ROOT env.
 */
export function findArenaRoot(): string {
  const envRoot = process.env.ARENA_ROOT;
  if (envRoot && isArenaHome(resolve(envRoot))) {
    return resolve(envRoot);
  }

  const envHome = process.env.ARENA_HOME;
  if (envHome && isArenaHome(resolve(envHome))) {
    return resolve(envHome);
  }

  let dir = process.cwd();
  for (let i = 0; i < 10; i++) {
    if (isArenaHome(dir)) {
      return dir;
    }
    const parent = dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }

  const managedHome = defaultArenaHome();
  if (isArenaHome(managedHome)) {
    return managedHome;
  }

  const localSource = localPythonSourcePath();
  if (localSource && isArenaHome(localSource)) {
    return localSource;
  }

  throw new Error(
    "Cannot find an Arena home. Run `arena-agent init`, or set ARENA_ROOT to a configured Arena directory."
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
    `No Python venv found at ${arenaRoot}/.venv. Run \`arena-agent init\` to bootstrap the runtime.`
  );
}
