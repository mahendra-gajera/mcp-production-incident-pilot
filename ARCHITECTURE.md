# Architecture Documentation

## Overview

This document provides detailed architecture diagrams and explanations for the MCP Production Incident Root Cause Analyzer.

---

## System Architecture

### High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│                          USER INPUT                              │
│              "500 errors on checkout API"                        │
│                                                                  │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│                    MCP CLIENT                                    │
│             (mcp_analyze_multi.py)                               │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                                                            │ │
│  │  1. Start 3 MCP Server Subprocesses                       │ │
│  │     • logs-server/server.py                               │ │
│  │     • git-server/server.py                                │ │
│  │     • datadog-server/server.py                            │ │
│  │                                                            │ │
│  │  2. Connect to Each Server via stdio                      │ │
│  │     • Create read/write streams                           │ │
│  │     • Initialize ClientSession for each                   │ │
│  │                                                            │ │
│  │  3. Collect Tools from All Servers                        │ │
│  │     • await logs_session.list_tools()                     │ │
│  │     • await git_session.list_tools()                      │ │
│  │     • await datadog_session.list_tools()                  │ │
│  │                                                            │ │
│  │  4. Create Tool-to-Session Mapping                        │ │
│  │     tool_to_session = {                                   │ │
│  │       "read_logs": (logs_session),                        │ │
│  │       "get_commits": (git_session),                       │ │
│  │       "get_metrics": (datadog_session)                    │ │
│  │     }                                                      │ │
│  │                                                            │ │
│  │  5. Send All Tools to Ollama                              │ │
│  │     call_ollama(messages, tools=all_tools)                │ │
│  │                                                            │ │
│  │  6. Route Tool Calls to Correct Server                    │ │
│  │     session = tool_to_session[tool_name]                  │ │
│  │     result = await session.call_tool(tool_name, args)     │ │
│  │                                                            │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
└───┬──────────────────┬────────────────────┬──────────────────────┘
    │                  │                    │
    │                  │                    │
    ▼                  ▼                    ▼
┌─────────┐      ┌─────────┐        ┌──────────┐
│  LOGS   │      │   GIT   │        │ DATADOG  │
│ SERVER  │      │  SERVER │        │  SERVER  │
└─────────┘      └─────────┘        └──────────┘
    │                  │                    │
    │                  │                    │
    ▼                  ▼                    ▼
