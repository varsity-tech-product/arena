import { execFileSync, spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { resolve } from "node:path";
import { localPythonSourcePath } from "../util/home.js";

export interface BootstrapOptions {
  home: string;
  pythonInstallSource: string;
  reinstall?: boolean;
  installMonitor?: boolean;
  installMcp?: boolean;
}

export function detectSystemPython(): string | null {
  const candidates: Array<{ command: string; args: string[] }> = [
    { command: "python3", args: ["--version"] },
    { command: "python", args: ["--version"] },
  ];
  if (process.platform === "win32") {
    candidates.unshift({ command: "py", args: ["-3", "--version"] });
  }

  for (const candidate of candidates) {
    const result = spawnSync(candidate.command, candidate.args, {
      stdio: "ignore",
    });
    if (result.status === 0) {
      return candidate.command;
    }
  }
  return null;
}

export function venvPythonPath(home: string): string {
  return process.platform === "win32"
    ? resolve(home, ".venv", "Scripts", "python.exe")
    : resolve(home, ".venv", "bin", "python");
}

export function bootstrapPythonRuntime(options: BootstrapOptions): string {
  const pythonBin = detectSystemPython();
  if (!pythonBin) {
    throw new Error("Python 3 was not found in PATH. Install Python 3.10+ first.");
  }

  const venvPython = venvPythonPath(options.home);
  if (!existsSync(venvPython)) {
    const args =
      pythonBin === "py"
        ? ["-3", "-m", "venv", resolve(options.home, ".venv")]
        : ["-m", "venv", resolve(options.home, ".venv")];
    execFileSync(pythonBin, args, { stdio: "inherit" });
  }

  execFileSync(
    venvPython,
    ["-m", "pip", "install", "--upgrade", "pip"],
    { stdio: "inherit" }
  );

  const installSource = resolveInstallSource(options.pythonInstallSource);
  const installArgs = ["-m", "pip", "install"];
  if (options.reinstall) {
    installArgs.push("--force-reinstall");
  }
  installArgs.push(installSource);
  execFileSync(venvPython, installArgs, { stdio: "inherit" });

  const extraPackages: string[] = [];
  if (options.installMcp ?? true) {
    extraPackages.push("mcp>=1.12.0");
  }
  if (options.installMonitor ?? true) {
    extraPackages.push("textual>=0.79.0", "rich>=13.7.0");
  }
  if (extraPackages.length > 0) {
    execFileSync(
      venvPython,
      ["-m", "pip", "install", ...extraPackages],
      { stdio: "inherit" }
    );
  }

  return venvPython;
}

export function resolveInstallSource(source: string): string {
  if (source === "local") {
    const localSource = localPythonSourcePath();
    if (!localSource) {
      throw new Error("Local Python source is unavailable from this npm install.");
    }
    return localSource;
  }
  return source;
}

export function commandAvailable(command: string): boolean {
  const locator = process.platform === "win32" ? "where" : "which";
  const result = spawnSync(locator, [command], { stdio: "ignore" });
  return result.status === 0;
}
