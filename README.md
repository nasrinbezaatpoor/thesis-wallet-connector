# 🔗 Web3 Connector — Connect to Web3 Without Any API Key

> **Thesis Project** | Connect to Web3 using only public blockchain RPC nodes — no Etherscan, BscScan, or any API key required.

---

## 🧩 The Problem

You have **two wallet addresses** and you want to find out:

- Are they connected? (shared transactions, common transfers)
- What's the balance of each on different blockchains?
- Is one a smart contract and the other an EOA?
- How can I analyze them without signing up for API keys?

Normally you'd need an Etherscan API key (which can take hours to register).  
**This project solves that** — it uses **public RPC nodes** directly. Zero registration, zero API keys.

---

## 🚀 Quick Start

```bash
# No dependencies to install — just run it!
python3 thesis_wallet_connector.py
```

That's it. No `pip install`, no `.env` file, no API key configuration.

---

## 🔧 Available Tools

| Tool | What it does |
|------|-------------|
| `wallet_info` | Check one wallet across Ethereum, BSC, and Polygon |
| `connect_wallets` | 🔍 **Main feature** — analyze connection between two wallets |
| `wallet_comparison` | Compare two wallets side by side |
| `token_balance` | Get ERC-20 token balance for any address |
| `transaction_info` | Get full details of a transaction |
| `latest_block` | Latest block number for a chain |
| `is_contract` | Check if an address is a contract or regular wallet (EOA) |

---

## 🧪 Live Examples

### 1️⃣ Check wallet info

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"wallet_info","arguments":{"address":"0xd61aec395613d833aa52bdd18a2cc7ee606837f5"}}}' | python3 thesis_wallet_connector.py 2>/dev/null
```

**Output:**
```
📊 Wallet Info: 0xd61aec395613d833aa52bdd18a2cc7ee606837f5

  ✅ Ethereum Mainnet: 0.000173 ETH
  ✅ BNB Smart Chain: 0.000000 BNB
  ❌ Polygon: HTTP 401 — Unauthorized
```

### 2️⃣ Connect to Web3 (the main thesis feature)

```bash
echo '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"connect_wallets","arguments":{"wallet_a":"0xd61aec395613d833aa52bdd18a2cc7ee606837f5","wallet_b":"0x54817444b7EE2229A5028d43Fc0FEd3746A82De9","chain":"bsc"}}}' | python3 thesis_wallet_connector.py 2>/dev/null
```

**Output:**
```
🔗 Web3 Connector — Analyzing connections
  Chain:    BNB Smart Chain
  Wallet A: 0xd61aec395613d833aa52bdd18a2cc7ee606837f5
  Wallet B: 0x54817444b7EE2229A5028d43Fc0FEd3746A82De9

  📊 Step 1: Checking Balances...
     Wallet A: 0.000000 BNB
     Wallet B: 0.000000 BNB

  📋 Step 2: Analyzing Address Types...
     Wallet A: EOA (External Owned Account — regular wallet)
     Wallet B: Smart Contract

  🔄 Step 3: Searching for Common Transfers...

  💡 For deeper analysis, check balances on other chains or get ERC-20 token balances.
```

---

## 🌐 Supported Blockchains

| Chain | Currency | Public RPC |
|-------|----------|------------|
| **Ethereum** | ETH | `ethereum-rpc.publicnode.com` |
| **BNB Smart Chain (BSC)** | BNB | `bsc-dataseed1.binance.org` |
| **Polygon** | MATIC | `polygon-rpc.com` |

No API keys needed for any of them.

---

## 🏗️ Architecture (How it works)

```
Your Wallet Address 
  → Python MCP Server 
    → Public RPC Node (JSON-RPC over HTTPS) 
      → Blockchain Data 
        → Beautiful output
```

The server implements the **[Model Context Protocol (MCP)](https://modelcontextprotocol.io)** — a standard way for AI tools and scripts to talk to each other.

---

## 💻 Use with MCP Clients

Add to your **Codex CLI** or **Claude Desktop** config:

```json
{
  "mcpServers": {
    "thesis-wallet": {
      "command": "python3",
      "args": ["/path/to/thesis_wallet_connector.py"]
    }
  }
}
```

---

## 📁 Project Files

```
mcp-server/
├── thesis_wallet_connector.py    🎯 Main thesis project (no API keys)
├── mcp_server.py                 MCP server framework (base engine)
├── etherscan_mcp_server.py       Optional — needs Etherscan API key
├── README.md                     This file
└── README_THESIS.md              Persian documentation (پایان‌نامه)
```

---

## 🎓 Who is this for?

- **University students** working on blockchain thesis projects
- **Developers** who don't want to register for API keys just to test something
- **Researchers** analyzing wallet connections on public chains
- **Anyone** who has two addresses and wants to see if they're related

---

## 🛣️ Roadmap / Future Ideas

- [ ] Add more chains (Arbitrum, Optimism, Avalanche)
- [ ] Historical transaction search between two wallets
- [ ] Token transfer history (ERC-20 / BEP-20)
- [ ] Web dashboard (simple UI)
- [ ] Batch wallet analysis

---

**Made with ❤️ for a university thesis project**  
**Author:** Nasrin Bezaatpoor  
**Date:** Khordad 1405 (June 2026)
