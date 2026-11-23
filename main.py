# main.py - V5.7.11 PIPFARM AUTO PROTOCOL
import os, json, time, threading
from flask import Flask, jsonify
app = Flask(__name__)

ACCESS_TOKEN = "r_pjZaKEPIMbY1Ds5t_TRIMWR1iG5ISvghNXivzGw0o"
ACCOUNT_IDS = [1076251, 1076252]
LOT_VOLUME = 400000
STATE_FILE = "/tmp/v5711.json"

def load_state():
    if os.path.exists(STATE_FILE):
        try: return json.load(open(STATE_FILE))
        except: pass
    return {"trades":0,"signals":[],"last_error":"V5.7.11 Auto Protocol - Ready"}
def save_state(s): json.dump(s, open(STATE_FILE,"w"))

def pipfarm_order(account_id, side):
    try:
        from ctrader_open_api import Client, TcpProtocol
        from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOANewOrderReq, ProtoOAAccountAuthReq
        from ctrader_open_api.messages.OpenApiModelMessages_pb2 import ProtoOAOrderType, ProtoOATradeSide
        
        # DEBUG: What protocols exist in this library version?
        avail = [x for x in dir(TcpProtocol) if not x.startswith('_')]
        
        result = {"ok": False, "msg": f"Available protocols: {avail}"}
        
        def on_message(client, message):
            result["msg"] = f"Got Type {message.payloadType} - Available was {avail}"
            result["ok"] = True
        
        def run_client():
            # Try each protocol that exists
            protocols_to_try = []
            # Try named ones if exist
            for name in ['TLS', 'SSL', 'SECURE', 'PLAIN', 'PLAINTEXT', 'TCP', 'V1', 'VERSION1', 'PROTOBUF']:
                if hasattr(TcpProtocol, name):
                    protocols_to_try.append(getattr(TcpProtocol, name))
            # Also try integer values
            protocols_to_try.extend([0,1,2])
            # Unique
            seen=set(); uniq=[]
            for p in protocols_to_try:
                if str(p) not in seen:
                    seen.add(str(p)); uniq.append(p)
            
            last_err=""
            for proto in uniq[:5]:  # Try first 5
                try:
                    client = Client("demo.ctraderapi.com", 5035, proto)
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
                    order_req.label = "pipfarm5711"
                    order_req.relativeStopLoss = 1750
                    order_req.relativeTakeProfit = 3000
                    client.send(order_req)
                    time.sleep(4)
                    client.stopService()
                    result["msg"] = f"SUCCESS with proto {proto} ({type(proto)}) - Available {avail} - Check cTrader Account {account_id} NOW!"
                    result["ok"] = True
                    return
                except Exception as e:
                    last_err = f"proto {proto} failed: {e}"
                    continue
            result["msg"] = f"All protocols failed. Available {avail} Last err: {last_err}"
        
        t = threading.Thread(target=run_client, daemon=True)
        t.start()
        t.join(timeout=20)
        return result["ok"], f"{'SUCCESS' if result['ok'] else 'FAILED'} Acc {account_id} - {result['msg']}"
            
    except Exception as e:
        import traceback
        return False, f"EXC: {e} {traceback.format_exc()[:800]}"

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
    return f"<h2>🔥 V5.7.11 AUTO PROTOCOL</h2><p>Finds correct protocol for your lib</p><p><b>Last:</b><br><div style='background:#efe;padding:12px;border:2px solid green;word-break:break-all'>{s.get('last_error','')}</div></p><hr><a href='/test-safe'><b style='background:green;color:white;padding:16px;font-size:20px'>TEST AUTO PROTOCOL NOW</b></a><hr>{logs}"
@app.route('/test-safe')
def test_safe():
    threading.Thread(target=lambda: place_both("LONG"), daemon=True).start()
    return "Auto protocol test - Wait 10 sec refresh <a href='/'>Back</a>"
@app.route('/ping')
def ping(): return "pong v5711 auto"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
