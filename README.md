# MCP Production Incident Root Cause Analyzer

An AI-powered incident analysis tool that uses **Model Context Protocol (MCP)** to automatically investigate production incidents by correlating logs, metrics, and git history.

---

## 🎯 What Is This?

When production incidents occur (like "500 errors on checkout API"), this tool:
1. Automatically searches application logs for errors
2. Queries metrics to detect anomalies and spikes
3. Checks recent git deployments and commits
4. Correlates all data to identify the root cause
5. Provides timeline, evidence, and recommendations

**Key Technology**: Uses **MCP (Model Context Protocol)** to connect AI (Ollama) to multiple specialized data sources.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│           MCP Client (mcp_analyze_multi.py)            │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │  1. Starts 3 MCP servers as subprocesses         │  │
│  │  2. Connects to each via stdio                   │  │
│  │  3. Collects tools from all servers (8 tools)    │  │
│  │  4. Sends tools to Ollama AI                     │  │
│  │  5. Routes tool calls to appropriate server      │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
└────────┬──────────────┬──────────────┬─────────────────┘
         │              │              │
         ▼              ▼              ▼
    ┌────────┐     ┌────────┐    ┌──────────┐
    │ LOGS   │     │  GIT   │    │ DATADOG  │
    │ SERVER │     │ SERVER │    │  SERVER  │
    └────────┘     └────────┘    └──────────┘
    (Python)       (Python)       (Python)
         │              │              │
         ▼              ▼              ▼
    ┌────────┐     ┌────────┐    ┌──────────┐
    │ Tools: │     │ Tools: │    │  Tools:  │
    │        │     │        │    │          │
    │ • read │     │ • get  │    │ • get    │
    │  _logs │     │  _recen│    │  _metric │
    │        │     │   t_com│    │   s      │
    │ • sear │     │   mits │    │          │
    │  ch_lo │     │        │    │ • get    │
    │  gs    │     │ • get  │    │  _anomal │
    │        │     │  _deplo│    │   ies    │
    │        │     │   yment│    │          │
    │        │     │   s    │    │ • get    │
    │        │     │        │    │  _error  │
    │        │     │ • sear │    │  _rates  │
    │        │     │  ch_com│    │          │
    │        │     │  mits  │    │          │
    └────────┘     └────────┘    └──────────┘
         │              │              │
         ▼              ▼              ▼
    ┌────────┐     ┌────────┐    ┌──────────┐
    │  Data  │     │  Data  │    │   Data   │
    │ app.log│     │ commits│    │ metrics  │
    │        │     │  .json │    │  .json   │
    └────────┘     └────────┘    └──────────┘
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed architecture diagrams.

---

## 📁 Project Structure

```
mcp-production-incident-pilot/
│
├── mcp_analyze_multi.py          # MCP Client - connects to all 3 servers
│
├── mcp-servers/                  # Custom MCP Servers
│   │
│   ├── logs-server/
│   │   ├── server.py             # Logs MCP Server
│   │   └── data/
│   │       └── app.log           # Application logs
│   │
│   ├── git-server/
│   │   ├── server.py             # Git MCP Server
│   │   └── data/
│   │       └── recent_commits.json
│   │
│   └── datadog-server/
│       ├── server.py             # Datadog MCP Server
│       └── data/
│           └── metrics.json
│
├── .env                          # Ollama API configuration
├── .gitignore                    # Git ignore rules
├── requirements.txt              # Python dependencies
│
├── README.md                     # This file
├── ARCHITECTURE.md               # Detailed architecture docs
└── MULTI_SERVER_SETUP.md         # Multi-server setup guide
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.8+**
- **Ollama Cloud API key** (get one at https://ollama.com/)

### Installation

**Step 1: Install Python dependencies**
```bash
pip install -r requirements.txt
```

**Step 2: Configure environment variables**

Create a `.env` file in the project root:
```bash
OLLAMA_HOST=https://ollama.com
OLLAMA_MODEL=qwen3-coder-next
OLLAMA_API_KEY=your_api_key_here
```

**Step 3: Run the analyzer**
```bash
python mcp_analyze_multi.py "500 errors on checkout API"
```

---

## 📖 Usage

### Basic Usage

```bash
python mcp_analyze_multi.py "500 errors on checkout API"
```

### What You'll See

```
======================================================================
MULTI-SERVER MCP INCIDENT ANALYZER
======================================================================

