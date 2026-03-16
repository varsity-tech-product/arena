import { z } from "zod";

export const name = "arena.market_state";
export const description =
  "Get the current Arena market state — price, orderbook, account, position, competition, and computed indicators.";

export const inputSchema = z.object({
  config_path: z
    .string()
    .optional()
    .describe("Path to runtime YAML config."),
  signal_indicators: z
    .array(
      z.object({
        indicator: z.string(),
        params: z.record(z.unknown()).optional().default({}),
        key: z.string().optional(),
      })
    )
    .optional()
    .describe("Optional indicator specs to compute."),
});

export const pythonTool = "varsity.market_state";
