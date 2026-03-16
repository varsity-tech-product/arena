import { execSync } from "node:child_process";
import { existsSync } from "node:fs";
import { resolve } from "node:path";

export interface PythonCheck {
  ok: boolean;
  python: string | null;
  venv: boolean;
  deps: boolean;
  errors: string[];
}

export function checkPythonEnvironment(arenaRoot: string): PythonCheck {
  const errors: string[] = [];
  let python: string | null = null;
  let venv = false;
  let deps = false;

  // Check venv
  const venvPython = resolve(arenaRoot, ".venv", "bin", "python");
  const venvPythonWin = resolve(arenaRoot, ".venv", "Scripts", "python.exe");

  if (existsSync(venvPython)) {
    python = venvPython;
    venv = true;
  } else if (existsSync(venvPythonWin)) {
    python = venvPythonWin;
    venv = true;
  } else {
    errors.push(
      `No venv found. Run: python3 -m venv ${arenaRoot}/.venv`
    );
    // Try system python
    try {
      execSync("python3 --version", { stdio: "pipe" });
      python = "python3";
    } catch {
      errors.push("python3 not found in PATH.");
    }
  }

  if (!python) return { ok: false, python, venv, deps, errors };

  // Check deps
  try {
    execSync(`${python} -c "import mcp; import arena_agent"`, {
      stdio: "pipe",
      cwd: arenaRoot,
    });
    deps = true;
  } catch {
    errors.push(
      `Missing Python deps. Run: ${python} -m pip install -e ${arenaRoot} mcp`
    );
  }

  // Check env file
  if (!existsSync(resolve(arenaRoot, ".env.runtime.local"))) {
    errors.push(
      "Missing .env.runtime.local — copy .env.runtime.local.example and set VARSITY_API_KEY."
    );
  }

  return { ok: errors.length === 0, python, venv, deps, errors };
}
