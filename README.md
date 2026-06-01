# MCP Server

A lightweight [Model Context Protocol](https://modelcontextprotocol.io) server implementation in Python.

Communicates via **JSON-RPC 2.0** over **stdin/stdout** — the standard transport for MCP. No external dependencies required (stdlib only).

## Quick Start

```bash
# Run the demo server
python3 mcp_server.py
```

The server listens for JSON-RPC messages on stdin and responds on stdout. Connect it to any MCP-compatible client (Claude Desktop, Codex, etc.).

## Usage

### Direct invocation (for testing)

```bash
# Send a single initialize request
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"clientInfo":{"name":"test-client","version":"0.1.0"},"capabilities":{}}}' | python3 mcp_server.py

# Debug mode (logs to stderr)
python3 mcp_server.py --debug
```

### With an MCP client

Configure the server in your MCP client's settings:

```json
{
  "mcpServers": {
    "my-server": {
      "command": "python3",
      "args": ["/path/to/mcp_server.py"]
    }
  }
}
```

## Included Tools

| Tool | Description |
|------|-------------|
| `calculator` | Basic arithmetic (`add`, `subtract`, `multiply`, `divide`) |
| `echo` | Echoes input text back |
| `current_time` | Returns the current UTC datetime as ISO 8601 |
| `greet` | Generates a personalized greeting |

## Included Resources

| URI | Description |
|-----|-------------|
| `server://info` | JSON metadata about the server |

## Included Prompts

| Name | Description |
|------|-------------|
| `code_review` | Template for asking the model to review code |

## Extending

Add your own tools, resources, and prompts via decorators:

```python
from mcp_server import MCPServer

server = MCPServer(name="my-server", version="1.0.0")

@server.tool(
    name="my_tool",
    description="Does something useful",
    input_schema={
        "type": "object",
        "properties": {
            "input": {"type": "string"},
        },
        "required": ["input"],
    },
)
def my_tool(input: str) -> str:
    return f"Processed: {input}"

server.run()
```

## Protocol Support

- Lifecycle: `initialize`, `notifications/initialized`
- Tools: `tools/list`, `tools/call`
- Resources: `resources/list`, `resources/read`
- Prompts: `prompts/list`, `prompts/get`
- Error handling: Standard JSON-RPC error codes

---

## Etherscan MCP Server

Provides 14 blockchain data tools via the [Etherscan API](https://etherscan.io/apis).

### Setup

```bash
export ETHERSCAN_API_KEY="your-api-key"
python3 etherscan_mcp_server.py
```

Or pass the key as an argument:

```bash
python3 etherscan_mcp_server.py --api-key YOUR_KEY
```

Get a free API key at [etherscan.io/myapikey](https://etherscan.io/myapikey).

### Available Tools

| Tool | Description |
|------|-------------|
| `eth_balance` | ETH balance of an address (wei & ether) |
| `eth_historical_balance` | Balance at a specific block number |
| `eth_transactions` | Recent normal ETH transactions |
| `eth_internal_transactions` | Internal transactions for an address |
| `eth_token_balance` | ERC-20 token balance for a wallet |
| `eth_token_supply` | Total supply of an ERC-20 token |
| `eth_total_eth_supply` | Total supply of ETH |
| `eth_contract_abi` | ABI for a verified contract |
| `eth_contract_source` | Verified source code of a contract |
| `eth_gas_oracle` | Current gas price estimates (Safe/Proposed/Fast) |
| `eth_gas_estimate` | Estimate gas for a transaction |
| `eth_block_number` | Latest block number |
| `eth_block_info` | Detailed info about a specific block |
| `eth_event_logs` | Event logs for a contract address |

### Client Configuration

```json
{
  "mcpServers": {
    "etherscan": {
      "command": "python3",
      "args": ["/path/to/etherscan_mcp_server.py"],
      "env": {
        "ETHERSCAN_API_KEY": "your-api-key"
      }
    }
  }
}
```
