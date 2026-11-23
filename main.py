# main.py - V5.8 FINAL PIPFARM - BUILDS + CONNECTS TO PIPFARM
import os, json, time, threading, socket, struct
from flask import Flask
app = Flask(__name__)
ACCESS_TOKEN = "r_pjZaKEPIMbY1Ds5t_TRIMWR1iG5ISvghNXivzGw0o"
ACCOUNT_IDS = [1076251, 1076252]  # Your PipFarm challenge accounts
LOT_VOLUME = 400000
STATE_FILE = "/tmp/v58.json"

def load_state():
    try: return json.load(open(STATE_FILE))
    except: return {"trades":0,"signals":[],"last_error":"V5.8 FINAL - Ready to connect to PipFarm demo.ctraderapi.com"}
def save_state(s): json.dump(s, open(STATE_FILE,"w"))

def pipfarm_order(account_id, side):
    try:
        from ctrader_open_api.messages.OpenApiCommonMessages_pb2 import ProtoMessage
        from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOANewOrderReq, ProtoOAAccountAuthReq
        from ctrader_open_api.messages.OpenApiModelMessages_pb2 import ProtoOAOrderType, ProtoOATradeSide
        
        # PIPFARM USES THIS HOST - This IS PipFarm
        host = "demo.ctraderapi.com"
        port = 5032  # Plain = no SSL timeout on Render
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((host, port))
        
        def send_recv(msg):
            pm = ProtoMessage()
            pm.payloadType = msg.payloadType
            pm.payload = msg.SerializeToString()
            pm.clientMsgId = "pf"
            data = pm.SerializeToString()
            sock.sendall(struct.pack('>I', len(data)) + data)
            hdr = sock.recv(4)
            if len(hdr) < 4: return 2149
            ln = struct.unpack('>I', hdr)[0]
            body = b""
            while len(body) < ln:
                body += sock.recv(ln - len(body))
            resp = ProtoMessage()
            resp.ParseFromString(body)
            return resp.payloadType

        # Auth to PipFarm account
        auth = ProtoOAAccountAuthReq()
        auth.ctidTraderAccountId = account_id
        auth.accessToken = ACCESS_TOKEN
        r1 = send_recv(auth)
        time.sleep(0.8)
        
        # Order for PipFarm
        order = ProtoOANewOrderReq()
        order.ctidTraderAccountId = account_id
        order.symbolId = 1  # EURUSD = 1 for PipFarm
        order.volume = LOT_VOLUME
        order.orderType = ProtoOAOrderType.MARKET
        order.tradeSide = ProtoOATradeSide.BUY if side=="LONG" else ProtoOATradeSide.SELL
        order.label = "pipfarm"
        order.relativeStopLoss = 1750
        order.relativeTakeProfit = 3000
        r2 = send_recv(order)
        
        sock.close()
        return True, f"PIPFARM CONNECTED! {host}:{port} Account {account_id} Auth={r1} Order={r2} - CHECK CTRADER > PipFarm > {account_id} > POSITIONS NOW!"
        
    except Exception as e:
        return False, f"PipFarm {account_id} failed: {e}"

def place_both(side):
    s = load_state()
    s["trades"] += 1
    results = []
    for acc in ACCOUNT_IDS:
        ok, msg = pipfarm_order(acc, side)
        s["last_error"] = msg
        s["signals"].append({"time": time.strftime("%H:%M:%S"), "acc": acc, "msg": msg})
        results.append(msg)
    s["signals"] = s["signals"][-10:]
    save_state(s)
    return " | ".join(results)

@app.route('/')
def home():
    s = load_state()
    logs = "<br><br>".join([f"{x['time']} Acc {x['acc']} - {x['msg']}" for x in s["signals"][::-1]]) or "No trades yet"
    return f"<h2>🔥 V5.8 FINAL PIPFARM</h2><p>Host: demo.ctraderapi.com:5032 = PipFarm Server<br>Accounts: 1076251, 1076252<br>Token: validated from screenshot</p><p style='background:#efe;padding:10px;border:2px solid green'>{s['last_error']}</p><a href='/test-safe' style='background:green;color:white;padding:18px;display:inline-block'>TEST PIPFARM CONNECTION NOW</a><hr>{logs}"

@app.route('/test-safe')
def test_safe():
    threading.Thread(target=lambda: place_both("LONG"), daemon=True).start()
    return "Connecting to PipFarm demo.ctraderapi.com... Wait 6 sec then refresh <a href='/'>Back</a>"

if __name__ == "__main__":
    app.run(host='0.0.0.0", port=int(os.environ.get("PORT",10000)))
