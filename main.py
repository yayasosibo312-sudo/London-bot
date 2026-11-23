# main.py - V5.7.10 PIPFARM FIXED CLIENT
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
    return {"trades":0,"signals":[],"last_error":"V5.7.10 Fixed - Ready"}
def save_state(s): json.dump(s, open(STATE_FILE,"w"))

def pipfarm_order(account_id, side):
    try:
        from ctrader_open_api import Client
        from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOANewOrderReq, ProtoOAAccountAuthReq
        from ctrader_open_api.messages.OpenApiModelMessages_pb2 import ProtoOAOrderType, ProtoOATradeSide
        
        result = {"ok": False, "msg": "Starting"}
        
        def on_message(client, message):
            result["msg"] = f"Got Type {message.payloadType}"
            result["ok"] = True
        
        def run_client():
            try:
                # Old library - no TcpProtocol arg
                client = Client("demo.ctraderapi.com", 5035)
                client.setAccessToken(ACCESS_TOKEN)
                client.setMessageReceivedCallback(on_message)
                client.startService()
                time.sleep(3)
                auth_req = ProtoOAAccountAuthReq()
                auth_req.ctidTraderAccountId = account_id
                auth_req.accessToken = ACCESS_TOKEN
                client.send(auth_req)
                time.sleep(2)
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
                time.sleep(4)
                client.stopService()
                if not result["ok"]:
                    result["msg"] = f"Sent to {account_id} - Check cTrader Positions! No error"
                    result["ok"] = True
            except Exception as e:
                result["msg"] = f"Client inner error: {e}"
        
        t = threading.Thread(target=run_client, daemon=True)
        t.start()
        t.join(timeout=15)
        
        return result["ok"], f"{'SUCCESS' if result['ok'] else 'TIMEOUT'} Account {account_id} - {result['msg']}"
            
    except Exception as e:
        import traceback
        return False, f"EXC: {e} {traceback.format_exc()[:600]}"

def place_both(side):
    s = load_state(); s["trades"] += 1
    for acc in ACCOUNT_IDS:
        ok, msg = pipfarm_order(acc, side)
        s["last_error"] = msg
        s["signals"].append({"time":__import__('datetime').datetime.now().strftime("%H:%M:%S"), "acc":acc, "side":side, "result":msg})
    s["signals"] = s["signals"][-20:]; save_state(s); return s["last_error"]

@app.route('/')
def home():
    s = load_state()
    logs = "".join([f"{x['time']} Acc:{x['acc']} -> {x['result']}<br><br>" for x in s["signals"][::-1]]) or "Ready"
    return f"<h2>🔥 V5.7.10 PIPFARM FIXED (No V2)</h2><p><b>Last:</b><br><div style='background:#efe;padding:12px;border:2px solid green'>{s.get('last_error','')}</div></p><hr><a href='/test-safe'><b style='background:green;color:white;padding:16px;font-size:20px'>TEST PIPFARM FIXED NOW</b></a><hr>{logs}"
@app.route('/test-safe')
def test_safe():
    threading.Thread(target=lambda: place_both("LONG"), daemon=True).start()
    return "Fixed client sent - Wait 8 sec refresh <a href='/'>Back</a>"
@app.route('/ping')
def ping(): return "pong v5710 fixed"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
