import { z } from "zod";

export const name = "arena.last_transition";
export const description =
  "Get the last stored transition — the most recent trade event with before/after states and metrics.";

export const inputSchema = z.object({
  config_path: z.string().optional(),
});

export const pythonTool = "varsity.last_transition";
