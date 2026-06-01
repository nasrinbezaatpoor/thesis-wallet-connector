<div dir="rtl" align="right">

# 🎓 پایان‌نامه: WalletConnector
### اتصال دو کیف پول بلاکچین بدون نیاز به API Key

---

## 📋 شرح پروژه

این پروژه یک **MCP Server** است که به شما امکان می‌دهد تنها با داشتن **آدرس ولت** (کیف پول)،
اطلاعات آن را از بلاکچین بخوانید و بین دو کیف پول ارتباط برقرار کنید.

**مزیت ویژه:** بدون نیاز به API Key از Etherscan یا BscScan — فقط با استفاده از RPC عمومی بلاکچین.

---

## 🎯 قابلیت‌ها

| ابزار | توضیحات |
|-------|---------|
| `wallet_info` | نمایش اطلاعات کامل یک ولت در چندین بلاکچین |
| `wallet_comparison` | مقایسه دو ولت کنار هم |
| `connect_wallets` | **ویژگی اصلی پایان‌نامه** — جستجوی ارتباط بین دو ولت |
| `token_balance` | دریافت موجودی توکن ERC-20 |
| `transaction_info` | جزئیات کامل یک تراکنش |
| `latest_block` | آخرین بلاک یک بلاکچین |
| `is_contract` | تشخیص Contract یا EOA بودن آدرس |

---

## 🌐 بلاکچین‌های پشتیبانی شده

| بلاکچین | واحد | RPC عمومی |
|----------|------|-----------|
| Ethereum | ETH | ethereum-rpc.publicnode.com |
| BSC (BEP-20) | BNB | bsc-dataseed1.binance.org |
| Polygon | MATIC | polygon-rpc.com |

---

## 🚀 اجرا

```bash
# بدون هیچ API Key — فقط اجرا کن!
python3 thesis_wallet_connector.py

# یا با دیتیل بیشتر
python3 thesis_wallet_connector.py --debug
```

---

## 📡 اتصال به عنوان MCP Client

اگر از Codex CLI یا Claude Desktop استفاده می‌کنید:

```json
{
  "mcpServers": {
    "thesis-wallet": {
      "command": "python3",
      "args": ["path/to/thesis_wallet_connector.py"]
    }
  }
}
```

---

## 🧪 نمونه استفاده (تست مستقیم)

```bash
# اطلاعات یک کیف پول
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"clientInfo":{"name":"test","version":"1.0"},"capabilities":{}}}
{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"wallet_info","arguments":{"address":"0xd61aec395613d833aa52bdd18a2cc7ee606837f5"}}}' | python3 thesis_wallet_connector.py 2>/dev/null
```

---

## 📁 ساختار فایل‌ها

```
mcp-server/
├── mcp_server.py                 # هسته MCP سرور (پایه)
├── thesis_wallet_connector.py    # 🎓 پروژه پایان‌نامه (همین فایل)
├── etherscan_mcp_server.py       # (اختیاری) با API Key
└── README_THESIS.md              # این فایل
```

---

## 🔬 معماری فنی

1. **ورودی:** فقط آدرس ولت (مثلاً `0xd61aec...`)
2. **پردازش:** تماس با RPC عمومی بلاکچین از طریق JSON-RPC
3. **خروجی:** اطلاعات موجودی، نوع آدرس، تراکنش‌ها، و ارتباط بین دو ولت

### نحوه کار بدون API Key:

```
Wallet Address → Python MCP Server → Public RPC Node → Blockchain Data → Results
```

---

## 📚 مراجع

- [Ethereum JSON-RPC Specification](https://ethereum.org/en/developers/docs/apis/json-rpc/)
- [BSC Public RPC](https://docs.bnbchain.org/)
- [MCP Protocol](https://modelcontextprotocol.io/)

---

**نویسنده:** برای پروژه پایان‌نامه دانشگاهی  
**تاریخ:** خرداد ۱۴۰۵

</div>