┌─────────┐      ┌─────────┐        ┌──────────┐
│  Data:  │      │  Data:  │        │  Data:   │
│         │      │         │        │          │
│ app.log │      │ commits │        │ metrics  │
│         │      │  .json  │        │  .json   │
└─────────┘      └─────────┘        └──────────┘
```

---

## Detailed Component Architecture

### 1. MCP Client Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                  mcp_analyze_multi.py                          │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │                   Main Function                          │ │
│  │                                                          │ │
│  │  1. Load environment variables (.env)                   │ │
│  │     • OLLAMA_HOST                                        │ │
│  │     • OLLAMA_MODEL                                       │ │
│  │     • OLLAMA_API_KEY                                     │ │
│  │                                                          │ │
│  │  2. Get incident description from command line          │ │
│  │     • sys.argv[1] or default                             │ │
│  │                                                          │ │
│  │  3. Call analyze_with_multi_mcp()                       │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │          analyze_with_multi_mcp(incident)                │ │
│  │                                                          │ │
│  │  ┌────────────────────────────────────────────────────┐ │ │
│  │  │  Phase 1: Server Setup                            │ │ │
│  │  │                                                    │ │ │
│  │  │  StdioServerParameters for each server:           │ │ │
│  │  │    • logs-server                                  │ │ │
│  │  │    • git-server                                   │ │ │
│  │  │    • datadog-server                               │ │ │
│  │  └────────────────────────────────────────────────────┘ │ │
│  │                                                          │ │
│  │  ┌────────────────────────────────────────────────────┐ │ │
│  │  │  Phase 2: Connection Management                   │ │ │
│  │  │                                                    │ │ │
│  │  │  async with stdio_client():                       │ │ │
│  │  │    • Start server subprocess                      │ │ │
│  │  │    • Get stdin/stdout streams                     │ │ │
│  │  │    • Wrap in ClientSession                        │ │ │
│  │  └────────────────────────────────────────────────────┘ │ │
│  │                                                          │ │
│  │  ┌────────────────────────────────────────────────────┐ │ │
│  │  │  Phase 3: Tool Collection                         │ │ │
│  │  │                                                    │ │ │
│  │  │  For each session:                                │ │ │
│  │  │    tools = await session.list_tools()            │ │ │
│  │  │                                                    │ │ │
│  │  │  Convert to Ollama format:                        │ │ │
│  │  │    {                                              │ │ │
│  │  │      "type": "function",                          │ │ │
│  │  │      "function": {                                │ │ │
│  │  │        "name": tool.name,                         │ │ │
│  │  │        "description": tool.description,           │ │ │
│  │  │        "parameters": tool.inputSchema             │ │ │
│  │  │      }                                            │ │ │
│  │  │    }                                              │ │ │
│  │  └────────────────────────────────────────────────────┘ │ │
│  │                                                          │ │
│  │  ┌────────────────────────────────────────────────────┐ │ │
│  │  │  Phase 4: AI Analysis Loop                        │ │ │
│  │  │                                                    │ │ │
│  │  │  while not done:                                  │ │ │
│  │  │    1. response = call_ollama(messages, tools)    │ │ │
│  │  │    2. if tool_calls:                              │ │ │
│  │  │         for each tool_call:                       │ │ │
│  │  │           • Get session from tool_to_session map │ │ │
│  │  │           • result = session.call_tool()          │ │ │
│  │  │           • Add result to messages                │ │ │
│  │  │    3. else:                                       │ │ │
│  │  │         • Display final analysis                  │ │ │
│  │  │         • Break                                   │ │ │
│  │  └────────────────────────────────────────────────────┘ │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │               call_ollama(messages, tools)               │ │
│  │                                                          │ │
│  │  • POST to https://ollama.com/api/chat                  │ │
│  │  • Send messages + tools                                 │ │
│  │  • Return response with tool_calls or final content      │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### 2. MCP Server Architecture (Generic)

```
┌────────────────────────────────────────────────────────────────┐
│                    MCP Server Template                         │
│               (logs/git/datadog-server.py)                     │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  Imports                                                 │ │
│  │                                                          │ │
│  │  from mcp.server import Server                          │ │
│  │  from mcp.types import Tool, TextContent                │ │
│  │  from mcp.server.stdio import stdio_server              │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  Server Initialization                                   │ │
│  │                                                          │ │
│  │  app = Server("server-name")                            │ │
│  │  DATA_DIR = "./data"                                     │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  @app.list_tools()                                       │ │
│  │  async def list_tools() -> list[Tool]:                  │ │
│  │                                                          │ │
│  │    return [                                             │ │
│  │      Tool(                                              │ │
│  │        name="tool_name",                                │ │
│  │        description="What this tool does",               │ │
│  │        inputSchema={                                    │ │
│  │          "type": "object",                              │ │
│  │          "properties": {...}                            │ │
│  │        }                                                │ │
│  │      )                                                  │ │
│  │    ]                                                    │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  @app.call_tool()                                        │ │
│  │  async def call_tool(name, arguments):                  │ │
│  │                                                          │ │
│  │    if name == "tool1":                                  │ │
│  │      # Implement tool logic                            │ │
│  │      result = do_something(arguments)                   │ │
│  │                                                          │ │
│  │      return [TextContent(                               │ │
│  │        type="text",                                     │ │
│  │        text=result                                      │ │
│  │      )]                                                 │ │
│  │                                                          │ │
│  │    elif name == "tool2":                                │ │
│  │      # Another tool                                     │ │
│  │      ...                                                │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  async def main():                                       │ │
│  │                                                          │ │
│  │    async with stdio_server() as (read, write):          │ │
│  │      await app.run(                                     │ │
│  │        read,                                            │ │
│  │        write,                                           │ │
│  │        app.create_initialization_options()              │ │
│  │      )                                                  │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
│  if __name__ == "__main__":                                   │
│    asyncio.run(main())                                        │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### 3. Logs Server Detailed Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                    Logs MCP Server                             │
│              (mcp-servers/logs-server/server.py)               │
│                                                                │
│  Server Name: "logs-server"                                   │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  Tools Provided (2 tools)                                │ │
│  │                                                          │ │
│  │  1. read_logs(file)                                     │ │
│  │     • Description: Read application logs from log files │ │
│  │     • Parameters:                                       │ │
│  │       - file: string (required) - Log filename          │ │
│  │     • Returns: Full log file content                    │ │
│  │                                                          │ │
│  │  2. search_logs(pattern, file)                          │ │
│  │     • Description: Search for patterns in logs          │ │
│  │     • Parameters:                                       │ │
│  │       - pattern: string (required) - Search term        │ │
│  │       - file: string (default: "app.log")               │ │
│  │     • Returns: Matching log lines (max 50)              │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  Data Source                                             │ │
│  │                                                          │ │
│  │  • Location: mcp-servers/logs-server/data/               │ │
│  │  • Files:                                                │ │
│  │    - app.log (Application logs with timestamps)          │ │
│  │                                                          │ │
│  │  • Format:                                               │ │
│  │    2026-02-17 14:45:23 ERROR [api] Message              │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  Implementation                                          │ │
│  │                                                          │ │
│  │  read_logs:                                             │ │
│  │    1. Build file path: DATA_DIR + file_name             │ │
│  │    2. Check if exists                                   │ │
│  │    3. Read entire file                                  │ │
│  │    4. Return content as TextContent                     │ │
│  │                                                          │ │
│  │  search_logs:                                           │ │
│  │    1. Build file path                                   │ │
│  │    2. Read all lines                                    │ │
│  │    3. Filter lines containing pattern (case insensitive)│ │
│  │    4. Limit to 50 matches                               │ │
│  │    5. Return formatted results                          │ │
│  └──────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────┘
```

### 4. Git Server Detailed Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                     Git MCP Server                             │
│               (mcp-servers/git-server/server.py)               │
│                                                                │
│  Server Name: "git-server"                                    │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  Tools Provided (3 tools)                                │ │
│  │                                                          │ │
│  │  1. get_recent_commits(limit)                           │ │
│  │     • Description: Get recent git commits and history   │ │
│  │     • Parameters:                                       │ │
│  │       - limit: number (default: 10)                     │ │
│  │     • Returns: Commit hash, author, date, message       │ │
│  │                                                          │ │
│  │  2. get_deployments()                                   │ │
│  │     • Description: Get recent deployment history        │ │
│  │     • Parameters: None                                  │ │
│  │     • Returns: Version, deployed_at, status, commits    │ │
│  │                                                          │ │
│  │  3. search_commits(query)                               │ │
│  │     • Description: Search commits by message or author  │ │
│  │     • Parameters:                                       │ │
│  │       - query: string (required)                        │ │
│  │     • Returns: Matching commits                         │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  Data Source                                             │ │
│  │                                                          │ │
│  │  • Location: mcp-servers/git-server/data/                │ │
│  │  • Files:                                                │ │
│  │    - recent_commits.json                                 │ │
│  │                                                          │ │
│  │  • Structure:                                            │ │
│  │    {                                                     │ │
│  │      "commits": [                                        │ │
│  │        {                                                 │ │
│  │          "hash": "a1b2c3d",                              │ │
│  │          "author": "user@email.com",                     │ │
│  │          "timestamp": "2026-02-17T10:00:00Z",            │ │
│  │          "message": "Commit message",                    │ │
│  │          "files_changed": ["file1.py"],                  │ │
│  │          "deployed_at": "2026-02-17T14:25:00Z"           │ │
│  │        }                                                 │ │
│  │      ],                                                  │ │
│  │      "deployments": [...]                                │ │
│  │    }                                                     │ │
│  └──────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────┘
```

