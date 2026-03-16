import { z } from "zod";
import { spawn, type ChildProcess } from "node:child_process";
import { findPython } from "../util/paths.js";
import { buildChildEnv } from "../util/env.js";

export const name = "arena.runtime_start";
export const description =
  "Start the autonomous trading agent runtime in the background.";

export const inputSchema = z.object({
  config: z
    .string()
    .optional()
    .default("arena_agent/config/codex_agent_config.yaml")
    .describe("Path to runtime YAML config."),
  agent: z
    .enum(["config", "rule", "claude", "codex", "auto", "tap"])
    .optional()
    .default("auto")
    .describe("Agent type."),
  model: z.string().optional().describe("Model override (e.g. sonnet)."),
  iterations: z
    .number()
    .optional()
    .describe("Max iterations. Omit for unlimited."),
});

let runtimeProcess: ChildProcess | null = null;

export function execute(
  args: z.infer<typeof inputSchema>,
  arenaRoot: string
): { pid: number | null; status: string; config: string; agent: string } {
  if (runtimeProcess && !runtimeProcess.killed) {
    return {
      pid: runtimeProcess.pid ?? null,
      status: "already_running",
      config: args.config,
      agent: args.agent,
    };
  }

  const python = findPython(arenaRoot);
  const env = buildChildEnv(arenaRoot);

  const cmdArgs = [
    "-m",
    "arena_agent",
    "run",
    "--agent",
    args.agent,
    "--config",
    args.config,
  ];
  if (args.model) cmdArgs.push("--model", args.model);
  if (args.iterations !== undefined)
    cmdArgs.push("--iterations", String(args.iterations));

  runtimeProcess = spawn(python, cmdArgs, {
    cwd: arenaRoot,
    env,
    stdio: "ignore",
    detached: true,
  });
  runtimeProcess.unref();

  const pid = runtimeProcess.pid ?? null;

  runtimeProcess.on("exit", () => {
    runtimeProcess = null;
  });

  return { pid, status: "started", config: args.config, agent: args.agent };
}

export function stop(): { status: string; pid: number | null } {
  if (!runtimeProcess || runtimeProcess.killed) {
    runtimeProcess = null;
    return { status: "not_running", pid: null };
  }
  const pid = runtimeProcess.pid ?? null;
  runtimeProcess.kill("SIGTERM");
  runtimeProcess = null;
  return { status: "stopped", pid };
}
