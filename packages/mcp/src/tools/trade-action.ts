import { z } from "zod";

export const name = "arena.trade_action";
export const description =
  "Submit a trading action — OPEN_LONG, OPEN_SHORT, CLOSE_POSITION, UPDATE_TPSL, or HOLD.";

export const inputSchema = z.object({
  type: z
    .enum(["OPEN_LONG", "OPEN_SHORT", "CLOSE_POSITION", "UPDATE_TPSL", "HOLD"])
    .describe("Action type."),
  size: z.number().optional().describe("Position size (e.g. 0.001 BTC)."),
  tp: z.number().optional().describe("Take-profit price."),
  sl: z.number().optional().describe("Stop-loss price."),
  execute: z
    .boolean()
    .optional()
    .default(false)
    .describe("Set true to execute a real trade (overrides dry_run)."),
  config_path: z.string().optional(),
  signal_indicators: z
    .array(
      z.object({
        indicator: z.string(),
        params: z.record(z.unknown()).optional().default({}),
        key: z.string().optional(),
      })
    )
    .optional(),
});

export const pythonTool = "varsity.trade_action";
