#!/usr/bin/env node

/**
 * arena-mcp CLI
 *
 * Usage:
 *   arena-mcp serve                    Start MCP server on stdio
 *   arena-mcp setup --client <name>    Configure an MCP client
 *   arena-mcp check                    Validate Python environment
 */
import { serve } from "./index.js";
import { findArenaRoot } from "./util/paths.js";
import { checkPythonEnvironment } from "./setup/detect-python.js";
import { CLIENT_SETUP } from "./setup/client-configs.js";

const args = process.argv.slice(2);
const command = args[0] ?? "serve";

async function main(): Promise<void> {
  if (command === "serve") {
    const rootIdx = args.indexOf("--arena-root");
    const root = rootIdx >= 0 ? args[rootIdx + 1] : undefined;
    await serve(root);
    return;
  }

  if (command === "check") {
    const root = findArenaRoot();
    const result = checkPythonEnvironment(root);
    console.log(`Arena root:  ${root}`);
    console.log(`Python:      ${result.python ?? "not found"}`);
    console.log(`Venv:        ${result.venv ? "ok" : "missing"}`);
    console.log(`Deps:        ${result.deps ? "ok" : "missing"}`);
    if (result.errors.length > 0) {
      console.log("\nIssues:");
      for (const err of result.errors) {
        console.log(`  - ${err}`);
      }
      process.exit(1);
    }
    console.log("\nAll checks passed.");
    return;
  }

  if (command === "setup") {
    const clientIdx = args.indexOf("--client");
    if (clientIdx < 0 || !args[clientIdx + 1]) {
      console.error(
        `Usage: arena-mcp setup --client <${Object.keys(CLIENT_SETUP).join("|")}>`
      );
      process.exit(1);
    }
    const clientName = args[clientIdx + 1];
    const setupFn = CLIENT_SETUP[clientName];
    if (!setupFn) {
      console.error(
        `Unknown client: ${clientName}. Supported: ${Object.keys(CLIENT_SETUP).join(", ")}`
      );
      process.exit(1);
    }

    const root = findArenaRoot();

    // Validate environment first
    console.log("Checking Python environment...");
    const check = checkPythonEnvironment(root);
    if (check.errors.length > 0) {
      console.log("\nIssues found:");
      for (const err of check.errors) {
        console.log(`  - ${err}`);
      }
      console.log("\nFix the issues above, then re-run setup.");
      process.exit(1);
    }

    const configPath = setupFn(root);
    console.log(`\nConfigured ${clientName} at: ${configPath}`);
    console.log(`Arena root: ${root}`);
    console.log("\nTools available:");
    console.log("  arena.market_state       Get market/account/position state");
    console.log("  arena.competition_info   Competition metadata");
    console.log("  arena.trade_action       Submit a trade");
    console.log("  arena.last_transition    Last trade event");
    console.log("  arena.runtime_start      Start autonomous agent");
    console.log("  arena.runtime_stop       Stop autonomous agent");
    return;
  }

  console.error(`Unknown command: ${command}`);
  console.error("Usage: arena-mcp [serve|setup|check]");
  process.exit(1);
}

main().catch((err) => {
  console.error(err instanceof Error ? err.message : err);
  process.exit(1);
});
