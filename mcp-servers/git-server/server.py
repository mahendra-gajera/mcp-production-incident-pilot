#!/usr/bin/env python3
"""
MCP Git Server
Provides tools to read git history and deployment information
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
app = Server("git-server")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools"""
    return [
        Tool(
            name="get_recent_commits",
            description="Get recent git commits and deployment history",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "number",
                        "description": "Number of recent commits to retrieve",
                        "default": 10
                    }
                }
            }
        ),
        Tool(
            name="get_deployments",
            description="Get recent deployment history",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="search_commits",
            description="Search commits by message or author",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (searches in commit messages and author)"
                    }
                },
                "required": ["query"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Execute tool"""

    commits_file = os.path.join(DATA_DIR, "recent_commits.json")

    if not os.path.exists(commits_file):
        return [TextContent(
            type="text",
            text="Error: Git data file not found"
        )]

    with open(commits_file, 'r') as f:
        data = json.load(f)

    if name == "get_recent_commits":
        limit = arguments.get("limit", 10)
        commits = data.get("commits", [])[:limit]

        result = f"Recent Commits (showing {len(commits)}):\n\n"
        for commit in commits:
            result += f"Commit: {commit['hash']}\n"
            result += f"Author: {commit['author']}\n"
            result += f"Date: {commit['timestamp']}\n"
            result += f"Message: {commit['message']}\n"
            result += f"Files: {', '.join(commit.get('files_changed', []))}\n"
            if 'deployed_at' in commit:
                result += f"Deployed: {commit['deployed_at']}\n"
            result += "\n"

        return [TextContent(type="text", text=result)]

    elif name == "get_deployments":
        deployments = data.get("deployments", [])

        result = f"Recent Deployments (showing {len(deployments)}):\n\n"
        for deployment in deployments:
            result += f"Version: {deployment['version']}\n"
            result += f"Deployed: {deployment['deployed_at']}\n"
            result += f"Status: {deployment['status']}\n"
            result += f"Commits: {', '.join(deployment['commits'])}\n\n"

        return [TextContent(type="text", text=result)]

    elif name == "search_commits":
        query = arguments.get("query", "").lower()
        commits = data.get("commits", [])

        matches = [
            c for c in commits
            if query in c['message'].lower() or query in c['author'].lower()
        ]

        if matches:
            result = f"Found {len(matches)} commits matching '{query}':\n\n"
            for commit in matches:
                result += f"[{commit['hash']}] {commit['message']}\n"
                result += f"  By: {commit['author']} at {commit['timestamp']}\n\n"
        else:
            result = f"No commits found matching '{query}'"

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
