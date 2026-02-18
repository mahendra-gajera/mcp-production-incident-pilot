#!/usr/bin/env python3
"""
MCP Datadog Server (Simulated)
Provides tools to query metrics and system performance data
"""

import os
import json
import asyncio
from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.stdio import stdio_server

# Data directory
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# Create server
app = Server("datadog-server")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools"""
    return [
        Tool(
            name="get_metrics",
            description="Get system metrics (CPU, memory, error rates, response times)",
            inputSchema={
                "type": "object",
                "properties": {
                    "metric_type": {
                        "type": "string",
                        "description": "Type of metric (all, cpu, memory, errors, response_time)",
                        "default": "all"
                    },
                    "time_range": {
                        "type": "string",
                        "description": "Time range for metrics",
                        "default": "last_hour"
                    }
                }
            }
        ),
        Tool(
            name="get_anomalies",
            description="Detect anomalies in metrics (spikes, unusual patterns)",
            inputSchema={
                "type": "object",
                "properties": {
                    "threshold": {
                        "type": "number",
                        "description": "Anomaly detection threshold (percentage change)",
                        "default": 50
                    }
                }
            }
        ),
        Tool(
            name="get_error_rates",
            description="Get error rates over time",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Execute tool"""

    metrics_file = os.path.join(DATA_DIR, "metrics.json")

    if not os.path.exists(metrics_file):
        return [TextContent(
            type="text",
            text="Error: Metrics data file not found"
        )]

    with open(metrics_file, 'r') as f:
        data = json.load(f)

    metrics = data.get("metrics", [])

    if name == "get_metrics":
        metric_type = arguments.get("metric_type", "all")

        result = "System Metrics:\n\n"
        result += "Timestamp | CPU% | Memory% | Requests/min | Error% | Response Time\n"
        result += "-" * 80 + "\n"

        for m in metrics:
            result += f"{m['timestamp']} | "
            result += f"{m['cpu_usage']}% | "
            result += f"{m['memory_usage']}% | "
            result += f"{m['request_rate']} | "
            result += f"{m['error_rate']}% | "
            result += f"{m['response_time_ms']}ms\n"

        return [TextContent(type="text", text=result)]

    elif name == "get_anomalies":
        threshold = arguments.get("threshold", 50)

        anomalies = []

        for i in range(1, len(metrics)):
            prev = metrics[i - 1]
            curr = metrics[i]

            # Check for spikes in various metrics
            cpu_change = ((curr['cpu_usage'] - prev['cpu_usage']) / prev['cpu_usage'] * 100) if prev['cpu_usage'] > 0 else 0
            memory_change = ((curr['memory_usage'] - prev['memory_usage']) / prev['memory_usage'] * 100) if prev['memory_usage'] > 0 else 0
            error_change = ((curr['error_rate'] - prev['error_rate']) / prev['error_rate'] * 100) if prev['error_rate'] > 0 else 0
            response_change = ((curr['response_time_ms'] - prev['response_time_ms']) / prev['response_time_ms'] * 100) if prev['response_time_ms'] > 0 else 0

            if abs(cpu_change) > threshold:
                anomalies.append(f"CPU spike at {curr['timestamp']}: {prev['cpu_usage']}% → {curr['cpu_usage']}% ({cpu_change:+.1f}%)")

            if abs(memory_change) > threshold:
                anomalies.append(f"Memory spike at {curr['timestamp']}: {prev['memory_usage']}% → {curr['memory_usage']}% ({memory_change:+.1f}%)")

            if error_change > threshold:
                anomalies.append(f"Error rate spike at {curr['timestamp']}: {prev['error_rate']}% → {curr['error_rate']}% ({error_change:+.1f}%)")

            if response_change > threshold:
                anomalies.append(f"Response time spike at {curr['timestamp']}: {prev['response_time_ms']}ms → {curr['response_time_ms']}ms ({response_change:+.1f}%)")

        if anomalies:
            result = f"Detected {len(anomalies)} anomalies:\n\n"
            result += "\n".join(anomalies)
        else:
            result = f"No anomalies detected with threshold {threshold}%"

        return [TextContent(type="text", text=result)]

    elif name == "get_error_rates":
        result = "Error Rates Over Time:\n\n"

        for m in metrics:
            result += f"{m['timestamp']}: {m['error_rate']}% "
            result += f"({int(m['request_rate'] * m['error_rate'] / 100)} errors)\n"

        return [TextContent(type="text", text=result)]

    else:
        return [TextContent(
            type="text",
            text=f"Error: Unknown tool '{name}'"
        )]


async def main():
    """Run the server"""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
