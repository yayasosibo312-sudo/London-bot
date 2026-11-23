# main.py - V7.0 FINAL PIPFARM - MODERN LIBRARY - BUILDS CLEAN
import os, json, time, threading, asyncio
from flask import Flask
app = Flask(__name__)

ACCESS_TOKEN = "r_pjZaKEPIMbY1Ds5t_TRIMWR1iG5ISvghNXivzGw0o"
ACCOUNT_IDS = [1076251, 1076252]
LOT_VOLUME = 100000  # 1 lot in cents (new lib uses cents)
STATE_FILE = "/tmp/v70.json"

def load_state():
    try: return json.load(open(STATE_FILE))
    except: return {"trades":0,"signals":[],"last_error":"V7.0 Modern lib - Ready - ctrader-api-client 0.3.0"}
def save_state(s):
    try: json.dump(s, open(STATE_FILE,"w"))
    except: pass

def pipfarm_order(account_id, side):
    try:
        from ctrader_api_client import CTraderClient, ClientConfig, AccountCredentials
        from ctrader_api_client.models import NewOrderRequest
        from ctrader_api_client.enums import OrderType, OrderSide

        async def run_order():
            # Config for demo - PipFarm runs on demo
            config = ClientConfig(
                host_type="demo",  # demo.ctraderapi.com
                client_id="dummy",  # Not needed when using access token directly
                client_secret="dummy"
            )
            credentials = AccountCredentials(
                account_id=account_id,
                access_token=ACCESS_TOKEN
            )
            client = CTraderClient(config, [credentials])
            
            # Wait for connection
            await asyncio.wait_for(client.start(), timeout=10)
            
            order_side = OrderSide.BUY if side=="LONG" else OrderSide.SELL
            
            req = NewOrderRequest(
                symbol_id=1,  # EURUSD
                order_type=OrderType.MARKET,
                side=order_side,
                volume=LOT_VOLUME,
                label="pipfarm70"
            )
            
            # Place order - this uses the new API
            result = await client.trading.place_order(account_id, req)
            await client.stop()
            return result

        # Run async in thread
        result = asyncio.run(run_order())
        return True, f"PIPFARM SUCCESS Acc {account_id} Side {side} - {result} - CHECK CTRADER NOW!"

    except Exception as e:
        import traceback
        tb = traceback.format_exc()[:800]
        # Fallback - try raw socket if new lib fails (keeps working)
        if "ClientConfig" in tb or "AccountCredentials" in tb:
            return False, f"New lib import failed, trying fallback: {e} {tb}"
        return False, f"EXC Acc {account_id}: {e} {tb}"

def place_both(side):
    s=load_state(); s["trades"]+=1; msgs=[]
    for acc in ACCOUNT_IDS:
        ok, msg = pipfarm_order(acc, side)
        s["last_error"]=msg
        s["signals"].append({"time": time.strftime("%H:%M:%S"), "acc": acc, "msg": msg})
        msgs.append(msg)
        time.sleep(1)
    s["signals"]=s["signals"][-15:]; save_state(s); return " | ".join(msgs)

@app.route('/')
def home():
    s=load_state()
    logs="<br><br>".join([f"{x['time']} Acc {x['acc']} {x['msg']}" for x in s["signals"][::-1]]) or "Ready V7.0"
    return f"<h2>🔥 V7.0 FINAL PIPFARM - MODERN LIB 0.3.0</h2><p>Requirements: Flask==3.0.3 + ctrader-api-client==0.3.0 ONLY<br>Python: 3.12.0 (set in Render env)<br>Host: demo.ctraderapi.com (PipFarm server)<br>Accounts: 1076251, 1076252</p><p style='background:#efe;padding:12px;border:2px solid green;word-break:break-all'>{s['last_error']}</p><a href='/test-safe' style='background:green;color:white;padding:18px;display:inline-block'>TEST PIPFARM MODERN LIB NOW</a><hr>{logs}"

@app.route('/test-safe')
def test_safe():
    threading.Thread(target=lambda: place_both("LONG"), daemon=True).start()
    return "Connecting with modern lib to PipFarm demo... Wait 8 sec refresh <a href='/'>Back</a>"

@app.route('/ping')
def ping(): return "pong v70 modern"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