Configuration:
  Host: https://ollama.com
  Model: qwen3-coder-next
  API Key: be000b51...

Incident: 500 errors on checkout API
======================================================================

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

[Tool #1] search_logs (LOGS server)
  Arguments: {'pattern': '500'}
  Result: Found 5 matches...

[Tool #2] get_metrics (DATADOG server)
  Arguments: {}
  Result: Error rate spike detected...

[Tool #3] get_deployments (GIT server)
  Arguments: {}
  Result: Recent deployment v2.4.1...

======================================================================
[6/6] ANALYSIS COMPLETE
======================================================================

Total MCP tool calls: 8
  - Logs Server: 3 calls
  - Git Server: 2 calls
  - Datadog Server: 3 calls

======================================================================
ROOT CAUSE ANALYSIS
======================================================================

Timeline:
- 14:25: Deployment v2.4.1 deployed
- 14:45: Error rate spike (0.1% → 15.5%)
- 14:46: Connection pool exhausted

Root Cause:
Database connection pool exhaustion after deployment v2.4.1

Evidence:
- Logs: "Connection pool exhausted"
- Metrics: Error spike, response time 180ms → 4500ms
- Git: HOTFIX increased pool 30 → 35 (insufficient)

Recommendations:
1. Increase connection pool to 50+
2. Add connection pool monitoring
3. Implement circuit breakers

======================================================================
```

---

## 🔧 How It Works

### 1. MCP Servers (Custom Built)

Each MCP server is a Python process that provides domain-specific tools:

**Logs Server** (`mcp-servers/logs-server/server.py`)
- **Tools**: `read_logs()`, `search_logs()`
- **Data**: Application log files in `data/app.log`

**Git Server** (`mcp-servers/git-server/server.py`)
- **Tools**: `get_recent_commits()`, `get_deployments()`, `search_commits()`
- **Data**: Git commit history in `data/recent_commits.json`

**Datadog Server** (`mcp-servers/datadog-server/server.py`)
- **Tools**: `get_metrics()`, `get_anomalies()`, `get_error_rates()`
- **Data**: System metrics in `data/metrics.json`

### 2. MCP Client (You Built This)

The client (`mcp_analyze_multi.py`):
1. Starts all 3 MCP servers as subprocesses
2. Connects to each via stdio (standard input/output)
3. Collects available tools from each server
4. Sends incident description + all tools to Ollama AI
5. Routes Ollama's tool calls to the correct server
6. Returns results back to Ollama
7. Displays final root cause analysis

### 3. Ollama AI (Cloud Service)

Ollama AI:
- Receives the incident description
- Decides which MCP tools to call (autonomous)
- Analyzes data from all sources
- Correlates logs, metrics, and git history
- Identifies root cause
- Provides recommendations

---

## 🔍 Example Scenarios

### Scenario 1: Database Issues
```bash
python mcp_analyze_multi.py "database timeout errors"
```
**AI will**:
- Search logs for "timeout"
- Check metrics for database connection pool
- Look for recent database-related commits

### Scenario 2: Memory Leak
```bash
python mcp_analyze_multi.py "out of memory errors"
```
**AI will**:
- Search logs for OOM errors
- Check memory usage metrics
- Find deployments that might have introduced the leak

### Scenario 3: API Performance
```bash
python mcp_analyze_multi.py "slow API response times"
```
**AI will**:
- Check response time metrics
- Look for performance-related commits
- Identify when the slowdown started

---

## 🎯 Key Features

✅ **Multi-Server MCP Architecture**
- 3 specialized MCP servers (not one generic server)
- Domain-specific tools for logs, git, and metrics

✅ **Autonomous AI Analysis**
- AI decides which tools to call
- Correlates data from multiple sources
- No manual investigation needed

✅ **Real MCP Implementation**
- Uses MCP Python SDK (`pip install mcp`)
- Proper stdio communication
- Tool routing and session management

✅ **Production-Ready Design**
- Easy to extend with more servers
- Replace dummy data with real APIs
- Modular and maintainable

---

## 🔄 Extending the System

### Add a New MCP Server

**Step 1: Create the server directory**
```bash
mkdir -p mcp-servers/kubernetes-server/data
```

**Step 2: Create the server** (`mcp-servers/kubernetes-server/server.py`)
```python
#!/usr/bin/env python3
import os
import json
import asyncio
from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.stdio import stdio_server

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
app = Server("kubernetes-server")

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="get_pods",
            description="Get pod status and information",
            inputSchema={
                "type": "object",
                "properties": {
                    "namespace": {
                        "type": "string",
                        "description": "Kubernetes namespace",
                        "default": "default"
                    }
                }
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "get_pods":
        # Implement your logic here
        pods_file = os.path.join(DATA_DIR, "pods.json")
        with open(pods_file, 'r') as f:
            data = json.load(f)
        return [TextContent(type="text", text=str(data))]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
```

**Step 3: Update the client** (`mcp_analyze_multi.py`)

Add to server configuration section:
```python
k8s_server_params = StdioServerParameters(
    command="python",
    args=[os.path.join(SERVERS_DIR, "kubernetes-server", "server.py")]
)
```

Add to connection section:
```python
async with stdio_client(logs_server_params) as (logs_read, logs_write), \
           stdio_client(git_server_params) as (git_read, git_write), \
           stdio_client(datadog_server_params) as (datadog_read, datadog_write), \
           stdio_client(k8s_server_params) as (k8s_read, k8s_write):

    async with ClientSession(logs_read, logs_write) as logs_session, \
               ClientSession(git_read, git_write) as git_session, \
               ClientSession(datadog_read, datadog_write) as datadog_session, \
               ClientSession(k8s_read, k8s_write) as k8s_session:

        # Get tools from new server
        k8s_tools = await k8s_session.list_tools()

        # Add to tool mapping
        for tool in k8s_tools.tools:
            tool_to_session[tool.name] = ("kubernetes", k8s_session)
```

### Connect to Real APIs

Replace dummy data files with real API calls:

**Logs Server** → Connect to:
- Elasticsearch
- Splunk
- CloudWatch Logs
- Datadog Logs API

**Git Server** → Connect to:
- GitHub API (`https://api.github.com`)
- GitLab API
- Bitbucket API

**Datadog Server** → Connect to:
- Datadog API (`https://api.datadoghq.com`)
- Prometheus
- Grafana

**Example: Connecting Logs Server to Elasticsearch**
```python
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

---

## 🐛 Troubleshooting

### Error: "OLLAMA_API_KEY not found"
**Solution**: Create `.env` file with your API key
```bash
OLLAMA_HOST=https://ollama.com
OLLAMA_MODEL=qwen3-coder-next
OLLAMA_API_KEY=your_api_key_here
```

### Error: "Connection timeout"
**Solutions**:
- Check your internet connection
- Verify Ollama API key is valid at https://ollama.com/
- Check firewall settings

### Error: "MCP server failed to start"
**Solutions**:
- Install dependencies: `pip install -r requirements.txt`
- Verify Python version: `python --version` (need 3.8+)
- Check server files exist in `mcp-servers/` directory
- Run server directly to see errors: `python mcp-servers/logs-server/server.py`

### Error: "ModuleNotFoundError: No module named 'mcp'"
**Solution**: Install MCP SDK
```bash
pip install mcp>=1.0.0
```

### Unicode Error in Terminal (Windows)
**Issue**: Unicode characters (→) can't be displayed
**Solution**: This is a known Windows terminal limitation
- The analysis still completes successfully
- You can ignore the warning
- Or use Windows Terminal with UTF-8 support

### No Tool Calls / Analysis Incomplete
**Solutions**:
- Check Ollama API key is valid
- Verify model name is correct (default: `qwen3-coder-next`)
- Try with a simpler incident description
- Check data files exist and have content

---

## 📚 Learn More

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Detailed technical architecture
- **[MULTI_SERVER_SETUP.md](MULTI_SERVER_SETUP.md)** - Multi-server setup guide
- **MCP Protocol**: https://modelcontextprotocol.io/
- **MCP Python SDK**: https://github.com/modelcontextprotocol/python-sdk
- **Ollama Cloud**: https://ollama.com/

---

## 📝 License

MIT License - Feel free to use and modify

---

## 🎉 Summary


- **Multi-Server Architecture**: 3 specialized servers, not 1 generic server
- **Autonomous AI**: Ollama decides which tools to call and when
- **Data Correlation**: Automatically connects logs, metrics, and git history
- **Root Cause Analysis**: Identifies incidents and provides recommendations
- **Production-Ready**: Modular design, easy to extend, ready for real APIs
