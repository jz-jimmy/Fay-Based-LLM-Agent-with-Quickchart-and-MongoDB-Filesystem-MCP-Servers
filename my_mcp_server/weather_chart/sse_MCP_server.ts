import express from "express";
import { SSEServerTransport } from "@modelcontextprotocol/sdk/server/sse.js";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { getWeatherChartUrl } from "./weatherapi"; // correct path

const app = express();

const mcpServer = new McpServer({
  name: "Weather Chart Server",
  version: "1.0.0",
});

mcpServer.tool(
  "get_weather_chart",
  "Get a temperature chart for the past 5 days of the given city",
  {
    city: z.string().min(2).max(100),
  },
  async ({ city }) => {
    const url = await getWeatherChartUrl(city);
    if (url === -1) {
      return {
        content: [
          {
            type: "text",
            text: `Could not fetch temperature data for "${city}". Please check the city name.`,
          },
        ],
      };
    }

    return {
      content: [
        {
          type: "text",
          text: `Here is the temperature chart for "${city}":\n${url}`,
        },
      ],
    };
  }
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

app.listen(3000, () => {
  console.log("MCP Weather Server is running on port 3000");
});
