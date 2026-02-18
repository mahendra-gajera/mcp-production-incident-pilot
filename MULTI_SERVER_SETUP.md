# Multi-Server MCP Setup Guide

## What We Built

You now have **3 custom MCP servers** + **1 MCP client** that connects to all of them!

---

## Architecture

```
┌─────────────────────────────┐
│  mcp_analyze_multi.py       │  ← YOUR MCP CLIENT
│  (Connects to 3 servers)    │
└────────┬────────┬────────┬──┘
         │        │        │
         ▼        ▼        ▼
    ┌────────┐┌────────┐┌─────────┐
    │ Logs   ││  Git   ││ Datadog │  ← 3 CUSTOM MCP SERVERS
    │ Server ││ Server ││ Server  │
    └────────┘└────────┘└─────────┘
         │        │        │
         ▼        ▼        ▼
    app.log   commits   metrics
```

---

## Project Structure

```
mcp-production-incident-pilot/
├── mcp_analyze_multi.py          # Multi-server MCP client
└── mcp-servers/                  # Custom MCP servers
    ├── logs-server/
    │   ├── server.py             # Logs MCP server
    │   └── data/
    │       └── app.log
    ├── git-server/
    │   ├── server.py             # Git MCP server
    │   └── data/
    │       └── recent_commits.json
    └── datadog-server/
        ├── server.py             # Datadog MCP server
        └── data/
            └── metrics.json
```

---

## The 3 MCP Servers

### 1. Logs Server
**File**: `mcp-servers/logs-server/server.py`

**Tools provided:**
- `read_logs(file)` - Read log files
- `search_logs(pattern, file)` - Search for patterns

**Data**: `data/app.log`

**Example tool call:**
```python
result = await logs_session.call_tool("search_logs", {
    "pattern": "500",
    "file": "app.log"
})
```

### 2. Git Server
**File**: `mcp-servers/git-server/server.py`

**Tools provided:**
- `get_recent_commits(limit)` - Get commit history
- `get_deployments()` - Get deployment info
- `search_commits(query)` - Search in commits

**Data**: `data/recent_commits.json`

**Example tool call:**
```python
result = await git_session.call_tool("get_deployments", {})
```

### 3. Datadog Server
**File**: `mcp-servers/datadog-server/server.py`

**Tools provided:**
- `get_metrics(metric_type)` - Get system metrics
- `get_anomalies(threshold)` - Detect spikes
- `get_error_rates()` - Get error rates

**Data**: `data/metrics.json`

**Example tool call:**
```python
result = await datadog_session.call_tool("get_metrics", {
    "metric_type": "all"
})
```

---

## How It Works

### Step 1: Start 3 MCP Servers
```python
# Python starts 3 separate server processes
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
```

### Step 2: Connect to All Servers
```python
# Client connects to all 3 via stdio
async with stdio_client(logs_server_params) as (logs_read, logs_write), \
           stdio_client(git_server_params) as (git_read, git_write), \
           stdio_client(datadog_server_params) as (datadog_read, datadog_write):

    async with ClientSession(logs_read, logs_write) as logs_session, \
               ClientSession(git_read, git_write) as git_session, \
               ClientSession(datadog_read, datadog_write) as datadog_session:

        # Initialize all sessions
        await logs_session.initialize()
        await git_session.initialize()
        await datadog_session.initialize()
```

### Step 3: Collect Tools from All Servers
```python
# Get tools from each server
logs_tools = await logs_session.list_tools()      # read_logs, search_logs
git_tools = await git_session.list_tools()        # get_commits, get_deployments, search_commits
datadog_tools = await datadog_session.list_tools() # get_metrics, get_anomalies, get_error_rates

# Combine all tools
all_tools = []
for tool in logs_tools.tools:
    all_tools.append({
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.inputSchema
        }
    })
# ... same for git and datadog tools
```

### Step 4: Send All Tools to Ollama
```python
# Ollama now has access to tools from all 3 servers
response = call_ollama(messages, tools=all_tools)
```

### Step 5: Route Tool Calls to Correct Server
```python
# Build mapping: tool name → session
tool_to_session = {
    "read_logs": ("logs", logs_session),
    "search_logs": ("logs", logs_session),
    "get_recent_commits": ("git", git_session),
    "get_deployments": ("git", git_session),
    "search_commits": ("git", git_session),
    "get_metrics": ("datadog", datadog_session),
    "get_anomalies": ("datadog", datadog_session),
    "get_error_rates": ("datadog", datadog_session)
}

# When Ollama calls a tool:
tool_name = "get_metrics"
server_type, session = tool_to_session[tool_name]
result = await session.call_tool(tool_name, arguments)
```

---

## Running the Multi-Server Analyzer

```bash
python mcp_analyze_multi.py "500 errors on checkout API"
```

### What You'll See:

```
[1/6] Starting 3 MCP servers...
  - Logs Server
  - Git Server
  - Datadog Server

[2/6] Initializing MCP sessions...

[3/6] Getting tools from all servers...
  - Logs Server: 2 tools
  - Git Server: 3 tools
  - Datadog Server: 3 tools

[4/6] Available tools:
  - read_logs (Logs Server)
  - search_logs (Logs Server)
  - get_recent_commits (Git Server)
  - get_deployments (Git Server)
  - search_commits (Git Server)
  - get_metrics (Datadog Server)
  - get_anomalies (Datadog Server)
  - get_error_rates (Datadog Server)

[5/6] Ollama analyzing with MCP tools...

[Tool #1] get_metrics (DATADOG server)
[Tool #2] search_logs (LOGS server)
[Tool #3] get_anomalies (DATADOG server)
[Tool #4] get_recent_commits (GIT server)

[6/6] ANALYSIS COMPLETE
Total MCP tool calls: 8
  - Logs Server: 3 calls
  - Git Server: 2 calls
  - Datadog Server: 3 calls
```

