#!/usr/bin/env python3
"""
Etherscan MCP Server

Provides blockchain data from Ethereum via the Etherscan API as MCP tools.
Requires an Etherscan API key set via the ETHERSCAN_API_KEY environment variable.

Usage:
    export ETHERSCAN_API_KEY="your-api-key"
    python3 etherscan_mcp_server.py

Or pass via --api-key argument:
    python3 etherscan_mcp_server.py --api-key YOUR_KEY
"""

import json
import os
import sys
import logging
import urllib.request
import urllib.error
import urllib.parse
from typing import Any

# Reuse the MCPServer base from the sibling file
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcp_server import MCPServer

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s: %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger("etherscan-mcp")

ETHERSCAN_API_BASE = "https://api.etherscan.io/api"


def etherscan_api_call(params: dict[str, str], api_key: str) -> dict[str, Any]:
    """Make a request to the Etherscan API and return the parsed result."""
    params["apikey"] = api_key
    url = ETHERSCAN_API_BASE + "?" + urllib.parse.urlencode(params)
    log.debug(f"GET {url.replace(api_key, '***')}")

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "mcp-etherscan/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.reason}"}
    except urllib.error.URLError as e:
        return {"error": f"Network error: {e.reason}"}
    except json.JSONDecodeError as e:
        return {"error": f"Invalid JSON response: {e}"}
    except Exception as e:
        return {"error": str(e)}

    if data.get("status") == "0" or data.get("message") == "NOTOK":
        return {"error": data.get("result", data.get("message", "Unknown API error"))}

    return {"result": data.get("result")}


