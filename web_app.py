#!/usr/bin/env python3
"""
Web Interface for Thesis Wallet Connector
یک صفحه وب ساده برای اتصال دو کیف پول بلاکچین
"""

import json
import http.server
import urllib.parse
import sys
import os

# Import the RPC functions from the thesis module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from thesis_wallet_connector import (
    RPC_ENDPOINTS, rpc_call, hex_to_int, wei_to_eth,
    BALANCE_OF_SIG, encode_address_for_call
)

PORT = 8080

HTML = r"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🔗 Wallet Connector — پروژه پایان‌نامه</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@300;500;700;900&display=swap');
  *{margin:0;padding:0;box-sizing:border-box}
  body{
    font-family:'Vazirmatn',sans-serif;
    background:linear-gradient(135deg,#0f0c29,#302b63,#24243e);
    min-height:100vh;color:#e0e0e0;padding:20px
  }
  .container{max-width:900px;margin:0 auto}
  h1{
    text-align:center;font-size:2.2rem;font-weight:900;
    background:linear-gradient(90deg,#00d2ff,#928dab);
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;
    margin:30px 0 10px
  }
  .subtitle{text-align:center;color:#888;margin-bottom:30px;font-weight:300;font-size:0.95rem}
  .card{
    background:rgba(255,255,255,0.05);
    backdrop-filter:blur(10px);
    border:1px solid rgba(255,255,255,0.1);
    border-radius:16px;padding:24px;margin-bottom:20px
  }
  .card h2{font-size:1.2rem;margin-bottom:16px;color:#aaa;font-weight:500}
  .card h2 span{color:#00d2ff}
  .grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
  @media(max-width:600px){.grid{grid-template-columns:1fr}}
  label{display:block;font-size:0.85rem;color:#999;margin-bottom:4px;font-weight:300}
  input,select{
    width:100%;padding:10px 14px;
    background:rgba(255,255,255,0.08);
    border:1px solid rgba(255,255,255,0.15);
    border-radius:10px;color:#fff;font-size:0.95rem;
    font-family:'Vazirmatn',sans-serif;transition:0.2s
  }
  input:focus,select:focus{
    outline:none;border-color:#00d2ff;box-shadow:0 0 0 3px rgba(0,210,255,0.15)
  }
  input::placeholder{color:#555}
  select option{background:#1a1a2e;color:#fff}
  .btn{
    width:100%;padding:12px;border:none;border-radius:10px;
    font-family:'Vazirmatn',sans-serif;font-size:1rem;font-weight:700;
    cursor:pointer;transition:0.3s;margin-top:16px;
    background:linear-gradient(90deg,#00d2ff,#3a7bd5);color:#fff
  }
  .btn:hover{transform:translateY(-2px);box-shadow:0 6px 20px rgba(0,210,255,0.3)}
  .btn:disabled{opacity:0.5;cursor:not-allowed;transform:none}
  .btn-secondary{
    background:rgba(255,255,255,0.1);
    color:#ccc;margin-top:0
  }
  .btn-secondary:hover{background:rgba(255,255,255,0.15)}
  .flex{display:flex;gap:8px}
  .flex .btn{flex:1}
  #output{
    background:rgba(0,0,0,0.4);
    border-radius:12px;padding:20px;
    font-family:'Courier New',monospace;font-size:0.85rem;
    white-space:pre-wrap;line-height:1.7;
    min-height:80px;margin-top:20px;direction:ltr;text-align:left
  }
  #output .persian{direction:rtl;text-align:right;font-family:'Vazirmatn',sans-serif}
  .footer{text-align:center;padding:20px;color:#555;font-size:0.8rem}
  .badge{
    display:inline-block;padding:3px 10px;border-radius:20px;
    font-size:0.75rem;font-weight:700;margin:2px
  }
  .badge-success{background:rgba(0,200,83,0.2);color:#4caf50}
  .badge-error{background:rgba(255,82,82,0.2);color:#ff5252}
  .badge-info{background:rgba(0,210,255,0.2);color:#00d2ff}
  .loading{
    display:inline-block;width:16px;height:16px;
    border:2px solid rgba(255,255,255,0.2);
    border-top-color:#00d2ff;border-radius:50%;
    animation:spin 0.8s linear infinite;margin-left:8px;vertical-align:middle
  }
  @keyframes spin{to{transform:rotate(360deg)}}
</style>
</head>
<body>
<div class="container">
  <h1>🔗 Wallet Connector</h1>
  <p class="subtitle">پروژه پایان‌نامه — اتصال دو کیف پول بلاکچین بدون API Key</p>

  <!-- Wallet Info Card -->
  <div class="card">
    <h2>🏦 <span>اطلاعات یک ولت</span></h2>
    <div class="grid">
      <div>
        <label>آدرس ولت</label>
        <input id="address" placeholder="0x...">
      </div>
      <div>
        <label>بلاکچین</label>
        <select id="chain-info">
          <option value="ethereum">اتریوم (Ethereum)</option>
          <option value="bsc">بایننس اسمارت چین (BSC)</option>
          <option value="polygon">پولیگان (Polygon)</option>
          <option value="arbitrum" selected>آربیتروم وان (Arbitrum One)</option>
        </select>
      </div>
    </div>
    <button class="btn btn-secondary" onclick="getWalletInfo()">📊 نمایش اطلاعات ولت</button>
  </div>

  <!-- Connect Wallets Card -->
  <div class="card">
    <h2>🔗 <span>اتصال دو ولت</span></h2>
    <div class="grid">
      <div>
        <label>ولت اول (A)</label>
        <input id="wallet_a" placeholder="0x...">
      </div>
      <div>
        <label>ولت دوم (B)</label>
        <input id="wallet_b" placeholder="0x...">
      </div>
    </div>
    <div class="grid" style="margin-top:12px">
      <div>
        <label>بلاکچین</label>
        <select id="chain-connect">
          <option value="ethereum">اتریوم (Ethereum)</option>
          <option value="bsc" selected>بایننس اسمارت چین (BSC)</option>
          <option value="polygon">پولیگان (Polygon)</option>
          <option value="arbitrum">آربیتروم وان (Arbitrum One)</option>
        </select>
      </div>
      <div>
        <label>هش تراکنش (اختیاری)</label>
        <input id="tx_hash" placeholder="0x... (برای جستجوی مستقیم)">
      </div>
    </div>
    <div class="flex" style="margin-top:12px">
      <button class="btn btn-secondary" onclick="connectWallets()">🔍 جستجوی اتصال</button>
      <button class="btn btn-secondary" onclick="compareWallets()">📊 مقایسه همزمان</button>
    </div>
  </div>

  <!-- Quick Actions -->
  <div class="card">
    <h2>⚡ <span>اتصال سریع (دمو)</span></h2>
    <p style="color:#888;font-size:0.85rem;margin-bottom:12px">
      با یک کلیک، دو ولت نمونه را روی آربیتروم بررسی کنید
    </p>
    <button class="btn btn-secondary" onclick="demoConnect()">🚀 اجرای دمو</button>
  </div>

  <div id="output">
    <div class="persian">💡 برای شروع، آدرس‌ها را وارد کنید و دکمه مورد نظر را بزنید</div>
  </div>

  <div class="footer">
    🎓 پروژه پایان‌نامه — بدون API Key، فقط با RPC عمومی بلاکچین
  </div>
</div>

<script>
const API = '/api';

function $(id){return document.getElementById(id)}

function setOutput(text, isError=false){
  const out = $('output');
  if(isError){
    out.innerHTML = '<span class="badge badge-error">خطا</span>\n' + text;
  } else {
    out.textContent = text;
  }
}

function showLoading(btn){
  const orig = btn.textContent;
  btn.disabled = true;
  btn.innerHTML = 'در حال پردازش <span class="loading"></span>';
  return orig;
}

function hideLoading(btn, text){
  btn.disabled = false;
  btn.textContent = text;
}

async function callAPI(endpoint, params){
  const resp = await fetch(API + '/' + endpoint + '?' + new URLSearchParams(params));
  return await resp.json();
}

async function getWalletInfo(){
  const btn = event.target;
  const orig = showLoading(btn);
  try {
    const data = await callAPI('wallet_info', {address: $('address').value, chain: $('chain-info').value});
    setOutput(data.result || data.error);
  } catch(e){ setOutput('خطا: ' + e.message, true) }
  hideLoading(btn, orig);
}

async function connectWallets(){
  const btn = event.target;
  const orig = showLoading(btn);
  try {
    const data = await callAPI('connect_wallets', {
      wallet_a: $('wallet_a').value,
      wallet_b: $('wallet_b').value,
      chain: $('chain-connect').value,
      tx_hash: $('tx_hash').value
    });
    setOutput(data.result || data.error);
  } catch(e){ setOutput('خطا: ' + e.message, true) }
  hideLoading(btn, orig);
}

async function compareWallets(){
  const btn = event.target;
  const orig = showLoading(btn);
  try {
    const data = await callAPI('compare', {
      wallet_a: $('wallet_a').value,
      wallet_b: $('wallet_b').value
    });
    setOutput(data.result || data.error);
  } catch(e){ setOutput('خطا: ' + e.message, true) }
  hideLoading(btn, orig);
}

async function demoConnect(){
  // Fill in demo wallets
  $('wallet_a').value = '0xd61aec395613d833aa52bdd18a2cc7ee606837f5';
  $('wallet_b').value = '0xB05271136822c4dD6d1b96A3FAD2D277BC83F9f4';
  $('chain-connect').value = 'arbitrum';
  $('tx_hash').value = '0xc43ef1c10d8ab913e69e0f4b4c426ed652791e4f5eecae474ce4e5a174a010b0';
  
  const btn = event.target;
  const orig = showLoading(btn);
  try {
    const data = await callAPI('connect_wallets', {
      wallet_a: $('wallet_a').value,
      wallet_b: $('wallet_b').value,
      chain: 'arbitrum',
      tx_hash: '0xc43ef1c10d8ab913e69e0f4b4c426ed652791e4f5eecae474ce4e5a174a010b0'
    });
    setOutput(data.result || data.error);
  } catch(e){ setOutput('خطا: ' + e.message, true) }
  hideLoading(btn, orig);
}
</script>
</body>
</html>"""


class APIHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")
        params = urllib.parse.parse_qs(parsed.query)
        
        # Serve HTML page
        if path == "" or path == "/" or path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML.encode("utf-8"))
            return
        
        # API endpoints
        if path.startswith("/api/"):
            self.handle_api(path, params)
            return
        
        self.send_error(404)
    
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else b"{}"
        data = json.loads(body) if body else {}
        
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")
        
        if path.startswith("/api/"):
            # Handle POST with JSON body as params
            self.handle_api(path, data)
            return
        
        self.send_error(404)
    
    def handle_api(self, path, params):
        endpoint = path.replace("/api/", "")
        result = None
        
        try:
            if endpoint == "wallet_info":
                address = params.get("address", [""])[0] if isinstance(params.get("address"), list) else params.get("address", "")
                chain = params.get("chain", ["ethereum"])[0] if isinstance(params.get("chain"), list) else params.get("chain", "ethereum")
                result = self._wallet_info(address, chain)
            
            elif endpoint == "connect_wallets":
                wallet_a = params.get("wallet_a", [""])[0] if isinstance(params.get("wallet_a"), list) else params.get("wallet_a", "")
                wallet_b = params.get("wallet_b", [""])[0] if isinstance(params.get("wallet_b"), list) else params.get("wallet_b", "")
                chain = params.get("chain", ["bsc"])[0] if isinstance(params.get("chain"), list) else params.get("chain", "bsc")
                tx_hash = params.get("tx_hash", [""])[0] if isinstance(params.get("tx_hash"), list) else params.get("tx_hash", "")
                result = self._connect_wallets(wallet_a, wallet_b, chain, tx_hash)
            
            elif endpoint == "compare":
                wallet_a = params.get("wallet_a", [""])[0] if isinstance(params.get("wallet_a"), list) else params.get("wallet_a", "")
                wallet_b = params.get("wallet_b", [""])[0] if isinstance(params.get("wallet_b"), list) else params.get("wallet_b", "")
                result = self._compare(wallet_a, wallet_b)
            
            else:
                result = f"نقطه پایانی نامعتبر: {endpoint}"
            
            self._json_response({"result": result})
        except Exception as e:
            self._json_response({"error": str(e)}, 500)
    
    def _wallet_info(self, address, chain):
        if not address or not address.startswith("0x"):
            return "❌ لطفاً یک آدرس معتبر وارد کنید (0x...)"
        if chain not in RPC_ENDPOINTS:
            return f"❌ بلاکچین نامعتبر: {chain}"
        
        info = RPC_ENDPOINTS[chain]
        lines = [f"🏦 Wallet Info — {info['name']}", "━" * 40]
        lines.append(f"  آدرس: {address}")
        
        # Balance
        resp = rpc_call(chain, "eth_getBalance", [address, "latest"])
        if "result" in resp:
            bal = wei_to_eth(hex_to_int(resp["result"]))
            lines.append(f"  💰 موجودی: {bal:.6f} {info['currency']}")
        else:
            lines.append(f"  ❌ خطا در دریافت موجودی")
        
        # Contract check
        resp = rpc_call(chain, "eth_getCode", [address, "latest"])
        if "result" in resp:
            if resp["result"] != "0x":
                lines.append(f"  📄 نوع: قرارداد هوشمند (Smart Contract)")
            else:
                lines.append(f"  👤 نوع: کیف پول معمولی (EOA)")
        
        # Transaction count
        resp = rpc_call(chain, "eth_getTransactionCount", [address, "latest"])
        if "result" in resp:
            nonce = hex_to_int(resp["result"])
            lines.append(f"  🔄 تعداد تراکنش‌ها: {nonce:,}")
        
        lines.append("")
        lines.append(f"  🔗 {info['explorer']}/address/{address}")
        return "\n".join(lines)
    
    def _connect_wallets(self, a, b, chain, tx_hash=""):
        if not a or not b or not a.startswith("0x") or not b.startswith("0x"):
            return "❌ لطفاً دو آدرس معتبر وارد کنید"
        if chain not in RPC_ENDPOINTS:
            return f"❌ بلاکچین نامعتبر: {chain}"
        
        info = RPC_ENDPOINTS[chain]
        lines = [f"🔗 Analyzing Connection — {info['name']}", "━" * 40]
        lines.append(f"  ولت A: {a}")
        lines.append(f"  ولت B: {b}")
        lines.append("")
        
        # Step 1: Balances
        lines.append("📊 مرحله ۱: موجودی‌ها")
        for wallet, label in [(a, "A"), (b, "B")]:
            resp = rpc_call(chain, "eth_getBalance", [wallet, "latest"])
            if "result" in resp:
                bal = wei_to_eth(hex_to_int(resp["result"]))
                lines.append(f"  ولت {label}: {bal:.6f} {info['currency']}")
        
        # Step 2: Check tx_hash
        if tx_hash:
            lines.append("")
            lines.append("🔍 مرحله ۲: بررسی تراکنش مشخص‌شده")
            tx_resp = rpc_call(chain, "eth_getTransactionByHash", [tx_hash])
            if "result" in tx_resp and tx_resp["result"]:
                tx = tx_resp["result"]
                tx_from = tx.get("from", "").lower()
                tx_to = tx.get("to", "").lower() if tx.get("to") else ""
                val = int(tx.get("value", "0x0"), 16)
                val_eth = wei_to_eth(val)
                
                a_lower = a.lower()
                b_lower = b.lower()
                
                if tx_from in (a_lower, b_lower) and tx_to in (a_lower, b_lower) and tx_from != tx_to:
                    direction = "A→B" if tx_from == a_lower else "B→A"
                    lines.append(f"  ✅ تراکنش یافت شد! {direction}")
                    lines.append(f"  💰 مقدار: {val_eth:.6f} {info['currency']}")
                    lines.append(f"  🔗 {info['explorer']}/tx/{tx_hash}")
                else:
                    lines.append(f"  ❌ این تراکنش مربوط به این دو ولت نیست")
            else:
                lines.append(f"  ❌ تراکنش یافت نشد")
        
        # Step 3: Recent native scan (last 5 blocks)
        lines.append("")
        lines.append("🔄 مرحله ۳: اسکن بلاک‌های اخیر")
        block_resp = rpc_call(chain, "eth_blockNumber", [])
        found_native = 0
        if "result" in block_resp:
            latest_block = hex_to_int(block_resp["result"])
            start_block = max(latest_block - 5, 0)
            for bn in range(latest_block, start_block - 1, -1):
                block = rpc_call(chain, "eth_getBlockByNumber", [hex(bn), True])
                if "result" in block and block["result"]:
                    for tx in block["result"].get("transactions", []):
                        f = tx.get("from", "").lower()
                        t = tx.get("to", "").lower() if tx.get("to") else ""
                        v = int(tx.get("value", "0x0"), 16)
                        if v > 0 and f in (a.lower(), b.lower()) and t in (a.lower(), b.lower()) and f != t:
                            found_native += 1
                if found_native:
                    break
        
        if found_native:
            lines.append(f"  ✅ {found_native} تراکنش بومی در بلاک‌های اخیر یافت شد")
        else:
            lines.append(f"  ℹ️  تراکنش بومی در ۵ بلاک آخر یافت نشد")
        
        # Step 4: ERC-20 Transfer events (last 500K blocks for speed)
        lines.append("")
        lines.append("📋 مرحله ۴: جستجوی تراکنش‌های توکن (ERC-20/BEP-20)")
        transfer_topic = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
        found_erc20 = 0
        
        # Get latest block first
        br = rpc_call(chain, "eth_blockNumber", [])
        latest_for_erc20 = hex_to_int(br["result"]) if "result" in br else 999999999
        from_block_erc20 = max(0, latest_for_erc20 - 500000)
        
        for params_list, direction in [
            ([transfer_topic, f"0x000000000000000000000000{a[2:]}", f"0x000000000000000000000000{b[2:]}"], "A→B"),
            ([transfer_topic, f"0x000000000000000000000000{b[2:]}", f"0x000000000000000000000000{a[2:]}"], "B→A"),
        ]:
            logs = rpc_call(chain, "eth_getLogs", [{"fromBlock": hex(from_block_erc20), "toBlock": "latest", "topics": params_list}])
            if "result" in logs and logs["result"]:
                found_erc20 += len(logs["result"])
                for log in logs["result"][:5]:
                    lines.append(f"    🪙 {direction} | توکن: {log['address'][:10]}...")
                    lines.append(f"       {info["explorer"]}/tx/{log['transactionHash']}")
        
        if found_erc20:
            lines.append(f"  ✅ {found_erc20} تراکنش توکن بین ولت‌ها یافت شد")
        else:
            lines.append(f"  ℹ️  تراکنش توکنی بین ولت‌ها یافت نشد")
        
        total = (1 if tx_hash and True else 0) + found_native + found_erc20
        lines.append("")
        lines.append("━" * 40)
        if total > 0:
            lines.append(f"  🎯 نتیجه: ✅ این دو ولت به هم متصل هستند! ({total} اتصال)")
        else:
            lines.append(f"  🎯 نتیجه: ❌ اتصالی بین این دو ولت یافت نشد")
            lines.append(f"  💡 راهنمایی: بلاکچین دیگری امتحان کنید یا محدوده بلاک را افزایش دهید")
        
        return "\n".join(lines)
    
    def _compare(self, a, b):
        if not a or not b or not a.startswith("0x") or not b.startswith("0x"):
            return "❌ لطفاً دو آدرس معتبر وارد کنید"
        
        lines = ["📊 Wallet Comparison — مقایسه همزمان", "━" * 40]
        lines.append(f"  ولت A: {a}")
        lines.append(f"  ولت B: {b}")
        lines.append("")
        
        for cid, info in RPC_ENDPOINTS.items():
            lines.append(f"── {info['name']} ──")
            for label, addr in [("A", a), ("B", b)]:
                resp = rpc_call(cid, "eth_getBalance", [addr, "latest"])
                if "result" in resp:
                    bal = wei_to_eth(hex_to_int(resp["result"]))
                    lines.append(f"  ولت {label}: {bal:.6f} {info['currency']}")
                else:
                    lines.append(f"  ولت {label}: ❌")
            lines.append("")
        
        return "\n".join(lines)
    
    def _json_response(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
    
    def log_message(self, format, *args):
        pass  # Suppress logs


def main():
    server = http.server.HTTPServer(("0.0.0.0", PORT), APIHandler)
    print(f"🚀 Web Interface started!")
    print(f"📡 Open in browser: http://localhost:{PORT}")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Server stopped")
        server.server_close()


if __name__ == "__main__":
    main()