---

## Benefits

✅ **Separation of Concerns**
- Each server handles one domain (logs, git, metrics)

✅ **Realistic MCP Architecture**
- Multiple specialized servers, not one generic filesystem server

✅ **Easier to Scale**
- Add more servers without changing client much

✅ **Better Organization**
- Data and logic are separated by domain

✅ **Production-Ready**
- Each server can connect to real APIs independently

---

## Key Implementation Details

### Server Implementation Pattern

All 3 servers follow the same pattern:

```python
#!/usr/bin/env python3
import os
import asyncio
from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.stdio import stdio_server

# Data directory (relative to server file)
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# Create server instance
app = Server("server-name")

@app.list_tools()
async def list_tools() -> list[Tool]:
    """Return list of tools this server provides"""
    return [
        Tool(
            name="tool_name",
            description="What this tool does",
            inputSchema={
                "type": "object",
                "properties": {
                    "param1": {"type": "string", ...}
                }
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Execute the requested tool"""
    if name == "tool_name":
        # Implement tool logic
        result = do_something(arguments)
        return [TextContent(type="text", text=result)]

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
```

### Client Tool Routing Logic

The client maintains a mapping between tool names and server sessions:

```python
# Map: tool_name → (server_type, session)
tool_to_session = {}

# Populate map when collecting tools
for tool in logs_tools.tools:
    tool_to_session[tool.name] = ("logs", logs_session)

for tool in git_tools.tools:
    tool_to_session[tool.name] = ("git", git_session)

for tool in datadog_tools.tools:
    tool_to_session[tool.name] = ("datadog", datadog_session)

# Route tool calls
if tool_name in tool_to_session:
    server_type, session = tool_to_session[tool_name]
    result = await session.call_tool(tool_name, tool_args)
```

---

## Next Steps: Making It Production-Ready

### 1. Replace Dummy Data with Real APIs

**Logs Server** → Connect to:
```python
# Example: Elasticsearch
from elasticsearch import Elasticsearch
es = Elasticsearch(['http://localhost:9200'])

@app.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "search_logs":
        pattern = arguments.get("pattern")
        result = es.search(
            index="application-logs",
            body={"query": {"match": {"message": pattern}}}
        )
        return [TextContent(type="text", text=str(result))]
```

**Git Server** → Connect to:
```python
# Example: GitHub API
import requests

@app.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "get_recent_commits":
        response = requests.get(
            "https://api.github.com/repos/owner/repo/commits",
            headers={"Authorization": f"token {GITHUB_TOKEN}"}
        )
        return [TextContent(type="text", text=response.text)]
```

**Datadog Server** → Connect to:
```python
# Example: Datadog API
from datadog import api, initialize

initialize(api_key=DD_API_KEY, app_key=DD_APP_KEY)

@app.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "get_metrics":
        result = api.Metric.query(
            start=now - 3600,
            end=now,
            query='avg:system.cpu.user{*}'
        )
        return [TextContent(type="text", text=str(result))]
```

### 2. Add More Servers

Add a Kubernetes server:

```bash
mkdir -p mcp-servers/kubernetes-server/data
```

Create `mcp-servers/kubernetes-server/server.py`:
```python
app = Server("kubernetes-server")

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(name="get_pods", description="Get pod status"),
        Tool(name="get_deployments", description="Get k8s deployments"),
        Tool(name="get_logs", description="Get container logs")
    ]
```

Update client to include kubernetes server.

### 3. Add Error Handling

```python
try:
    result = await session.call_tool(tool_name, tool_args)
except Exception as e:
    # Log error and send to Ollama
    error_msg = f"Error calling {tool_name}: {str(e)}"
    messages.append({
        "role": "tool",
        "content": error_msg
    })
```

### 4. Add Retry Logic

```python
max_retries = 3
for attempt in range(max_retries):
    try:
        result = await session.call_tool(tool_name, tool_args)
        break
    except Exception as e:
        if attempt == max_retries - 1:
            raise
        await asyncio.sleep(2 ** attempt)  # Exponential backoff
```

### 5. Add Authentication & Security

```python
# Use environment variables for API keys
ELASTICSEARCH_HOST = os.getenv("ELASTICSEARCH_HOST")
ELASTICSEARCH_USER = os.getenv("ELASTICSEARCH_USER")
ELASTICSEARCH_PASS = os.getenv("ELASTICSEARCH_PASS")

es = Elasticsearch(
    [ELASTICSEARCH_HOST],
    http_auth=(ELASTICSEARCH_USER, ELASTICSEARCH_PASS),
    use_ssl=True
)
```

---

## Summary

🎉 **You now have a real multi-server MCP architecture!**

- ✅ 3 custom MCP servers (YOU built these with Python)
- ✅ 1 MCP client (YOU built this with Python)
- ✅ Domain-specific tools (logs, git, metrics)
- ✅ Realistic production-like setup
- ✅ Proper MCP protocol implementation
- ✅ Ready to connect to real APIs

**This is a proper MCP system, not just a demo!**

Each server is independent and can be:
- Updated separately
- Scaled independently
- Connected to different data sources
- Replaced with real API integrations

The client handles:
- Multi-server connection management
- Tool routing
- Session management
- Integration with AI (Ollama)

**This demonstrates the true power of Model Context Protocol!**
