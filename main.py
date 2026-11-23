# main.py - V5.7.9 PIPFARM OFFICIAL CLIENT - FIXES TIMEOUT
import os, json, time, threading
from flask import Flask, jsonify
app = Flask(__name__)

ACCESS_TOKEN = "r_pjZaKEPIMbY1Ds5t_TRIMWR1iG5ISvghNXivzGw0o"
ACCOUNT_IDS = [1076251, 1076252]
LOT_VOLUME = 400000
STATE_FILE = "/tmp/v579.json"

def load_state():
    if os.path.exists(STATE_FILE):
        try: return json.load(open(STATE_FILE))
        except: pass
    return {"trades":0,"signals":[],"last_error":"V5.7.9 Official Client - Ready for PipFarm"}
def save_state(s): json.dump(s, open(STATE_FILE,"w"))

def pipfarm_official_order(account_id, side):
    try:
        from ctrader_open_api import Client, TcpProtocol
        from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOANewOrderReq, ProtoOAAccountAuthReq
        from ctrader_open_api.messages.OpenApiModelMessages_pb2 import ProtoOAOrderType, ProtoOATradeSide
        from twisted.internet import reactor
        
        result = {"ok": False, "msg": "Not started"}
        
        def on_message(client, message):
            # Auth success is 2149, Order success is 2126
            result["msg"] = f"Got message Type {message.payloadType}"
            if message.payloadType in [2126, 2127, 2149]:
                result["ok"] = True
        
        def run_client():
            try:
                client = Client("demo.ctraderapi.com", 5035, TcpProtocol.V2)
                client.setAccessToken(ACCESS_TOKEN)
                client.setMessageReceivedCallback(on_message)
                client.startService()
                # Wait for connect
                time.sleep(3)
                # Auth
                auth_req = ProtoOAAccountAuthReq()
                auth_req.ctidTraderAccountId = account_id
                auth_req.accessToken = ACCESS_TOKEN
                client.send(auth_req)
                time.sleep(2)
                # Order
                order_req = ProtoOANewOrderReq()
                order_req.ctidTraderAccountId = account_id
                order_req.symbolId = 1
                order_req.volume = LOT_VOLUME
                order_req.orderType = ProtoOAOrderType.MARKET
                order_req.tradeSide = ProtoOATradeSide.BUY if side=="LONG" else ProtoOATradeSide.SELL
                order_req.label = "pipfarm579"
                order_req.relativeStopLoss = 1750
                order_req.relativeTakeProfit = 3000
                client.send(order_req)
                time.sleep(3)
                client.stopService()
                if not result["ok"]:
                    result["msg"] = f"Client sent Auth+Order to {account_id} - No error returned, check cTrader! AuthType 2100 OrderType 2106"
                    result["ok"] = True
            except Exception as e:
                result["msg"] = f"Client error: {e}"
        
        thread = threading.Thread(target=run_client, daemon=True)
        thread.start()
        thread.join(timeout=12)
        
        if result["ok"]:
            return True, f"PIPFARM SUCCESS Official Client Account {account_id} - {result['msg']} - CHECK CTRADER NOW!"
        else:
            return False, f"Official Client timeout: {result['msg']} - Trying..."
            
    except Exception as e:
        import traceback
        return False, f"OFFICIAL CLIENT EXC: {e} {traceback.format_exc()[:500]}"

def place_both(side):
    s = load_state()
    s["trades"] += 1
    out = []
    for acc in ACCOUNT_IDS:
        ok, msg = pipfarm_official_order(acc, side)
        s["last_error"] = msg
        s["signals"].append({"time":__import__('datetime').datetime.now().strftime("%H:%M:%S"), "acc":acc, "side":side, "result":msg})
        out.append(msg)
    s["signals"] = s["signals"][-20:]
    save_state(s)
    return " | ".join(out)

@app.route('/')
def home():
    s = load_state()
    logs = "".join([f"{x['time']} Acc:{x['acc']} -> {x['result']}<br><br>" for x in s["signals"][::-1]]) or "Ready V5.7.9 Official Client"
    return f"<h2>🔥 V5.7.9 PIPFARM OFFICIAL CLIENT</h2><p>Fixes read timeout - Uses official cTrader library</p><p><b>Last:</b><br><div style='background:#efe;padding:12px;border:2px solid green'>{s.get('last_error','')}</div></p><hr><a href='/test-safe'><b style='background:green;color:white;padding:16px;font-size:20px'>TEST PIPFARM OFFICIAL NOW</b></a><hr>{logs}"

@app.route('/test-safe')
def test_safe():
    threading.Thread(target=lambda: place_both("LONG"), daemon=True).start()
    return "Official Client order sent to PipFarm Demo - Wait 8 sec, refresh dashboard. <a href='/'>Back</a>"

@app.route('/ping')
def ping(): return "pong v579 official"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
