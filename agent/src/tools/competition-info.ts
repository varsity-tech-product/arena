import { z } from "zod";

export const name = "arena.competition_info";
export const description =
  "Get compact Arena competition metadata — status, time remaining, trade limits.";

export const inputSchema = z.object({
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

export const pythonTool = "varsity.competition_info";
