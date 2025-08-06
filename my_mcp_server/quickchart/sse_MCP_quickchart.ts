// sse_MCP_quickchart.ts
import express from "express";
import { SSEServerTransport } from "@modelcontextprotocol/sdk/server/sse.js";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { generateChartImageFile } from "./quickchart";
import path from "path";
import { promises as fs } from "fs";        // ▲ for cleanup

const app = express();

// Serve static chart files
app.use("/charts", express.static(path.join(process.cwd(), "charts")));

const mcpServer = new McpServer({
  name: "Local QuickChart Server",
  version: "1.0.0",
});

mcpServer.tool(
  "generate_chart",
  "Generate a chart image with various chart styles and return a local URL",
  {
    title: z.string().min(1).max(100),

    // --- minimal change #1: flexible input -------------------------
    labels: z
      .union([z.array(z.string()), z.string()])
      .transform((v) =>
        typeof v === "string"
          ? v.split(/[;,|\s]+/).map((s) => s.trim()).filter(Boolean)
          : v,
      ),

    // Accept "20,25,30" or [20,25,30]
    data: z
      .union([z.array(z.number()), z.string()])
      .transform((v) =>
        typeof v === "string"
          ? v
              .split(/[;,|\s\[\]]+/)
              .map((s) => Number(s.trim()))
              .filter((n) => !Number.isNaN(n))
          : v,
      ),
    // ---------------------------------------------------------------

    chartType: z.enum(["line", "bar", "pie", "radar"]).default("line"),
  },
  async ({ title, labels, data, chartType }) => {
    // --- minimal change #2: sanity-check lengths -------------------
    if (labels.length !== data.length) {
      return {
        content: [
          {
            type: "text",
            text: `The number of labels (${labels.length}) and data points (${data.length}) must match.`,
          },
        ],
      };
    }
    // ---------------------------------------------------------------

    const imagePath = await generateChartImageFile(
      title,
      labels,
      data,
      chartType,
    );

    if (imagePath === -1) {
      return {
        content: [
          {
            type: "text",
            text: "Could not generate chart image.",
          },
        ],
      };
    }

    // const fullUrl = `http://localhost:3001${imagePath}`; 
    //annotated after quickchart.ts changes due to not storing locally

    const fullUrl = imagePath.startsWith("http")
      ? imagePath        // now already an absolute link
      : `http://localhost:3001${imagePath}`;

    return {
      content: [
        {
          type: "text",
          // text: `Here is the chart for "${title}":\n${fullUrl}`,
          text: fullUrl,
        },
      ],
    };
  },
);

let transport: SSEServerTransport | null = null;

app.get("/sse", (req, res) => {
  transport = new SSEServerTransport("/messages", res);
  mcpServer.connect(transport);
});

app.post("/messages", (req, res) => {
  if (transport) {
    transport.handlePostMessage(req, res);
    }
});

/* ────────────────────────────────────────────────────────────────────────── */
/*  Automatic cleanup: delete PNGs older than 7 days from ./charts           */
/* ────────────────────────────────────────────────────────────────────────── */
const CHARTS_DIR = path.join(process.cwd(), "charts");   // ▲
const MAX_FILE_AGE_MS = 7 * 24 * 60 * 60 * 1000;         // ▲ 7 days
const CLEAN_INTERVAL_MS = 12 * 60 * 60 * 1000;           // ▲ run twice a day

async function cleanOldCharts() {                         // ▲
  try {
    const files = await fs.readdir(CHARTS_DIR);
    const now = Date.now();
    await Promise.all(
      files
        .filter((f) => f.endsWith(".png"))
        .map(async (file) => {
          const full = path.join(CHARTS_DIR, file);
          const { mtimeMs } = await fs.stat(full);
          if (now - mtimeMs > MAX_FILE_AGE_MS) {
            await fs.unlink(full);
          }
        }),
    );
  } catch (err) {
    // Silent fail: don't crash server because of cleanup
    console.error("[chart-cleanup]", err);
  }
}

/* kick off once on startup, then every 12 h ------------------------------ */
cleanOldCharts();                                          // ▲ initial sweep
setInterval(cleanOldCharts, CLEAN_INTERVAL_MS);            // ▲ periodic sweep
/* ────────────────────────────────────────────────────────────────────────── */

app.listen(3001, () => {
  console.log("Local QuickChart MCP Server running on port 3001");
});
