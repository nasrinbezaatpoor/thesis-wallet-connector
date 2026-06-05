#!/usr/bin/env python3
"""
پروژه پایان‌نامه: Web3Connector - پل ارتباطی به Web3
Thesis Project: Web3 Bridge - Connect to blockchain without any API key

این سرور MCP با استفاده از RPC عمومی بلاکچین، بدون نیاز به API Key،
شما را به دنیای Web3 متصل می‌کند و ارتباط بین آدرس‌ها را تحلیل می‌کند.
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
log = logging.getLogger("thesis-web3")

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
    "arbitrum": {
        "name": "Arbitrum One",
        "rpc": "https://arb1.arbitrum.io/rpc",
        "chain_id": 42161,
        "currency": "ETH",
        "explorer": "https://arbiscan.io",
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
            headers={"Content-Type": "application/json", "User-Agent": "thesis-web3/1.0"},
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
    """Create the thesis MCP server with Web3 connection tools."""
    server = MCPServer(name="thesis-web3-connector", version="1.0.0")

    # =====================================================================
    # Tool 1: Get wallet basic info (balance on all chains)
    # =====================================================================

    @server.tool(
        name="wallet_info",
        description="Web3: Get address info across Ethereum, BSC and Polygon",
        input_schema={
            "type": "object",
            "properties": {
                "address": {
                    "type": "string",
                    "description": "Address (0x-prefixed) - any wallet or contract",
                },
            },
            "required": ["address"],
        },
    )
    def wallet_info(address: str) -> str:
        lines = [f"📊 Web3 Info: {address}\n"]
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
                    "description": "Address (0x-prefixed) - any wallet or contract",
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
                    "description": "First address (0x-prefixed)",
                },
                "wallet_b": {
                    "type": "string",
                    "description": "Second address (0x-prefixed)",
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
                "tx_hash": {
                    "type": "string",
                    "description": "Optional: known transaction hash between the two wallets for direct verification",
                    "default": "",
                },
            },
            "required": ["wallet_a", "wallet_b", "chain"],
        },
    )
    def connect_wallets(wallet_a: str, wallet_b: str, chain: str,
                        from_block: int = 0, to_block: str = "latest",
                        tx_hash: str = "") -> str:
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
            f"🔗 Web3 Connector — Analyzing connections",
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"  Chain:    {chain_info['name']}",
            f"  Address A: {wallet_a}",
            f"  Address B: {wallet_b}",
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

        # Method 3: Find common transactions (native & ERC-20)
        lines.append("")
        lines.append("🔄 Step 3: Searching for Common Transfers...")
        
        # ── 3A: Check known transaction hash (fast) ──
        lines.append("     📍 3a) Checking for native coin transfers...")
        native_found = []
        
        # If user provided a tx_hash, verify it
        if tx_hash:
            tx_resp = rpc_call(chain, "eth_getTransactionByHash", [tx_hash])
            if "result" in tx_resp and tx_resp["result"]:
                tx_data = tx_resp["result"]
                tx_from = tx_data.get("from", "").lower()
                tx_to = tx_data.get("to", "").lower() if tx_data.get("to") else ""
                val = int(tx_data.get("value", "0x0"), 16)
                
                if tx_from in (a, b) and tx_to in (a, b) and tx_from != tx_to and val > 0:
                    direction = "A→B" if tx_from == a else "B→A"
                    native_found.append({
                        "tx": tx_hash,
                        "value": val,
                        "direction": direction,
                    })
        
        # ── Also scan last 5 blocks for recent activity ──
        clean_url = chain_info["rpc"]
        block_resp = rpc_call(chain, "eth_blockNumber", [])
        if "result" in block_resp:
            latest_block = hex_to_int(block_resp["result"])
            start_block = max(latest_block - 5, from_block)
            
            for block_num in range(latest_block, start_block - 1, -1):
                block_hex = hex(block_num)
                block_resp = rpc_call(chain, "eth_getBlockByNumber", [block_hex, True])
                if "result" in block_resp and block_resp["result"]:
                    for tx in block_resp["result"].get("transactions", []):
                        tx_from = tx.get("from", "").lower()
                        tx_to = tx.get("to", "").lower() if tx.get("to") else ""
                        val = int(tx.get("value", "0x0"), 16)
                        
                        if val > 0 and tx_from in (a, b) and tx_to in (a, b) and tx_from != tx_to:
                            direction = "A→B" if tx_from == a else "B→A"
                            if not any(c["tx"] == tx["hash"] for c in native_found):
                                native_found.append({
                                    "tx": tx["hash"],
                                    "value": val,
                                    "direction": direction,
                                })
                if native_found:
                    break
        
        if native_found:
            explorer = chain_info["explorer"]
            currency = chain_info["currency"]
            for conn in native_found[:10]:
                val_eth = wei_to_eth(conn["value"])
                lines.append(f"     ✅ {conn['direction']} | {val_eth:.6f} {currency}")
                lines.append(f"        Tx: {explorer}/tx/{conn['tx']}")
        
        # ── 3B: Search for ERC-20 Transfer events ──
        lines.append("     📍 3b) Searching for ERC-20/BEP-20 Transfer events...")
        transfer_topic = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
        
        params_a_from = {
            "fromBlock": hex(from_block),
            "toBlock": to_block_hex,
            "topics": [transfer_topic, "0x000000000000000000000000" + a[2:], "0x000000000000000000000000" + b[2:]],
        }
        params_a_to = {
            "fromBlock": hex(from_block),
            "toBlock": to_block_hex,
            "topics": [transfer_topic, "0x000000000000000000000000" + b[2:], "0x000000000000000000000000" + a[2:]],
        }

        erc20_found = []
        for params, direction in [(params_a_from, "A→B"), (params_a_to, "B→A")]:
            logs_resp = rpc_call(chain, "eth_getLogs", [params])
            if "result" in logs_resp and logs_resp["result"]:
                for log_entry in logs_resp["result"]:
                    erc20_found.append({
                        "tx": log_entry.get("transactionHash", "unknown"),
                        "token": log_entry.get("address", "unknown"),
                        "direction": direction,
                    })

        if erc20_found:
            explorer = chain_info["explorer"]
            for conn in erc20_found[:10]:
                lines.append(f"     ✅ {conn['direction']} | Token: {conn['token'][:10]}...")
                lines.append(f"        Tx: {explorer}/tx/{conn['tx']}")
        
        total = len(native_found) + len(erc20_found)
        if total == 0:
            lines.append("     🔍 No common transactions found in scanned range.")
        
        lines.append("")
        lines.append("📝 Summary of Connection Analysis:")
        lines.append(f"     • Native transfers found: {len(native_found)}")
        lines.append(f"     • ERC-20 transfers found: {len(erc20_found)}")
        lines.append(f"     • Total connections: {total}")
        if total > 0:
            lines.append(f"     ✅ Wallets ARE connected on {chain_info['name']}!")
        else:
            lines.append(f"     ℹ️  No direct connection found on {chain_info['name']}")
            lines.append(f"     💡 Try a different chain or expand block range")

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
                    "description": "First address (0x-prefixed)",
                },
                "wallet_b": {
                    "type": "string",
                    "description": "Second address (0x-prefixed)",
                },
            },
            "required": ["wallet_a", "wallet_b"],
        },
    )
    def wallet_comparison(wallet_a: str, wallet_b: str) -> str:
        lines = ["📊 Wallet Comparison Report"]
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append(f"  Address A: {wallet_a}")
        lines.append(f"  Address B: {wallet_b}")
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
    print("🚀 Thesis Web3 Connector Server Started!", file=sys.stderr)
    print("📘 No API keys required — uses public RPC nodes", file=sys.stderr)
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", file=sys.stderr)
    
    try:
        server.run()
    except KeyboardInterrupt:
        log.info("Server stopped")
        sys.exit(0)
