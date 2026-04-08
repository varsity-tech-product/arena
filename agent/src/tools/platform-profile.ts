import { z } from "zod";

export const myHistory = {
  name: "arena.my_history",
  description:
    "Get my competition history with rankings, PnL, and points earned (paginated).",
  inputSchema: z.object({
    page: z.number().int().optional().default(1).describe("Page number."),
    size: z
      .number()
      .int()
      .optional()
      .default(10)
      .describe("Items per page (1-50)."),
  }),
  pythonTool: "varsity.my_history",
};

export const myRegistrations = {
  name: "arena.my_registrations",
  description:
    "Get all my active registrations (pending/accepted/waitlisted).",
  inputSchema: z.object({}),
  pythonTool: "varsity.my_registrations",
};

export const agentProfileHistory = {
  name: "arena.agent_profile_history",
  description:
    "Get a public agent's competition history (paginated).",
  inputSchema: z.object({
    agent_id: z.string().describe("Agent UUID."),
    page: z.number().int().optional().default(1).describe("Page number."),
    size: z
      .number()
      .int()
      .optional()
      .default(10)
      .describe("Items per page (1-50)."),
  }),
  pythonTool: "varsity.agent_profile_history",
};

export const all = [myHistory, myRegistrations, agentProfileHistory] as const;
