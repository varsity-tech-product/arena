import { z } from "zod";

export const register = {
  name: "arena.register",
  description:
    "Register for an agent competition. Must be in 'registration_open' state.",
  inputSchema: z.object({
    slug: z.string().describe("Competition slug."),
  }),
  pythonTool: "varsity.register",
};

export const all = [register] as const;
