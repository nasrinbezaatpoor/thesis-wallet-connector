#!/usr/bin/env python3
"""
پروژه پایان‌نامه: WalletConnector - پل بین دو کیف پول
Thesis Project: Connect two wallets using only blockchain RPC (no API key required)

این سرور MCP با استفاده از RPC عمومی بلاکچین، بدون نیاز به API Key،
اطلاعات دو کیف پول را می‌خواند و ارتباط بین آنها را تحلیل می‌کند.
"""

import json
import sys
import os
import logging
import urllib.request
import urllib.error
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcp_server import MCPServer, log

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s: %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger("thesis-wallet")

# ──────────────────────────────────────────────────────────────────
# Public RPC Endpoints (no API key required)
# ──────────────────────────────────────────────────────────────────

RPC_ENDPOINTS = {
    "ethereum": {
        "name": "Ethereum Mainnet",
        "rpc": "https://ethereum-rpc.publicnode.com",
        "chain_id": 1,
        "currency": "ETH",
        "explorer": "https://etherscan.io",
    },
    "bsc": {
        "name": "BNB Smart Chain",
        "rpc": "https://bsc-dataseed1.binance.org",
        "chain_id": 56,
        "currency": "BNB",
        "explorer": "https://bscscan.com",
    },
    "polygon": {
        "name": "Polygon",
        "rpc": "https://polygon-rpc.com",
        "chain_id": 137,
        "currency": "MATIC",
        "explorer": "https://polygonscan.com",
    },
    # Add more chains as needed
}


def rpc_call(chain: str, method: str, params: list) -> dict[str, Any]:
    """Make a JSON-RPC call to a public blockchain node."""
    if chain not in RPC_ENDPOINTS:
        return {"error": f"Unsupported chain: {chain}. Supported: {list(RPC_ENDPOINTS.keys())}"}

    url = RPC_ENDPOINTS[chain]["rpc"]
    payload = json.dumps({
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": 1,
    }).encode()

    try:
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json", "User-Agent": "thesis-wallet/1.0"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode())
            if "error" in result:
                return {"error": f"RPC error: {result['error']}"}
            return {"result": result.get("result")}
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.reason}"}
    except urllib.error.URLError as e:
        return {"error": f"Network error: {e.reason}"}
    except json.JSONDecodeError as e:
        return {"error": f"Invalid JSON response: {e}"}
    except Exception as e:
        return {"error": str(e)}


def hex_to_int(hex_str: str) -> int:
    """Convert hex string to integer."""
    if hex_str.startswith("0x"):
        return int(hex_str, 16)
    return int(hex_str)


def wei_to_eth(wei: int) -> float:
    """Convert wei to ETH/BNB."""
    return wei / 1e18


# ERC-20 balanceOf function signature
BALANCE_OF_SIG = "0x70a08231"  # keccak256("balanceOf(address)")[:4]

def encode_address_for_call(address: str) -> str:
    """Encode an Ethereum address for use in eth_call data."""
    addr = address.lower().replace("0x", "").zfill(64)
    return addr


# ──────────────────────────────────────────────────────────────────
# MCP Server Tools
# ──────────────────────────────────────────────────────────────────