def create_etherscan_server(api_key: str) -> MCPServer:
    """Create an MCPServer with Etherscan blockchain tools."""
    server = MCPServer(name="etherscan-mcp", version="1.0.0")

    # =====================================================================
    # Account Tools
    # =====================================================================

    @server.tool(
        name="eth_balance",
        description="Get the ETH balance of an address (in wei and ether)",
        input_schema={
            "type": "object",
            "properties": {
                "address": {
                    "type": "string",
                    "pattern": "^0x[a-fA-F0-9]{40}$",
                    "description": "Ethereum address (0x-prefixed, 42 chars)",
                },
            },
            "required": ["address"],
        },
    )
    def eth_balance(address: str) -> str:
        resp = etherscan_api_call(
            {"module": "account", "action": "balance", "address": address, "tag": "latest"},
            api_key,
        )
        if "error" in resp:
            return f"Error: {resp['error']}"
        wei = int(resp["result"])
        eth = wei / 1e18
        return f"Address: {address}\nBalance: {wei} wei ({eth:.6f} ETH)"

    @server.tool(
        name="eth_transactions",
        description="Get recent normal (ETH) transactions for an address",
        input_schema={
            "type": "object",
            "properties": {
                "address": {
                    "type": "string",
                    "description": "Ethereum address (0x-prefixed)",
                },
                "start_block": {
                    "type": "integer",
                    "description": "Starting block number (default 0)",
                    "default": 0,
                },
                "end_block": {
                    "type": "integer",
                    "description": "Ending block number (default 99999999)",
                    "default": 99999999,
                },
                "page": {
                    "type": "integer",
                    "description": "Page number (default 1)",
                    "default": 1,
                },
                "offset": {
                    "type": "integer",
                    "description": "Number of records per page (max 100, default 10)",
                    "default": 10,
                },
                "sort": {
                    "type": "string",
                    "enum": ["asc", "desc"],
                    "description": "Sort order (default desc)",
                    "default": "desc",
                },
            },
            "required": ["address"],
        },
    )
    def eth_transactions(address: str, start_block: int = 0,
                         end_block: int = 99999999, page: int = 1,
                         offset: int = 10, sort: str = "desc") -> str:
        resp = etherscan_api_call({
            "module": "account", "action": "txlist",
            "address": address,
            "startblock": str(start_block),
            "endblock": str(end_block),
            "page": str(page),
            "offset": str(offset),
            "sort": sort,
        }, api_key)
        if "error" in resp:
            return f"Error: {resp['error']}"
        txs = resp["result"]
        if not txs:
            return "No transactions found."
        if isinstance(txs, list) and len(txs) > 20:
            txs = txs[:20]

        lines = [f"Found {len(txs)} transaction(s):\n"]
        for tx in txs:
            value_eth = int(tx.get("value", 0)) / 1e18
            lines.append(
                f"  Tx: {tx['hash'][:18]}... | Block: {tx['blockNumber']} | "
                f"From: {tx['from'][:10]}... → To: {tx['to'][:10]}... | "
                f"Value: {value_eth:.6f} ETH"
            )
        return "\n".join(lines)

    @server.tool(
        name="eth_token_balance",
        description="Get ERC-20 token balance for an address",
        input_schema={
            "type": "object",
            "properties": {
                "address": {
                    "type": "string",
                    "description": "Wallet address (0x-prefixed)",
                },
                "contract_address": {
                    "type": "string",
                    "description": "Token contract address (0x-prefixed)",
                },
            },
            "required": ["address", "contract_address"],
        },
    )
    def eth_token_balance(address: str, contract_address: str) -> str:
        resp = etherscan_api_call({
            "module": "account", "action": "tokenbalance",
            "contractaddress": contract_address,
            "address": address,
            "tag": "latest",
        }, api_key)
        if "error" in resp:
            return f"Error: {resp['error']}"
        balance = resp["result"]
        return (
            f"Token Contract: {contract_address}\n"
            f"Wallet: {address}\n"
            f"Balance (raw): {balance}"
        )

    @server.tool(
        name="eth_internal_transactions",
        description="Get internal transactions for an address",
        input_schema={
            "type": "object",
            "properties": {
                "address": {
                    "type": "string",
                    "description": "Ethereum address (0x-prefixed)",
                },
                "start_block": {
                    "type": "integer",
                    "description": "Starting block number (default 0)",
                    "default": 0,
                },
                "end_block": {
                    "type": "integer",
                    "description": "Ending block number (default 99999999)",
                    "default": 99999999,
                },
            },
            "required": ["address"],
        },
    )
    def eth_internal_transactions(address: str, start_block: int = 0,
                                  end_block: int = 99999999) -> str:
        resp = etherscan_api_call({
            "module": "account", "action": "txlistinternal",
            "address": address,
            "startblock": str(start_block),
            "endblock": str(end_block),
            "sort": "desc",
        }, api_key)
        if "error" in resp:
            return f"Error: {resp['error']}"
        txs = resp["result"]
        if not txs:
            return "No internal transactions found."
        if isinstance(txs, list) and len(txs) > 20:
            txs = txs[:20]

        lines = [f"Found {len(txs)} internal transaction(s):\n"]
        for tx in txs:
            value_eth = int(tx.get("value", 0)) / 1e18
            lines.append(
                f"  Tx: {tx['hash'][:18]}... | Block: {tx['blockNumber']} | "
                f"From: {tx['from'][:10]}... → To: {tx['to'][:10]}... | "
                f"Value: {value_eth:.6f} ETH"
            )
        return "\n".join(lines)

    @server.tool(
        name="eth_historical_balance",
        description="Get ETH balance for an address at a specific block number",
        input_schema={
            "type": "object",
            "properties": {
                "address": {
                    "type": "string",
                    "description": "Ethereum address (0x-prefixed)",
                },
                "block": {
                    "type": "integer",
                    "description": "Block number to query balance at",
                },
            },
            "required": ["address", "block"],
        },
    )
    def eth_historical_balance(address: str, block: int) -> str:
        resp = etherscan_api_call({
            "module": "account", "action": "balancehistory",
            "address": address,
            "blockno": str(block),
        }, api_key)
        if "error" in resp:
            return f"Error: {resp['error']}"
        wei = int(resp["result"])
        eth = wei / 1e18
        return f"Address: {address} @ Block {block}\nBalance: {wei} wei ({eth:.6f} ETH)"

    # =====================================================================
    # Contract Tools
    # =====================================================================

    @server.tool(
        name="eth_contract_abi",
        description="Get the ABI for a verified smart contract",
        input_schema={
            "type": "object",
            "properties": {
                "address": {
                    "type": "string",
                    "description": "Contract address (0x-prefixed)",
                },
            },
            "required": ["address"],
        },
    )
    def eth_contract_abi(address: str) -> str:
        resp = etherscan_api_call({
            "module": "contract", "action": "getabi",
            "address": address,
        }, api_key)
        if "error" in resp:
            return f"Error: {resp['error']}"
        abi = resp["result"]
        if isinstance(abi, str):
            try:
                parsed = json.loads(abi)
                abi = json.dumps(parsed, indent=2)
            except json.JSONDecodeError:
                pass
        else:
            abi = json.dumps(abi, indent=2)
        return f"Contract ABI ({address}):\n\n{abi}"

    @server.tool(
        name="eth_contract_source",
        description="Get the verified source code of a contract",
        input_schema={
            "type": "object",
            "properties": {
                "address": {
                    "type": "string",
                    "description": "Contract address (0x-prefixed)",
                },
            },
            "required": ["address"],
        },
    )
    def eth_contract_source(address: str) -> str:
        resp = etherscan_api_call({
            "module": "contract", "action": "getsourcecode",
            "address": address,
        }, api_key)
        if "error" in resp:
            return f"Error: {resp['error']}"
        sources = resp["result"]
        if not sources:
            return "No source code found."

        info = sources[0]
        output = []
        output.append(f"Contract Name: {info.get('ContractName', 'N/A')}")
        output.append(f"Compiler: {info.get('CompilerVersion', 'N/A')}")
        output.append(f"Optimization: {info.get('OptimizationUsed', 'N/A')}")
        output.append(f"License: {info.get('LicenseType', 'N/A')}")
        output.append("")

        source_code = info.get("SourceCode", "")
        if source_code:
            # Some contracts have multiple files (JSON-encoded)
            if source_code.startswith("{"):
                try:
                    files = json.loads(source_code)
                    for path, content in files.items():
                        output.append(f"=== {path} ===")
                        output.append(content)
                except json.JSONDecodeError:
                    output.append(source_code)
            else:
                output.append(source_code)
        else:
            output.append("(No source code available)")

        return "\n".join(output)

    # =====================================================================
    # Gas & Block Tools
    # =====================================================================

    @server.tool(
        name="eth_gas_oracle",
        description="Get current gas price estimates from Etherscan's Gas Oracle",
        input_schema={
            "type": "object",
            "properties": {},
        },
    )
    def eth_gas_oracle() -> str:
        resp = etherscan_api_call({
            "module": "gastracker", "action": "gasoracle",
        }, api_key)
        if "error" in resp:
            return f"Error: {resp['error']}"
        g = resp["result"]
        return (
            f"Gas Oracle (Gwei):\n"
            f"  Safe (Slow):  {g.get('SafeGasPrice', '?')} gwei\n"
            f"  Proposed:     {g.get('ProposeGasPrice', '?')} gwei\n"
            f"  Fast:         {g.get('FastGasPrice', '?')} gwei\n"
            f"  Base Fee:     {g.get('suggestBaseFee', '?')} gwei\n"
            f"  Priority Fee: {g.get('gasUsedRatio', '?')}"
        )

    @server.tool(
        name="eth_gas_estimate",
        description="Estimate gas for a transaction (simulation)",
        input_schema={
            "type": "object",
            "properties": {
                "to": {
                    "type": "string",
                    "description": "Destination address (0x-prefixed)",
                },
                "value": {
                    "type": "string",
                    "description": "Value in wei (optional)",
                    "default": "0x0",
                },
                "data": {
                    "type": "string",
                    "description": "Calldata (0x-prefixed hex, optional)",
                    "default": "0x",
                },
            },
            "required": ["to"],
        },
    )
    def eth_gas_estimate(to: str, value: str = "0x0", data: str = "0x") -> str:
        resp = etherscan_api_call({
            "module": "proxy", "action": "eth_estimateGas",
            "to": to, "value": value, "data": data,
        }, api_key)
        if "error" in resp:
            return f"Error: {resp['error']}"
        return f"Estimated gas: {resp['result']}"

    @server.tool(
        name="eth_block_number",
        description="Get the latest block number",
        input_schema={
            "type": "object",
            "properties": {},
        },
    )
    def eth_block_number() -> str:
        resp = etherscan_api_call({
            "module": "proxy", "action": "eth_blockNumber",
        }, api_key)
        if "error" in resp:
            return f"Error: {resp['error']}"
        block_hex = resp["result"]
        block_dec = int(block_hex, 16)
        return f"Latest Block: {block_dec} ({block_hex})"

    @server.tool(
        name="eth_block_info",
        description="Get detailed info about a block by number",
        input_schema={
            "type": "object",
            "properties": {
                "block": {
                    "type": "integer",
                    "description": "Block number",
                },
            },
            "required": ["block"],
        },
    )
    def eth_block_info(block: int) -> str:
        resp = etherscan_api_call({
            "module": "proxy", "action": "eth_getBlockByNumber",
            "tag": hex(block), "boolean": "false",
        }, api_key)
        if "error" in resp:
            return f"Error: {resp['error']}"
        b = resp["result"]
        if not b:
            return f"Block {block} not found."
        ts = int(b.get("timestamp", "0x0"), 16)
        from datetime import datetime, timezone
        dt = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
        tx_count = len(b.get("transactions", []))
        return (
            f"Block #{block}\n"
            f"  Hash:       {b.get('hash', '?')}\n"
            f"  Timestamp:  {dt}\n"
            f"  Tx Count:   {tx_count}\n"
            f"  Gas Used:   {int(b.get('gasUsed', '0x0'), 16)} / {int(b.get('gasLimit', '0x0'), 16)}\n"
            f"  Miner:      {b.get('miner', '?')}\n"
            f"  Difficulty: {int(b.get('difficulty', '0x0'), 16)}"
        )

    # =====================================================================
    # Token / Stats Tools
    # =====================================================================

    @server.tool(
        name="eth_token_supply",
        description="Get total supply of an ERC-20 token",
        input_schema={
            "type": "object",
            "properties": {
                "contract_address": {
                    "type": "string",
                    "description": "Token contract address (0x-prefixed)",
                },
            },
            "required": ["contract_address"],
        },
    )
    def eth_token_supply(contract_address: str) -> str:
        resp = etherscan_api_call({
            "module": "stats", "action": "tokensupply",
            "contractaddress": contract_address,
        }, api_key)
        if "error" in resp:
            return f"Error: {resp['error']}"
        return f"Token ({contract_address}) total supply: {resp['result']}"

    @server.tool(
        name="eth_total_eth_supply",
        description="Get the total supply of ETH",
        input_schema={
            "type": "object",
            "properties": {},
        },
    )
    def eth_total_eth_supply() -> str:
        resp = etherscan_api_call({
            "module": "stats", "action": "ethsupply",
        }, api_key)
        if "error" in resp:
            return f"Error: {resp['error']}"
        wei = int(resp["result"])
        eth = wei / 1e18
        return f"Total ETH Supply: {wei} wei ({eth:,.0f} ETH)"

    # =====================================================================
    # Event Logs
    # =====================================================================

    @server.tool(
        name="eth_event_logs",
        description="Get event logs for a contract address",
        input_schema={
            "type": "object",
            "properties": {
                "address": {
                    "type": "string",
                    "description": "Contract address (0x-prefixed)",
                },
                "from_block": {
                    "type": "integer",
                    "description": "Starting block (default 0)",
                    "default": 0,
                },
                "to_block": {
                    "type": "integer",
                    "description": "Ending block (default 99999999)",
                    "default": 99999999,
                },
                "topic0": {
                    "type": "string",
                    "description": "Optional topic filter (0x-prefixed 32-byte)",
                },
            },
            "required": ["address"],
        },
    )
    def eth_event_logs(address: str, from_block: int = 0,
                       to_block: int = 99999999,
                       topic0: str | None = None) -> str:
        params = {
            "module": "logs", "action": "getLogs",
            "address": address,
            "fromBlock": hex(from_block),
            "toBlock": hex(to_block),
        }
        if topic0:
            params["topic0"] = topic0

        resp = etherscan_api_call(params, api_key)
        if "error" in resp:
            return f"Error: {resp['error']}"
        logs = resp["result"]
        if not logs:
            return "No logs found."
        if isinstance(logs, list) and len(logs) > 20:
            logs = logs[:20]

        lines = [f"Found {len(logs)} log(s):\n"]
        for log_entry in logs:
            topics = ", ".join(log_entry.get("topics", []))[:80]
            data = log_entry.get("data", "")[:40]
            lines.append(
                f"  Block #{log_entry.get('blockNumber', '?')} | "
                f"Tx: {log_entry.get('transactionHash', '?')[:18]}...\n"
                f"    Topics: {topics}\n"
                f"    Data: {data}..."
            )
        return "\n".join(lines)

    return server


# ======================================================================
# Entry point
# ======================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Etherscan MCP Server — blockchain data via MCP tools"
    )
    parser.add_argument("--api-key", help="Etherscan API key (or set ETHERSCAN_API_KEY env var)")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    if args.debug:
        log.setLevel(logging.DEBUG)

    api_key = args.api_key or os.environ.get("ETHERSCAN_API_KEY")
    if not api_key:
        print(
            "Error: Etherscan API key required. "
            "Set ETHERSCAN_API_KEY environment variable or pass --api-key.",
            file=sys.stderr,
        )
        sys.exit(1)

    server = create_etherscan_server(api_key)

    try:
        server.run()
    except KeyboardInterrupt:
        log.info("Server stopped by user")
        sys.exit(0)


if __name__ == "__main__":
    main()
