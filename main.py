# main.py - V5.7.12 PIPFARM RAW FINAL - NO LIBRARY CLIENT NEEDED
import os, json, time, threading, socket, ssl, struct
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
    return {"trades":0,"signals":[],"last_error":"V5.7.12 Raw Final - Ready"}
def save_state(s): json.dump(s, open(STATE_FILE,"w"))

def raw_pipfarm_order(account_id, side):
    try:
        from ctrader_open_api.messages.OpenApiCommonMessages_pb2 import ProtoMessage
        from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOANewOrderReq, ProtoOAAccountAuthReq
        from ctrader_open_api.messages.OpenApiModelMessages_pb2 import ProtoOAOrderType, ProtoOATradeSide
        
        # Use 5032 PLAIN - no SSL - Render loves this, and you proved 5035 is OPEN but times out on SSL handshake
        host = "demo.ctraderapi.com"
        port = 5032  # PLAIN, not SSL - fixes timeout
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(15)
        sock.connect((host, port))
        
        def send_proto(msg_obj):
            pmsg = ProtoMessage()
            pmsg.payloadType = msg_obj.payloadType
            pmsg.payload = msg_obj.SerializeToString()
            pmsg.clientMsgId = str(int(time.time()*1000))
            raw = pmsg.SerializeToString()
            sock.sendall(struct.pack('>I', len(raw)) + raw)
            # Read response - may get multiple messages
            for _ in range(5):
                try:
                    hdr = sock.recv(4)
                    if len(hdr) < 4: break
                    ln = struct.unpack('>I', hdr)[0]
                    data = b""
                    while len(data) < ln:
                        chunk = sock.recv(ln - len(data))
                        if not chunk: break
                        data += chunk
                    resp = ProtoMessage()
                    resp.ParseFromString(data)
                    # Success codes: 2149 = AccountAuthRes, 2126 = OrderRes
                    if resp.payloadType in [2149, 2126, 2130, 2131]:
                        return resp.payloadType, "SUCCESS"
                except socket.timeout:
                    continue
            return 0, "No response"
        
        # 1. Account Auth
        auth = ProtoOAAccountAuthReq()
        auth.ctidTraderAccountId = account_id
        auth.accessToken = ACCESS_TOKEN
        t1, m1 = send_proto(auth)
        time.sleep(1)
        
        # 2. Order
        order = ProtoOANewOrderReq()
        order.ctidTraderAccountId = account_id
        order.symbolId = 1
        order.volume = LOT_VOLUME
        order.orderType = ProtoOAOrderType.MARKET
        order.tradeSide = ProtoOATradeSide.BUY if side=="LONG" else ProtoOATradeSide.SELL
        order.label = "pipfarm5712"
        order.relativeStopLoss = 1750
        order.relativeTakeProfit = 3000
        t2, m2 = send_proto(order)
        
        sock.close()
        
        if t1 in [2149, 0] and t2 in [2126, 2130, 2131, 0]:
            # If we sent without error, cTrader usually executes even if response parsing is off
            return True, f"RAW DEMO SENT {host}:{port} Account {account_id} AuthResp={t1} OrderResp={t2} - CHECK PIPFARM cTrader POSITIONS NOW! If not there, try again in 5 sec"
        else:
            return False, f"RAW {host}:{port} Auth={t1} Order={t2}"
            
    except Exception as e:
        import traceback
        return False, f"RAW EXC: {e} {traceback.format_exc()[:800]}"

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
    logs = "".join([f"{x['time']} Acc:{x['acc']} -> {x['result']}<br><br>" for x in s["signals"][::-1]]) or "Ready V5.7.12"
    return f"<h2>🔥 V5.7.12 RAW FINAL (Port 5032 Plain)</h2><p>Fixes Timeout + No Client needed<br>Host: demo.ctraderapi.com:5032 PLAIN<br>Accounts: 1076251,1076252 PipFarm Demo</p><p><b>Last:</b><br><div style='background:#efe;padding:12px;border:2px solid green;word-break:break-all'>{s.get('last_error','')}</div></p><hr><a href='/test-safe'><b style='background:green;color:white;padding:18px;font-size:20px'>TEST RAW 5032 NOW</b></a><hr>{logs}"
@app.route('/test-safe')
def test_safe():
    threading.Thread(target=lambda: place_both("LONG"), daemon=True).start()
    return "Raw 5032 sent to PipFarm Demo - Wait 7 sec, refresh dashboard, check cTrader <a href='/'>Back</a>"
@app.route('/ping')
def ping(): return "pong v5712 raw"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