### 5. Datadog Server Detailed Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                  Datadog MCP Server                            │
│            (mcp-servers/datadog-server/server.py)              │
│                                                                │
│  Server Name: "datadog-server"                                │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  Tools Provided (3 tools)                                │ │
│  │                                                          │ │
│  │  1. get_metrics(metric_type, time_range)                │ │
│  │     • Description: Get system metrics                   │ │
│  │     • Parameters:                                       │ │
│  │       - metric_type: all|cpu|memory|errors (default:all)│ │
│  │       - time_range: string (default: "last_hour")       │ │
│  │     • Returns: CPU%, Memory%, Requests, Errors, RT      │ │
│  │                                                          │ │
│  │  2. get_anomalies(threshold)                            │ │
│  │     • Description: Detect anomalies and spikes          │ │
│  │     • Parameters:                                       │ │
│  │       - threshold: number (default: 50) - % change      │ │
│  │     • Returns: List of detected anomalies               │ │
│  │                                                          │ │
│  │  3. get_error_rates()                                   │ │
│  │     • Description: Get error rates over time            │ │
│  │     • Parameters: None                                  │ │
│  │     • Returns: Timestamp + error percentage             │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  Data Source                                             │ │
│  │                                                          │ │
│  │  • Location: mcp-servers/datadog-server/data/            │ │
│  │  • Files:                                                │ │
│  │    - metrics.json                                        │ │
│  │                                                          │ │
│  │  • Structure:                                            │ │
│  │    {                                                     │ │
│  │      "metrics": [                                        │ │
│  │        {                                                 │ │
│  │          "timestamp": "2026-02-17T14:30:00Z",            │ │
│  │          "cpu_usage": 25,                                │ │
│  │          "memory_usage": 45,                             │ │
│  │          "request_rate": 120,                            │ │
│  │          "error_rate": 0.1,                              │ │
│  │          "response_time_ms": 180                         │ │
│  │        }                                                 │ │
│  │      ]                                                   │ │
│  │    }                                                     │ │
│  └──────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagram

### Complete Analysis Flow

```
┌─────────┐
│  START  │
└────┬────┘
     │
     ▼
┌──────────────────────────────────┐
│ User runs:                       │
│ python mcp_analyze_multi.py      │
│ "500 errors on checkout API"     │
└────┬─────────────────────────────┘
     │
     ▼
┌──────────────────────────────────┐
│ Load .env configuration:         │
│ • OLLAMA_HOST                    │
│ • OLLAMA_MODEL                   │
│ • OLLAMA_API_KEY                 │
└────┬─────────────────────────────┘
     │
     ▼
┌──────────────────────────────────┐
│ Start 3 MCP Server Subprocesses: │
│ • python logs-server/server.py   │
│ • python git-server/server.py    │
│ • python datadog-server/server.py│
└────┬─────────────────────────────┘
     │
     ▼
┌──────────────────────────────────┐
│ Connect to each via stdio:       │
│ • Create read/write streams      │
│ • Wrap in ClientSession          │
│ • Initialize sessions            │
└────┬─────────────────────────────┘
     │
     ▼
┌──────────────────────────────────┐
│ Collect tools from all servers:  │
│ • Logs: 2 tools                  │
│ • Git: 3 tools                   │
│ • Datadog: 3 tools               │
│ • Total: 8 tools                 │
└────┬─────────────────────────────┘
     │
     ▼
┌──────────────────────────────────┐
│ Create system message:           │
│ "You are an incident analyzer    │
│  with access to logs, git,       │
│  and metrics tools..."           │
└────┬─────────────────────────────┘
     │
     ▼
┌──────────────────────────────────┐
│ Initial Ollama call:             │
│ • messages: [system, user]       │
│ • tools: all_tools (8 tools)     │
└────┬─────────────────────────────┘
     │
     ▼
┌──────────────────────────────────┐
│ Ollama analyzes and decides:     │
│ "I need to search logs for 500"  │
└────┬─────────────────────────────┘
     │
     ▼
┌──────────────────────────────────┐
│ Tool Call #1:                    │
│ • tool: search_logs              │
│ • args: {pattern: "500"}         │
└────┬─────────────────────────────┘
     │
     ▼
┌──────────────────────────────────┐
│ Client routes to Logs Server:    │
│ result = logs_session.call_tool( │
│   "search_logs",                 │
│   {"pattern": "500"}             │
│ )                                │
└────┬─────────────────────────────┘
     │
     ▼
┌──────────────────────────────────┐
│ Logs Server executes:            │
│ • Opens app.log                  │
│ • Searches for "500"             │
│ • Returns: "Found 5 matches...   │
│   Database timeout errors..."    │
└────┬─────────────────────────────┘
     │
     ▼
┌──────────────────────────────────┐
│ Client adds result to messages:  │
│ messages.append({                │
│   "role": "tool",                │
│   "content": result              │
│ })                               │
└────┬─────────────────────────────┘
     │
     ▼
┌──────────────────────────────────┐
│ Next Ollama call with new data:  │
│ "I see DB errors, check metrics" │
└────┬─────────────────────────────┘
     │
     ▼
┌──────────────────────────────────┐
│ Tool Call #2:                    │
│ • tool: get_metrics              │
│ • args: {}                       │
└────┬─────────────────────────────┘
     │
     ▼
┌──────────────────────────────────┐
│ Client routes to Datadog Server  │
│ (similar to above)               │
└────┬─────────────────────────────┘
     │
     ▼
┌──────────────────────────────────┐
│ ... More tool calls ...          │
│ Tool #3: get_deployments (Git)   │
│ Tool #4: get_anomalies (Datadog) │
│ Tool #5: get_recent_commits(Git) │
│ etc.                             │
└────┬─────────────────────────────┘
     │
     ▼
┌──────────────────────────────────┐
│ Ollama has enough data:          │
│ No more tool_calls in response   │
│ Returns final analysis           │
└────┬─────────────────────────────┘
     │
     ▼
┌──────────────────────────────────┐
│ Display ROOT CAUSE ANALYSIS:     │
│                                  │
│ Timeline:                        │
│ - 14:25: Deployment              │
│ - 14:45: Error spike             │
│ - 14:46: Pool exhausted          │
│                                  │
│ Root Cause:                      │
│ - Connection pool exhaustion     │
│                                  │
│ Evidence:                        │
│ - Logs, Metrics, Git             │
│                                  │
│ Recommendations:                 │
│ - Increase pool size             │
│ - Add monitoring                 │
│ - Circuit breakers               │
└────┬─────────────────────────────┘
     │
     ▼
┌─────────┐
│   END   │
└─────────┘
```

