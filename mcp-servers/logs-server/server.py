#!/usr/bin/env python3
"""
MCP Logs Server
Provides tools to read and search application logs
"""

import os
import asyncio
from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.stdio import stdio_server

# Data directory
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# Create server
app = Server("logs-server")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools"""
    return [
        Tool(
            name="read_logs",
            description="Read application logs from log files",
            inputSchema={
                "type": "object",
                "properties": {
                    "file": {
                        "type": "string",
                        "description": "Log file name (e.g., 'app.log', 'error.log')"
                    }
                },
                "required": ["file"]
            }
        ),
        Tool(
            name="search_logs",
            description="Search for specific patterns in logs",
            inputSchema={
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Search pattern (e.g., 'ERROR', '500', 'timeout')"
                    },
                    "file": {
                        "type": "string",
                        "description": "Log file to search in",
                        "default": "app.log"
                    }
                },
                "required": ["pattern"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Execute tool"""

    if name == "read_logs":
        file_name = arguments.get("file", "app.log")
        file_path = os.path.join(DATA_DIR, file_name)

        if not os.path.exists(file_path):
            return [TextContent(
                type="text",
                text=f"Error: Log file '{file_name}' not found"
            )]

        with open(file_path, 'r') as f:
            content = f.read()

        return [TextContent(
            type="text",
            text=content
        )]

    elif name == "search_logs":
        pattern = arguments.get("pattern")
        file_name = arguments.get("file", "app.log")
        file_path = os.path.join(DATA_DIR, file_name)

        if not os.path.exists(file_path):
            return [TextContent(
                type="text",
                text=f"Error: Log file '{file_name}' not found"
            )]

        with open(file_path, 'r') as f:
            lines = f.readlines()

        matches = [line.strip() for line in lines if pattern.lower() in line.lower()]

        if matches:
            result = f"Found {len(matches)} matches for '{pattern}':\n\n"
            result += "\n".join(matches[:50])  # Limit to 50 matches
            if len(matches) > 50:
                result += f"\n\n... and {len(matches) - 50} more matches"
        else:
            result = f"No matches found for '{pattern}'"

        return [TextContent(
            type="text",
            text=result
        )]

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
