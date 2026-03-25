import { z } from "zod";
import { stop } from "./runtime-start.js";

export const name = "arena.runtime_stop";
export const description = "Stop the autonomous trading agent runtime.";

export const inputSchema = z.object({});

export { stop as execute };
