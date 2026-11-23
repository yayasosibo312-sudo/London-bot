# main.py - V5.7.12 PIPFARM RAW FINAL - NO CLIENT NEEDED
import os, json, time, threading, socket, struct
from flask import Flask
app = Flask(__name__)
ACCESS_TOKEN = "r_pjZaKEPIMbY1Ds5t_TRIMWR1iG5ISvghNXivzGw0o"
ACCOUNT_IDS = [1076251, 1076252]
LOT_VOLUME = 400000
STATE_FILE = "/tmp/v5712.json"
def load_state():
    if os.path.exists(STATE_FILE):
        try: return json.load(open(STATE_FILE))
        except: pass
    return {"trades":0,"signals":[],"last_error":"V5.7.12 Raw Final - Ready - Fix requirements.txt to build"}
def save_state(s): json.dump(s, open(STATE_FILE,"w"))
def raw_pipfarm_order(account_id, side):
    try:
        from ctrader_open_api.messages.OpenApiCommonMessages_pb2 import ProtoMessage
        from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOANewOrderReq, ProtoOAAccountAuthReq
        from ctrader_open_api.messages.OpenApiModelMessages_pb2 import ProtoOAOrderType, ProtoOATradeSide
        host = "demo.ctraderapi.com"; port = 5032
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(15); sock.connect((host, port))
        def send_proto(msg_obj):
            pmsg = ProtoMessage()
            pmsg.payloadType = msg_obj.payloadType
            pmsg.payload = msg_obj.SerializeToString()
            pmsg.clientMsgId = str(int(time.time()*1000))
            raw = pmsg.SerializeToString()
            sock.sendall(struct.pack('>I', len(raw)) + raw)
            try:
                hdr = sock.recv(4)
                if len(hdr) < 4: return 0, "No header"
                ln = struct.unpack('>I', hdr)[0]
                data = b""
                while len(data) < ln:
                    chunk = sock.recv(ln - len(data))
                    if not chunk: break
                    data += chunk
                resp = ProtoMessage(); resp.ParseFromString(data)
                return resp.payloadType, "OK"
            except socket.timeout:
                return 0, "Timeout but sent"
        auth = ProtoOAAccountAuthReq(); auth.ctidTraderAccountId = account_id; auth.accessToken = ACCESS_TOKEN
        t1,_ = send_proto(auth); time.sleep(1)
        order = ProtoOANewOrderReq(); order.ctidTraderAccountId = account_id; order.symbolId = 1; order.volume = LOT_VOLUME; order.orderType = ProtoOAOrderType.MARKET
        order.tradeSide = order.tradeSide = __import__('ctrader_open_api.messages.OpenApiModelMessages_pb2', fromlist=['ProtoOATradeSide']).ProtoOATradeSide.BUY if side=="LONG" else __import__('ctrader_open_api.messages.OpenApiModelMessages_pb2', fromlist=['ProtoOATradeSide']).ProtoOATradeSide.SELL
        order.label = "pipfarm5712"; order.relativeStopLoss = 1750; order.relativeTakeProfit = 3000
        t2,_ = send_proto(order)
        sock.close()
        return True, f"RAW DEMO SENT {host}:{port} Acc {account_id} Auth={t1} Order={t2} - CHECK PIPFARM CTRADER NOW! Trade may be there even if resp 0"
    except Exception as e:
        import traceback; return False, f"RAW EXC: {e} {traceback.format_exc()[:800]}"
def place_both(side):
    s = load_state(); s["trades"] += 1
    for acc in ACCOUNT_IDS:
        ok, msg = raw_pipfarm_order(acc, side)
        s["last_error"] = msg
        s["signals"].append({"time":__import__('datetime').datetime.now().strftime("%H:%M:%S"), "acc":acc, "side":side, "result":msg})
    s["signals"] = s["signals"][-20:]; save_state(s); return s["last_error"]
@app.route('/')
def home():
    s = load_state()
    logs = "".join([f"{x['time']} Acc:{x['acc']} -> {x['result']}<br><br>" for x in s["signals"][::-1]]) or "Ready"
    return f"<h2>🔥 V5.7.12 RAW FINAL Port 5032</h2><p>Requirements fixed: Flask, protobuf, ctrader-open-api</p><p><b>Last:</b><br><div style='background:#efe;padding:12px;border:2px solid green;word-break:break-all'>{s.get('last_error','')}</div></p><hr><a href='/test-safe'><b style='background:green;color:white;padding:18px;font-size:20px'>TEST RAW 5032 NOW</b></a><hr>{logs}"
@app.route('/test-safe')
def test_safe():
    threading.Thread(target=lambda: place_both("LONG"), daemon=True).start()
    return "Raw 5032 sent - Wait 7 sec refresh <a href='/'>Back</a>"
@app.route('/ping')
def ping(): return "pong v5712 raw"
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
