#!/usr/bin/env node
/**
 * LeRoy MCP connector template.
 *
 * `leroy mcp add` clones this folder and helps you fill in your tools, so LeRoy can talk to
 * any system with an API. Docs: https://modelcontextprotocol.io
 *
 * Rules:
 *  - Read secrets from the environment (see .env.example). NEVER hardcode keys.
 *  - Keep each tool small and well-described — the description is what LeRoy reads to decide
 *    when to call it.
 */
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

const server = new McpServer({ name: "my-connector", version: "0.1.0" });

// --- Example tool: replace with your own -----------------------------------
server.tool(
  "ping",
  "Health check — returns 'ok'. Replace with real tools for your system.",
  {},
  async () => ({ content: [{ type: "text", text: "ok" }] }),
);

// Example of a tool that takes input and reads a key from the environment:
//
// const API_KEY = process.env.MY_CONNECTOR_API_KEY;
// server.tool(
//   "search",
//   "Search your system for records matching a query.",
//   { query: z.string().describe("what to search for") },
//   async ({ query }) => {
//     // ...call your API using API_KEY...
//     return { content: [{ type: "text", text: `results for: ${query}` }] };
//   },
// );
// ---------------------------------------------------------------------------

const transport = new StdioServerTransport();
await server.connect(transport);
