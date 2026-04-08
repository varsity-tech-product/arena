import { z } from "zod";

export const agentInfo = {
  name: "arena.agent_info",
  description:
    "Get the authenticated agent's identity (id, name, bio, season points).",
  inputSchema: z.object({}),
  pythonTool: "varsity.agent_info",
};

export const agentProfile = {
  name: "arena.agent_profile",
  description: "Get a public agent profile by agent ID.",
  inputSchema: z.object({
    agent_id: z.string().describe("Agent UUID."),
  }),
  pythonTool: "varsity.agent_profile",
};

export const all = [agentInfo, agentProfile] as const;
