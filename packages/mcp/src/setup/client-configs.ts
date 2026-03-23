import { writeFileSync, readFileSync, existsSync, mkdirSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { homedir } from "node:os";
import {
  ensureOpenClawTradingAgent,
  openclawMcpInstructions,
} from "./openclaw-agent.js";
import type { ManagedAgent } from "../util/home.js";

interface McpServerEntry {
  type?: string;
  command: string;
  args: string[];
  env?: Record<string, string>;
}

function mergeConfig(
  path: string,
  serverName: string,
  entry: McpServerEntry
): void {
  let existing: Record<string, unknown> = {};
  if (existsSync(path)) {
    try {
      existing = JSON.parse(readFileSync(path, "utf-8"));
    } catch {
      // Overwrite invalid JSON
    }
  }
  const servers =
    (existing.mcpServers as Record<string, unknown>) ?? {};
  servers[serverName] = entry;
  existing.mcpServers = servers;

  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, JSON.stringify(existing, null, 2) + "\n");
}

// ── Claude Code (project-local .mcp.json) ──────────────────────────

export function setupClaudeCode(arenaRoot: string): string {
  const configPath = resolve(arenaRoot, ".mcp.json");
  mergeConfig(configPath, "arena", {
    type: "stdio",
    command: "arena-mcp",
    args: ["serve"],
    env: { ARENA_ROOT: arenaRoot },
  });
  return configPath;
}

// ── Claude Code (user-scope ~/.claude.json) ─────────────────────────

export function setupClaudeCodeUser(arenaRoot: string): string {
  const configPath = resolve(homedir(), ".claude.json");
  mergeConfig(configPath, "arena", {
    type: "stdio",
    command: "arena-mcp",
    args: ["serve"],
    env: { ARENA_ROOT: arenaRoot },
  });
  return configPath;
}

// ── Claude Desktop ──────────────────────────────────────────────────

export function setupClaudeDesktop(arenaRoot: string): string {
  const platform = process.platform;
  let configDir: string;
  if (platform === "darwin") {
    configDir = resolve(
      homedir(),
      "Library",
      "Application Support",
      "Claude"
    );
  } else {
    configDir = resolve(homedir(), ".config", "Claude");
  }
  const configPath = resolve(configDir, "claude_desktop_config.json");
  mergeConfig(configPath, "arena", {
    command: "arena-mcp",
    args: ["serve"],
    env: { ARENA_ROOT: arenaRoot },
  });
  return configPath;
}

// ── Cursor ──────────────────────────────────────────────────────────

export function setupCursor(arenaRoot: string): string {
  const configPath = resolve(arenaRoot, ".cursor", "mcp.json");
  mergeConfig(configPath, "arena", {
    command: "arena-mcp",
    args: ["serve"],
    env: { ARENA_ROOT: arenaRoot },
  });
  return configPath;
}

// ── Gemini CLI (~/.gemini/settings.json) ────────────────────────────

export function setupGemini(arenaRoot: string): string {
  const configPath = resolve(homedir(), ".gemini", "settings.json");
  mergeConfig(configPath, "arena", {
    command: "arena-mcp",
    args: ["serve"],
    env: { ARENA_ROOT: arenaRoot },
  });
  return configPath;
}

// ── Codex CLI (~/.codex/config.toml) ────────────────────────────────

export function setupCodex(arenaRoot: string): string {
  const configPath = resolve(homedir(), ".codex", "config.toml");
  mkdirSync(dirname(configPath), { recursive: true });

  let content = "";
  if (existsSync(configPath)) {
    try {
      content = readFileSync(configPath, "utf-8");
    } catch {
      // Overwrite if unreadable
    }
  }

  writeFileSync(configPath, mergeCodexToml(content, arenaRoot), "utf-8");
  return configPath;
}

/**
 * Pure function: merge arena MCP server into Codex config.toml content.
 * Removes any existing [mcp_servers.arena] and [mcp_servers.arena.*]
 * sections, then appends the correct block.
 */
export function mergeCodexToml(content: string, arenaRoot: string): string {
  const lines = content.split("\n");
  const filtered: string[] = [];
  let inArenaSection = false;

  for (const line of lines) {
    const trimmed = line.trim();
    if (/^\[/.test(trimmed)) {
      inArenaSection = /^\[mcp_servers\.arena(?:\..*)?\]$/.test(trimmed);
    }
    if (!inArenaSection) {
      filtered.push(line);
    }
  }

  // Trim trailing blank lines
  while (filtered.length > 0 && filtered[filtered.length - 1].trim() === "") {
    filtered.pop();
  }

  const base = filtered.length > 0 ? filtered.join("\n") + "\n" : "";
  const escaped = arenaRoot.replace(/\\/g, "\\\\").replace(/"/g, '\\"');
  const section = [
    "",
    "[mcp_servers.arena]",
    'command = "arena-mcp"',
    'args = ["serve"]',
    "",
    "[mcp_servers.arena.env]",
    `ARENA_ROOT = "${escaped}"`,
    "",
  ].join("\n");

  return base + section;
}

// ── OpenClaw ────────────────────────────────────────────────────────

export function setupOpenClaw(
  arenaRoot: string,
  _options?: { mode?: string }
): string {
  // Verify openclaw is available — never modify user's global config or agents
  ensureOpenClawTradingAgent(arenaRoot);

  // Print instructions for optional MCP tools setup (user applies manually)
  console.log(openclawMcpInstructions(arenaRoot));

  return "(no config modified — see instructions above)";
}

// ── Client setup registry ───────────────────────────────────────────

export const CLIENT_SETUP: Record<
  string,
  (root: string, options?: { mode?: string }) => string
> = {
  "claude-code": setupClaudeCode,
  "claude-desktop": setupClaudeDesktop,
  cursor: setupCursor,
  gemini: setupGemini,
  codex: setupCodex,
  openclaw: setupOpenClaw,
};

// ── Auto-wire: called during `arena-agent init` ─────────────────────

interface WiredEntry {
  backend: string;
  configPath: string;
}

export function autoWireMcpForAgent(
  home: string,
  agent: ManagedAgent,
  detectedBackends: ManagedAgent[]
): WiredEntry[] {
  const wired: WiredEntry[] = [];

  const wireOne = (label: string, fn: () => string): void => {
    try {
      const configPath = fn();
      wired.push({ backend: label, configPath });
    } catch {
      // Don't fail init if MCP wiring fails
    }
  };

  switch (agent) {
    case "claude":
      wireOne("Claude Code", () => setupClaudeCodeUser(home));
      break;
    case "gemini":
      wireOne("Gemini CLI", () => setupGemini(home));
      break;
    case "codex":
      wireOne("Codex CLI", () => setupCodex(home));
      break;
    case "openclaw":
      // Never modify user's OpenClaw config — just print MCP setup instructions
      wireOne("OpenClaw", () => setupOpenClaw(home));
      break;
    case "auto":
      // Wire all detected backends except OpenClaw MCP (requires explicit opt-in)
      for (const b of detectedBackends) {
        if (b === "openclaw") continue;
        wired.push(...autoWireMcpForAgent(home, b, []));
      }
      break;
    // "rule" → no MCP wiring needed
  }

  return wired;
}