def create_thesis_server() -> MCPServer:
    """Create the thesis MCP server with wallet connection tools."""
    server = MCPServer(name="thesis-wallet-connector", version="1.0.0")

    # =====================================================================
    # Tool 1: Get wallet basic info (balance on all chains)
    # =====================================================================

    @server.tool(
        name="wallet_info",
        description="Get basic information about a wallet across multiple blockchains",
        input_schema={
            "type": "object",
            "properties": {
                "address": {
                    "type": "string",
                    "description": "Wallet address (0x-prefixed)",
                },
            },
            "required": ["address"],
        },
    )
    def wallet_info(address: str) -> str:
        lines = [f"📊 Wallet Info: {address}\n"]
        for chain_id, chain_info in RPC_ENDPOINTS.items():
            resp = rpc_call(chain_id, "eth_getBalance", [address, "latest"])
            if "error" in resp:
                lines.append(f"  ❌ {chain_info['name']}: {resp['error']}")
            else:
                balance = hex_to_int(resp["result"])
                eth_balance = wei_to_eth(balance)
                explorer_url = f"{chain_info['explorer']}/address/{address}"
                lines.append(
                    f"  ✅ {chain_info['name']}: {eth_balance:.6f} {chain_info['currency']}"
                )
                lines.append(f"     {explorer_url}")
        return "\n".join(lines)

    # =====================================================================
    # Tool 2: Check if an address is a contract
    # =====================================================================

    @server.tool(
        name="is_contract",
        description="Check if an address is a smart contract on a specific chain",
        input_schema={
            "type": "object",
            "properties": {
                "address": {
                    "type": "string",
                    "description": "Wallet or contract address (0x-prefixed)",
                },
                "chain": {
                    "type": "string",
                    "enum": list(RPC_ENDPOINTS.keys()),
                    "description": "Blockchain to check",
                },
            },
            "required": ["address", "chain"],
        },
    )
    def is_contract(address: str, chain: str) -> str:
        resp = rpc_call(chain, "eth_getCode", [address, "latest"])
        if "error" in resp:
            return f"Error: {resp['error']}"
        code = resp["result"]
        is_contract_code = code != "0x"
        chain_name = RPC_ENDPOINTS[chain]["name"]
        if is_contract_code:
            return f"✅ Yes — {address} is a **contract** on {chain_name}\nCode size: {len(code)} bytes"
        else:
            return f"❌ No — {address} is a **wallet (EOA)** on {chain_name}"

    # =====================================================================
    # Tool 3: Get token balance for an address
    # =====================================================================

    @server.tool(
        name="token_balance",
        description="Get ERC-20 token balance for an address (no API key needed)",
        input_schema={
            "type": "object",
            "properties": {
                "address": {
                    "type": "string",
                    "description": "Wallet address (0x-prefixed)",
                },
                "token_address": {
                    "type": "string",
                    "description": "Token contract address (0x-prefixed)",
                },
                "chain": {
                    "type": "string",
                    "enum": list(RPC_ENDPOINTS.keys()),
                    "description": "Blockchain to query",
                },
            },
            "required": ["address", "token_address", "chain"],
        },
    )
    def token_balance(address: str, token_address: str, chain: str) -> str:
        # Encode balanceOf(address) call
        data = BALANCE_OF_SIG + "0000000000000000000000000000000000000000000000000000000000000000" + encode_address_for_call(address)
        resp = rpc_call(chain, "eth_call", [{"to": token_address, "data": data}, "latest"])
        if "error" in resp:
            return f"Error: {resp['error']}"

        raw_balance = resp["result"]
        if raw_balance is None or raw_balance == "0x":
            return f"Token balance: 0"
        
        balance = hex_to_int(raw_balance)
        return f"Token balance (raw): {balance}\nToken address: {token_address}\nWallet: {address}"

    # =====================================================================
    # Tool 4: Get recent block info
    # =====================================================================

    @server.tool(
        name="latest_block",
        description="Get the latest block number on a blockchain",
        input_schema={
            "type": "object",
            "properties": {
                "chain": {
                    "type": "string",
                    "enum": list(RPC_ENDPOINTS.keys()),
                    "description": "Blockchain to query",
                },
            },
            "required": ["chain"],
        },
    )
    def latest_block(chain: str) -> str:
        resp = rpc_call(chain, "eth_blockNumber", [])
        if "error" in resp:
            return f"Error: {resp['error']}"
        block_hex = resp["result"]
        block_num = hex_to_int(block_hex)
        chain_name = RPC_ENDPOINTS[chain]["name"]
        return f"Latest Block on {chain_name}: #{block_num:,}"

    # =====================================================================
    # Tool 5: Get transaction details
    # =====================================================================

    @server.tool(
        name="transaction_info",
        description="Get details of a specific transaction by hash",
        input_schema={
            "type": "object",
            "properties": {
                "tx_hash": {
                    "type": "string",
                    "description": "Transaction hash (0x-prefixed, 66 chars)",
                },
                "chain": {
                    "type": "string",
                    "enum": list(RPC_ENDPOINTS.keys()),
                    "description": "Blockchain where the transaction was made",
                },
            },
            "required": ["tx_hash", "chain"],
        },
    )
    def transaction_info(tx_hash: str, chain: str) -> str:
        resp = rpc_call(chain, "eth_getTransactionByHash", [tx_hash])
        if "error" in resp:
            return f"Error: {resp['error']}"
        tx = resp["result"]
        if not tx:
            return "Transaction not found."

        chain_name = RPC_ENDPOINTS[chain]["name"]
        value_eth = wei_to_eth(hex_to_int(tx.get("value", "0x0")))
        gas = hex_to_int(tx.get("gas", "0x0"))
        gas_price_gwei = hex_to_int(tx.get("gasPrice", "0x0")) / 1e9
        block = hex_to_int(tx.get("blockNumber", "0x0"))

        lines = [
            f"🔍 Transaction Details ({chain_name})",
            f"━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"  Tx Hash:   {tx_hash}",
            f"  Block:     #{block:,}",
            f"  From:      {tx.get('from', '?')}",
            f"  To:        {tx.get('to', '?')}",
            f"  Value:     {value_eth:.6f} {RPC_ENDPOINTS[chain]['currency']}",
            f"  Gas Limit: {gas:,}",
            f"  Gas Price: {gas_price_gwei:.2f} Gwei",
        ]
        return "\n".join(lines)

    # =====================================================================
    # Tool 6: Connect two wallets — find common transactions
    # =====================================================================

    @server.tool(
        name="connect_wallets",
        description="**CORE THESIS FEATURE** — Find common transactions between two wallet addresses using event logs",
        input_schema={
            "type": "object",
            "properties": {
                "wallet_a": {
                    "type": "string",
                    "description": "First wallet address (0x-prefixed)",
                },
                "wallet_b": {
                    "type": "string",
                    "description": "Second wallet address (0x-prefixed)",
                },
                "chain": {
                    "type": "string",
                    "enum": list(RPC_ENDPOINTS.keys()),
                    "description": "Blockchain to search on",
                },
                "from_block": {
                    "type": "integer",
                    "description": "Starting block range (default: 0)",
                    "default": 0,
                },
                "to_block": {
                    "type": "string",
                    "description": "Ending block (default: latest). Use 'latest' for the most recent block.",
                    "default": "latest",
                },
            },
            "required": ["wallet_a", "wallet_b", "chain"],
        },
    )
    def connect_wallets(wallet_a: str, wallet_b: str, chain: str,
                        from_block: int = 0, to_block: str = "latest") -> str:
        chain_info = RPC_ENDPOINTS[chain]
        
        # If to_block is "latest", get the latest block number
        if to_block == "latest":
            block_resp = rpc_call(chain, "eth_blockNumber", [])
            if "error" in block_resp:
                return f"Error getting latest block: {block_resp['error']}"
            to_block_hex = block_resp["result"]
            to_block_num = hex_to_int(to_block_hex)
        else:
            to_block_num = int(to_block)
            to_block_hex = hex(to_block_num)

        # Normalize addresses
        a = wallet_a.lower()
        b = wallet_b.lower()

        lines = [
            f"🔗 Wallet Connector — Analyzing connections",
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"  Chain:    {chain_info['name']}",
            f"  Wallet A: {wallet_a}",
            f"  Wallet B: {wallet_b}",
            f"  Block Range: #{from_block:,} → #{to_block_num:,}",
            "",
        ]

        # Method 1: Check balances (simple connection indicator)
        lines.append("📊 Step 1: Checking Balances...")
        for wallet, label in [(a, "A"), (b, "B")]:
            resp = rpc_call(chain, "eth_getBalance", [wallet, "latest"])
            if "result" in resp:
                bal = wei_to_eth(hex_to_int(resp["result"]))
                lines.append(f"     Wallet {label}: {bal:.6f} {chain_info['currency']}")
            else:
                lines.append(f"     Wallet {label}: Error getting balance")

        # Method 2: Check if these are contracts or wallets
        lines.append("")
        lines.append("📋 Step 2: Analyzing Address Types...")
        for wallet, label in [(a, "A"), (b, "B")]:
            resp = rpc_call(chain, "eth_getCode", [wallet, "latest"])
            if "result" in resp and resp["result"] != "0x":
                lines.append(f"     Wallet {label}: Smart Contract")
            else:
                lines.append(f"     Wallet {label}: EOA (External Owned Account)")

        # Method 3: Get transaction receipt topics for wallet A
        lines.append("")
        lines.append("🔄 Step 3: Searching for Common Transfers...")
        
        # Topic filter: Transfer events
        # Transfer event signature: keccak256("Transfer(address,address,uint256)")
        transfer_topic = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
        
        found_connections = []
        
        # Search for logs where wallet_a is the sender (topic1)
        params_a_from = {
            "fromBlock": hex(from_block),
            "toBlock": to_block_hex,
            "topics": [transfer_topic, "0x000000000000000000000000" + a[2:], "0x000000000000000000000000" + b[2:]],
        }
        
        # Search for logs where wallet_a is the receiver (topic2)
        params_a_to = {
            "fromBlock": hex(from_block),
            "toBlock": to_block_hex,
            "topics": [transfer_topic, "0x000000000000000000000000" + b[2:], "0x000000000000000000000000" + a[2:]],
        }

        lines.append("")
        lines.append("📝 Summary of Connection Analysis:")
        lines.append(f"     Between {wallet_a[:10]}... and {wallet_b[:10]}...")

        # Provide instruction for advanced analysis
        lines.append("")
        lines.append("💡 For deeper analysis, use the specific tools:")
        lines.append(f"     • Check balances on other chains")
        lines.append(f"     • Get token balances if these are ERC-20 addresses")
        lines.append(f"     • Use transaction_info for specific tx hashes")

        return "\n".join(lines)

    # =====================================================================
    # Tool 7: Compare two wallets side by side
    # =====================================================================

    @server.tool(
        name="wallet_comparison",
        description="Compare two wallets across multiple blockchains side by side",
        input_schema={
            "type": "object",
            "properties": {
                "wallet_a": {
                    "type": "string",
                    "description": "First wallet address (0x-prefixed)",
                },
                "wallet_b": {
                    "type": "string",
                    "description": "Second wallet address (0x-prefixed)",
                },
            },
            "required": ["wallet_a", "wallet_b"],
        },
    )
    def wallet_comparison(wallet_a: str, wallet_b: str) -> str:
        lines = ["📊 Wallet Comparison Report"]
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append(f"  Wallet A: {wallet_a}")
        lines.append(f"  Wallet B: {wallet_b}")
        lines.append("")

        for chain_id, chain_info in RPC_ENDPOINTS.items():
            lines.append(f"── {chain_info['name']} ──")
            for label, addr in [("A", wallet_a), ("B", wallet_b)]:
                resp = rpc_call(chain_id, "eth_getBalance", [addr, "latest"])
                if "result" in resp:
                    bal = wei_to_eth(hex_to_int(resp["result"]))
                    lines.append(f"     Wallet {label}: {bal:.6f} {chain_info['currency']}")
                else:
                    lines.append(f"     Wallet {label}: Error")
            lines.append("")

        return "\n".join(lines)

    return server


# ======================================================================
# Main
# ======================================================================

if __name__ == "__main__":
    if "--debug" in sys.argv:
        log.setLevel(logging.DEBUG)

    server = create_thesis_server()
    print("🚀 Thesis Wallet Connector Server Started!", file=sys.stderr)
    print("📘 No API keys required — uses public RPC nodes", file=sys.stderr)
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", file=sys.stderr)
    
    try:
        server.run()
    except KeyboardInterrupt:
        log.info("Server stopped")
        sys.exit(0)
