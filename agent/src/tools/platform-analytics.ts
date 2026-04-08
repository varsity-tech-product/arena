import { z } from "zod";

export const equityCurve = {
  name: "arena.equity_curve",
  description:
    "Get downsampled equity curve for an agent in a competition (up to 500 points).",
  inputSchema: z.object({
    competition_id: z.number().int().describe("Competition ID."),
    agent_id: z.string().describe("Agent UUID."),
    range: z
      .enum(["all", "7d", "30d"])
      .optional()
      .default("all")
      .describe("Time range."),
  }),
  pythonTool: "varsity.equity_curve",
};

export const dailyReturns = {
  name: "arena.daily_returns",
  description:
    "Get paginated daily return metrics for an agent in a competition (newest first).",
  inputSchema: z.object({
    competition_id: z.number().int().describe("Competition ID."),
    agent_id: z.string().describe("Agent UUID."),
    range: z.string().optional().default("all").describe("Time range."),
    page: z.number().int().optional().default(1).describe("Page number."),
    size: z
      .number()
      .int()
      .optional()
      .default(20)
      .describe("Items per page (1-100)."),
  }),
  pythonTool: "varsity.daily_returns",
};

export const performance = {
  name: "arena.performance",
  description:
    "Get performance KPIs for an agent in a competition (ROI, Sharpe, drawdown, win rate).",
  inputSchema: z.object({
    competition_id: z.number().int().describe("Competition ID."),
    agent_id: z.string().describe("Agent UUID."),
  }),
  pythonTool: "varsity.performance",
};

export const all = [equityCurve, dailyReturns, performance] as const;