---

## Communication Protocol (MCP stdio)

### stdio Communication Flow

```
┌──────────────┐                    ┌──────────────┐
│              │                    │              │
│  MCP CLIENT  │                    │  MCP SERVER  │
│              │                    │              │
└──────┬───────┘                    └──────┬───────┘
       │                                   │
       │  1. Start subprocess              │
       ├───────────────────────────────────►
       │     python server.py              │
       │                                   │
       │  2. Initialize request            │
       ├───────────────────────────────────►
       │     {"jsonrpc": "2.0",            │
       │      "method": "initialize", ...} │
       │                                   │
       │  3. Initialize response           │
       ◄───────────────────────────────────┤
       │     {"result": {                  │
       │       "protocolVersion": "0.1.0", │
       │       "capabilities": {...}       │
       │     }}                            │
       │                                   │
       │  4. List tools request            │
       ├───────────────────────────────────►
       │     {"method": "tools/list"}      │
       │                                   │
       │  5. Tools list response           │
       ◄───────────────────────────────────┤
       │     {"result": {                  │
       │       "tools": [                  │
       │         {name: "read_logs", ...}  │
       │       ]                           │
       │     }}                            │
       │                                   │
       │  6. Call tool request             │
       ├───────────────────────────────────►
       │     {"method": "tools/call",      │
       │      "params": {                  │
       │        "name": "read_logs",       │
       │        "arguments": {...}         │
       │      }}                           │
       │                                   │
       │  7. Tool result response          │
       ◄───────────────────────────────────┤
       │     {"result": {                  │
       │       "content": [                │
       │         {                         │
       │           "type": "text",         │
       │           "text": "log content"   │
       │         }                         │
       │       ]                           │
       │     }}                            │
       │                                   │
       ▼                                   ▼
```

---

## Tool Routing Logic

```
┌────────────────────────────────────────────────────────────────┐
│                     Tool Routing in Client                     │
│                                                                │
│  1. Build tool_to_session map:                                │
│                                                                │
│     tool_to_session = {                                       │
│       "read_logs":         ("logs", logs_session),            │
│       "search_logs":       ("logs", logs_session),            │
│       "get_recent_commits": ("git", git_session),             │
│       "get_deployments":   ("git", git_session),              │
│       "search_commits":    ("git", git_session),              │
│       "get_metrics":       ("datadog", datadog_session),      │
│       "get_anomalies":     ("datadog", datadog_session),      │
│       "get_error_rates":   ("datadog", datadog_session)       │
│     }                                                          │
│                                                                │
│  2. When Ollama calls a tool:                                 │
│                                                                │
│     tool_name = "search_logs"                                 │
│     tool_args = {"pattern": "500", "file": "app.log"}         │
│                                                                │
│     # Look up which server handles this tool                  │
│     server_type, session = tool_to_session[tool_name]         │
│     # server_type = "logs"                                    │
│     # session = logs_session                                  │
│                                                                │
│     # Route to appropriate server                             │
│     result = await session.call_tool(tool_name, tool_args)    │
│                                                                │
│  3. Track calls per server:                                   │
│                                                                │
│     server_calls = {"logs": 0, "git": 0, "datadog": 0}        │
│     server_calls[server_type] += 1                            │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

---

## Scalability Architecture

### Adding a New Server (Example: Kubernetes)

```
Step 1: Create New Server
┌────────────────────────────────────────┐
│ mcp-servers/kubernetes-server/         │
│   ├── server.py                        │
│   └── data/                            │
│       └── pods.json                    │
└────────────────────────────────────────┘

