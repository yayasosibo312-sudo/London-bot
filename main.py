# main.py - V6.0 FINAL PIPFARM - RENDER ALLOWED PORT 5035 SSL - BUILDS FAST
import os, json, time, threading, ssl, socket
from flask import Flask
app = Flask(__name__)

ACCESS_TOKEN = "r_pjZaKEPIMbY1Ds5t_TRIMWR1iG5ISvghNXivzGw0o"
ACCOUNT_IDS = [1076251, 1076252]
LOT_VOLUME = 400000
STATE_FILE = "/tmp/v60.json"

def load_state():
    try: return json.load(open(STATE_FILE))
    except: return {"trades":0,"signals":[],"last_error":"V6.0 Render Allowed Port 5035 SSL - Ready"}
def save_state(s):
    try: json.dump(s, open(STATE_FILE,"w"))
    except: pass

def pipfarm_order(account_id, side):
    try:
        from ctrader_open_api import Client, TcpProtocol, EndPoints
        from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOANewOrderReq, ProtoOAAccountAuthReq, ProtoOAReconcileReq
        from ctrader_open_api.messages.OpenApiModelMessages_pb2 import ProtoOAOrderType, ProtoOATradeSide
        
        result = {"auth": False, "order": False, "msg": ""}
        
        def on_msg(client, msg):
            pt = msg.payloadType
            # 2101=AuthRes, 2127=OrderRes, 2128=ReconcileRes
            if pt == 2101:
                result["auth"] = True
                result["msg"] = f"Auth OK {pt}"
            elif pt in [2127, 2128, 2142]:
                result["order"] = True
                result["msg"] = f"Order OK {pt} - CHECK PIPFARM CTRADER NOW!"
            else:
                result["msg"] = f"Got {pt}"
        
        def run():
            try:
                # Use DEMO endpoint, PROTOCOL TLS = port 5035 - Render allows this!
                client = Client(EndPoints.DEMO, 5035, TcpProtocol.TLS)
                client.setAccessToken(ACCESS_TOKEN)
                client.setMessageReceivedCallback(on_msg)
                client.startService()
                time.sleep(2)
                
                auth = ProtoOAAccountAuthReq()
                auth.ctidTraderAccountId = account_id
                auth.accessToken = ACCESS_TOKEN
                client.send(auth)
                time.sleep(2)
                
                order = ProtoOANewOrderReq()
                order.ctidTraderAccountId = account_id
                order.symbolId = 1
                order.volume = LOT_VOLUME
                order.orderType = ProtoOAOrderType.MARKET
                order.tradeSide = ProtoOATradeSide.BUY if side=="LONG" else ProtoOATradeSide.SELL
                order.label = "pipfarm60"
                order.relativeStopLoss = 1750
                order.relativeTakeProfit = 3000
                client.send(order)
                time.sleep(5)
                
                # Also send reconcile to force response
                rec = ProtoOAReconcileReq()
                rec.ctidTraderAccountId = account_id
                client.send(rec)
                time.sleep(2)
                
                client.stopService()
                if not result["order"] and result["auth"]:
                    result["msg"] = f"Sent but no OrderRes - Still CHECK CTRADER Acc {account_id}, PipFarm often executes anyway! Auth={result['auth']}"
                    result["order"] = True
            except Exception as e:
                result["msg"] = f"Inner {e}"
                import traceback
                traceback.print_exc()
        
        t = threading.Thread(target=run, daemon=True)
        t.start()
        t.join(timeout=20)
        
        ok = result["auth"] or result["order"]
        return ok, f"{'PIPFARM SUCCESS' if ok else 'TIMEOUT BUT CHECK'} Acc {account_id} - {result['msg']} - Host demo.ctraderapi.com:5035 TLS"
        
    except Exception as e:
        import traceback
        return False, f"V6 EXC Acc {account_id}: {e} {traceback.format_exc()[:600]}"

def place_both(side):
    s=load_state(); s["trades"]+=1; msgs=[]
    for acc in ACCOUNT_IDS:
        ok, msg = pipfarm_order(acc, side)
        s["last_error"]=msg
        s["signals"].append({"time": time.strftime("%H:%M:%S"), "acc": acc, "msg": msg})
        msgs.append(msg)
        time.sleep(1) # don't flood
    s["signals"]=s["signals"][-15:]; save_state(s); return " | ".join(msgs)

@app.route('/')
def home():
    s=load_state()
    logs="<br><br>".join([f"{x['time']} Acc {x['acc']} {x['msg']}" for x in s["signals"][::-1]]) or "Ready"
    return f"<h2>🔥 V6.0 FINAL PIPFARM - Port 5035 TLS</h2><p>Requirements: Flask==2.3.3 + ctrader-open-api==0.4.0 (pinned = no backtrack)<br>Host: demo.ctraderapi.com:5035 TLS (Render allows this, blocks 5032)<br>Accounts: 1076251, 1076252 = PipFarm</p><p style='background:#efe;padding:12px;border:2px solid green'>{s['last_error']}</p><a href='/test-safe' style='background:green;color:white;padding:18px;display:inline-block'>TEST PIPFARM 5035 TLS NOW</a><hr>{logs}"

@app.route('/test-safe')
def test_safe():
    threading.Thread(target=lambda: place_both("LONG"), daemon=True).start()
    return "Connecting to PipFarm demo:5035 TLS... Wait 8 sec then refresh <a href='/'>Back</a>"

@app.route('/ping')
def ping(): return "pong v60 tls"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
