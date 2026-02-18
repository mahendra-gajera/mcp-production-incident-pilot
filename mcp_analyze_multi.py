#!/usr/bin/env python3
"""
MCP Multi-Server Incident Analyzer
Connects to 3 separate MCP servers: Logs, Git, and Datadog
"""

import os
import sys
import json
import asyncio
import requests
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Ollama configuration
OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'https://ollama.com')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'qwen3-coder-next')
OLLAMA_API_KEY = os.getenv('OLLAMA_API_KEY')

# MCP Servers directory
SERVERS_DIR = os.path.join(os.path.dirname(__file__), 'mcp-servers')


def call_ollama(messages, tools=None):
    """Call Ollama Cloud API with function calling support"""
    api_url = f"{OLLAMA_HOST}/api/chat"

    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False
    }

    if tools:
        payload["tools"] = tools

    headers = {
        "Content-Type": "application/json"
    }

    if OLLAMA_API_KEY:
        headers["Authorization"] = f"Bearer {OLLAMA_API_KEY}"

    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=60)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"\nError calling Ollama: {e}")
        raise


async def analyze_with_multi_mcp(incident_description):
    """Analyze incident using Ollama with 3 MCP servers"""

    print("\n" + "=" * 70)
    print("MULTI-SERVER MCP INCIDENT ANALYZER")
    print("=" * 70)
    print(f"\nIncident: {incident_description}\n")
    print("=" * 70)

    # Configure 3 MCP servers
    logs_server_params = StdioServerParameters(
        command="python",
        args=[os.path.join(SERVERS_DIR, "logs-server", "server.py")]
    )

    git_server_params = StdioServerParameters(
        command="python",
        args=[os.path.join(SERVERS_DIR, "git-server", "server.py")]
    )

    datadog_server_params = StdioServerParameters(
        command="python",
        args=[os.path.join(SERVERS_DIR, "datadog-server", "server.py")]
    )

    print("\n[1/6] Starting 3 MCP servers...")
    print("  - Logs Server")
    print("  - Git Server")
    print("  - Datadog Server")

    # Connect to all 3 servers
    async with stdio_client(logs_server_params) as (logs_read, logs_write), \
               stdio_client(git_server_params) as (git_read, git_write), \
               stdio_client(datadog_server_params) as (datadog_read, datadog_write):

        async with ClientSession(logs_read, logs_write) as logs_session, \
                   ClientSession(git_read, git_write) as git_session, \
                   ClientSession(datadog_read, datadog_write) as datadog_session:

            print("[2/6] Initializing MCP sessions...")

            # Initialize all sessions
            await logs_session.initialize()
            await git_session.initialize()
            await datadog_session.initialize()

            print("[3/6] Getting tools from all servers...")

            # Get tools from all servers
            logs_tools = await logs_session.list_tools()
            git_tools = await git_session.list_tools()
            datadog_tools = await datadog_session.list_tools()

            print(f"  - Logs Server: {len(logs_tools.tools)} tools")
            print(f"  - Git Server: {len(git_tools.tools)} tools")
            print(f"  - Datadog Server: {len(datadog_tools.tools)} tools")

            # Combine all tools for Ollama
            all_tools = []

            # Map tool names to sessions
            tool_to_session = {}

            print("\n[4/6] Available tools:")

            for tool in logs_tools.tools:
                print(f"  - {tool.name} (Logs Server)")
                all_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": f"[Logs Server] {tool.description}",
                        "parameters": tool.inputSchema
                    }
                })
                tool_to_session[tool.name] = ("logs", logs_session)

            for tool in git_tools.tools:
                print(f"  - {tool.name} (Git Server)")
                all_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": f"[Git Server] {tool.description}",
                        "parameters": tool.inputSchema
                    }
                })
                tool_to_session[tool.name] = ("git", git_session)

            for tool in datadog_tools.tools:
                print(f"  - {tool.name} (Datadog Server)")
                all_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": f"[Datadog Server] {tool.description}",
                        "parameters": tool.inputSchema
                    }
                })
                tool_to_session[tool.name] = ("datadog", datadog_session)

            # System message
            system_msg = """You are a production incident analyzer with access to multiple data sources.

You have tools from 3 different servers:
1. Logs Server - Read and search application logs
2. Git Server - Access git history and deployments
3. Datadog Server - Query metrics and detect anomalies

Your task:
1. Use logs tools to find errors and warnings
2. Use datadog tools to check metrics and detect anomalies
3. Use git tools to check recent deployments
4. Correlate all data to find the root cause
5. Provide timeline, evidence, and recommendations

Call the appropriate tools from each server to gather complete information."""

            messages = [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": f"Analyze this production incident: {incident_description}"}
            ]

            print("\n[5/6] Ollama analyzing with MCP tools...\n")
            print("=" * 70)

            # Tool calling loop
            tool_count = 0
            max_iterations = 25
            server_calls = {"logs": 0, "git": 0, "datadog": 0}

            for iteration in range(max_iterations):
                try:
                    # Call Ollama
                    response = call_ollama(messages, all_tools)

                    # Get the message from response
                    assistant_msg = response.get("message", {})

                    # Check if Ollama wants to use tools
                    if assistant_msg.get("tool_calls"):
                        tool_calls = assistant_msg["tool_calls"]

                        # Add assistant message to history
                        messages.append(assistant_msg)

                        # Execute each tool call
                        for tool_call in tool_calls:
                            tool_count += 1
                            function = tool_call.get("function", {})
                            tool_name = function.get("name")
                            tool_args = function.get("arguments", {})

                            # Parse arguments if string
                            if isinstance(tool_args, str):
                                try:
                                    tool_args = json.loads(tool_args)
                                except:
                                    pass

                            # Get the appropriate session
                            if tool_name in tool_to_session:
                                server_type, session = tool_to_session[tool_name]
                                server_calls[server_type] += 1

                                print(f"\n[Tool #{tool_count}] {tool_name} ({server_type.upper()} server)")
                                print(f"  Arguments: {tool_args}")

                                try:
                                    # Call the appropriate MCP server
                                    result = await session.call_tool(tool_name, tool_args)
                                    result_content = str(result.content)

                                    # Show brief result
                                    preview = result_content[:200] + "..." if len(result_content) > 200 else result_content
                                    print(f"  Result: {preview}")

                                    # Add tool result to messages
                                    messages.append({
                                        "role": "tool",
                                        "content": result_content
                                    })

                                except Exception as e:
                                    error_msg = f"Error: {str(e)}"
                                    print(f"  {error_msg}")
                                    messages.append({
                                        "role": "tool",
                                        "content": error_msg
                                    })
                            else:
                                print(f"\n[Tool #{tool_count}] {tool_name} - Unknown tool!")
                                messages.append({
                                    "role": "tool",
                                    "content": f"Error: Unknown tool '{tool_name}'"
                                })

                    else:
                        # No more tool calls, Ollama has finished
                        final_response = assistant_msg.get("content", "")

                        if final_response:
                            print("\n" + "=" * 70)
                            print("[6/6] ANALYSIS COMPLETE")
                            print("=" * 70)
                            print(f"\nTotal MCP tool calls: {tool_count}")
                            print(f"  - Logs Server: {server_calls['logs']} calls")
                            print(f"  - Git Server: {server_calls['git']} calls")
                            print(f"  - Datadog Server: {server_calls['datadog']} calls")
                            print("\n" + "=" * 70)
                            print("ROOT CAUSE ANALYSIS")
                            print("=" * 70)

                            # Handle Unicode encoding
                            try:
                                print(f"\n{final_response}\n")
                            except UnicodeEncodeError:
                                clean_response = final_response.encode('ascii', 'ignore').decode('ascii')
                                print(f"\n{clean_response}\n")

                            print("=" * 70)
                        else:
                            print("\nNo final response from Ollama.")

                        break

                except Exception as e:
                    print(f"\nError in iteration {iteration + 1}: {e}")
                    import traceback
                    traceback.print_exc()
                    break

            if iteration >= max_iterations - 1:
                print(f"\n\nReached maximum iterations ({max_iterations}).")


def main():
    """Main entry point"""

    print("=" * 70)
    print("MULTI-SERVER MCP INCIDENT ANALYZER")
    print("=" * 70)

    # Check API key
    if not OLLAMA_API_KEY:
        print("\nERROR: OLLAMA_API_KEY not found in .env file!")
        sys.exit(1)

    print(f"\nConfiguration:")
    print(f"  Host: {OLLAMA_HOST}")
    print(f"  Model: {OLLAMA_MODEL}")
    print(f"  API Key: {OLLAMA_API_KEY[:20]}...")

    # Get incident description
    if len(sys.argv) > 1:
        incident = " ".join(sys.argv[1:])
    else:
        incident = "500 errors on checkout API starting at 14:45"
        print(f"\nUsing default incident:")
        print(f"  \"{incident}\"")
        print("\nUsage: python mcp_analyze_multi.py \"your incident\"")

    print(f"\nIncident: {incident}")
    print("=" * 70)

    # Run analysis
    try:
        asyncio.run(analyze_with_multi_mcp(incident))
    except KeyboardInterrupt:
        print("\n\nAnalysis interrupted by user.")
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
