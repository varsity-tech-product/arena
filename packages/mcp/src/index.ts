/**
 * Arena Trade MCP Server
 *
 * Thin TypeScript MCP server that delegates trading operations to the
 * Python arena_agent runtime via a stdio child process bridge.
 */
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { PythonBridge } from "./python-bridge.js";
import { findArenaRoot } from "./util/paths.js";

import * as marketState from "./tools/market-state.js";
import * as competitionInfo from "./tools/competition-info.js";
import * as tradeAction from "./tools/trade-action.js";
import * as lastTransition from "./tools/last-transition.js";
import * as runtimeStart from "./tools/runtime-start.js";
import * as runtimeStop from "./tools/runtime-stop.js";

export function createServer(arenaRoot?: string): McpServer {
  const root = arenaRoot ?? findArenaRoot();
  const bridge = new PythonBridge(root);

  const server = new McpServer({
    name: "arena-trade",
    version: "0.1.0",
  });

  // --- Forwarded tools (Python bridge) ---

  const forwardedTools = [
    marketState,
    competitionInfo,
    tradeAction,
    lastTransition,
  ] as const;

  for (const tool of forwardedTools) {
    server.tool(
      tool.name,
      tool.description,
      tool.inputSchema.shape,
      async (args: Record<string, unknown>) => {
        try {
          const result = await bridge.callTool(tool.pythonTool, args);
          return {
            content: [
              { type: "text" as const, text: JSON.stringify(result, null, 2) },
            ],
          };
        } catch (err) {
          const msg = err instanceof Error ? err.message : String(err);
          return {
            content: [{ type: "text" as const, text: `Error: ${msg}` }],
            isError: true,
          };
        }
      }
    );
  }

  // --- Native tools (TypeScript) ---

  server.tool(
    runtimeStart.name,
    runtimeStart.description,
    runtimeStart.inputSchema.shape,
    async (args) => {
      const result = runtimeStart.execute(
        args as ReturnType<typeof runtimeStart.inputSchema.parse>,
        root
      );
      return {
        content: [
          { type: "text" as const, text: JSON.stringify(result, null, 2) },
        ],
      };
    }
  );

  server.tool(
    runtimeStop.name,
    runtimeStop.description,
    runtimeStop.inputSchema.shape,
    async () => {
      const result = runtimeStop.execute();
      return {
        content: [
          { type: "text" as const, text: JSON.stringify(result, null, 2) },
        ],
      };
    }
  );

  return server;
}

/**
 * Start the MCP server on stdio (default entry point for MCP clients).
 */
export async function serve(arenaRoot?: string): Promise<void> {
  const server = createServer(arenaRoot);
  const transport = new StdioServerTransport();
  await server.connect(transport);
}