Step 2: Define Tools
┌────────────────────────────────────────┐
│ @app.list_tools()                      │
│ async def list_tools():                │
│   return [                             │
│     Tool(name="get_pods", ...),        │
│     Tool(name="get_deployments", ...), │
│     Tool(name="get_logs", ...)         │
│   ]                                    │
└────────────────────────────────────────┘

Step 3: Add to Client
┌────────────────────────────────────────┐
│ k8s_server_params = StdioServerParams( │
│   command="python",                    │
│   args=["mcp-servers/k8s/server.py"]   │
│ )                                      │
│                                        │
│ async with stdio_client(k8s_params):   │
│   async with ClientSession() as k8s:   │
│     k8s_tools = await k8s.list_tools() │
│     all_tools.extend(k8s_tools)        │
└────────────────────────────────────────┘

Result: 11 Tools Available
┌────────────────────────────────────────┐
│ • Logs: 2 tools                        │
│ • Git: 3 tools                         │
│ • Datadog: 3 tools                     │
│ • Kubernetes: 3 tools                  │
│ • TOTAL: 11 tools                      │
└────────────────────────────────────────┘
```

---

## Error Handling Flow

```
┌──────────────────┐
│ Tool Call        │
└────┬─────────────┘
     │
     ▼
┌──────────────────────────────┐
│ Try:                         │
│   session.call_tool()        │
└────┬─────────────────────────┘
     │
     ├─────► Success
     │       │
     │       ▼
     │     ┌──────────────────────┐
     │     │ Return result        │
     │     │ Add to messages      │
     │     └──────────────────────┘
     │
     └─────► Exception
             │
             ▼
           ┌──────────────────────┐
           │ Catch error          │
           │ Log error message    │
           └────┬─────────────────┘
                │
                ▼
           ┌──────────────────────┐
           │ Add error to messages│
           │ {                    │
           │   "role": "tool",    │
           │   "content": "Error" │
           │ }                    │
           └────┬─────────────────┘
                │
                ▼
           ┌──────────────────────┐
           │ Ollama sees error    │
           │ May try alternative  │
           │ tools or approach    │
           └──────────────────────┘
```

---

## Deployment Architecture

### Current (Demo): Local Files

```
┌─────────────────────────────────────────┐
│ MCP Servers read from local files:      │
│                                         │
│ Logs Server → data/app.log              │
│ Git Server → data/recent_commits.json   │
│ Datadog Server → data/metrics.json      │
└─────────────────────────────────────────┘
```

### Production: Real APIs

```
┌─────────────────────────────────────────┐
│ MCP Servers call real APIs:              │
│                                         │
│ Logs Server                             │
│   ↓                                     │
│   Elasticsearch / Splunk / CloudWatch   │
│                                         │
│ Git Server                              │
│   ↓                                     │
│   GitHub API / GitLab API               │
│                                         │
│ Datadog Server                          │
│   ↓                                     │
│   Datadog API / Prometheus / Grafana    │
└─────────────────────────────────────────┘
```

---

## Summary

This architecture demonstrates:

1. **Multi-Server MCP Design**: 3 specialized servers, not 1 generic server
2. **Proper MCP Protocol**: stdio communication, tool registration, autonomous calling
3. **Modular Structure**: Easy to add more servers
4. **Production-Ready**: Replace data files with real APIs
5. **AI-Driven Analysis**: Ollama autonomously explores data and correlates findings

**This is a real-world MCP application, not a demo.**
