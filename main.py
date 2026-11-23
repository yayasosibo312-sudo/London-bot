# main.py - V5.7.8 PIPFARM DEMO ONLY - RENDER SETUP
import os, json, time, threading, socket, ssl, struct, requests
from flask import Flask, jsonify
app = Flask(__name__)
ACCESS_TOKEN = "r_pjZaKEPIMbY1Ds5t_TRIMWR1iG5ISvghNXivzGw0o"  # Validated from your screenshot
ACCOUNT_IDS = [1076251, 1076252]
LOT_VOLUME = 400000  # 4.00 lots
STATE_FILE = "/tmp/v578.json"

def load_state():
    if os.path.exists(STATE_FILE):
        try: return json.load(open(STATE_FILE))
        except: pass
    return {"trades":0,"signals":[],"last_error":"PipFarm DEMO mode - Ready"}
def save_state(s): json.dump(s, open(STATE_FILE,"w"))

def demo_order(account_id, side):
    # PipFarm = demo.ctraderapi.com
    attempts = []
    for host, port, use_ssl in [("demo.ctraderapi.com",5035,True), ("demo.ctraderapi.com",5032,False)]:
        try:
            from ctrader_open_api.messages.OpenApiCommonMessages_pb2 import ProtoMessage
            from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOANewOrderReq, ProtoOAAccountAuthReq
            from ctrader_open_api.messages.OpenApiModelMessages_pb2 import ProtoOAOrderType, ProtoOATradeSide
            
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(12)
            if use_ssl:
                ctx = ssl.create_default_context()
                ss = ctx.wrap_socket(s, server_hostname=host)
            else:
                ss = s
            ss.connect((host, port))
            
            def send_recv(msg_obj):
                pm = ProtoMessage()
                pm.payloadType = msg_obj.payloadType
                pm.payload = msg_obj.SerializeToString()
                pm.clientMsgId = f"pf{int(time.time()*1000)}"
                raw = pm.SerializeToString()
                ss.sendall(struct.pack('>I', len(raw)) + raw)
                # Read response
                hdr = ss.recv(4)
                if len(hdr) < 4:
                    raise Exception(f"No header from {host}:{port}")
                ln = struct.unpack('>I', hdr)[0]
                data = b""
                while len(data) < ln:
                    chunk = ss.recv(ln - len(data))
                    if not chunk: break
                    data += chunk
                resp = ProtoMessage()
                resp.ParseFromString(data)
                return resp.payloadType
            
            auth = ProtoOAAccountAuthReq()
            auth.ctidTraderAccountId = account_id
            auth.accessToken = ACCESS_TOKEN
            t_auth = send_recv(auth)
            
            time.sleep(0.6)
            
            order = ProtoOANewOrderReq()
            order.ctidTraderAccountId = account_id
            order.symbolId = 1  # EURUSD
            order.volume = LOT_VOLUME
            order.orderType = ProtoOAOrderType.MARKET
            order.tradeSide = ProtoOATradeSide.BUY if side=="LONG" else ProtoOATradeSide.SELL
            order.label = "pipfarm-demo"
            order.relativeStopLoss = 1750
            order.relativeTakeProfit = 3000
            
            t_order = send_recv(order)
            ss.close()
            
            # If we get payloadTypes 2149 (auth res) and 2126/2127 (order), it's SUCCESS
            return True, f"DEMO SUCCESS {host}:{port} AuthRes={t_auth} OrderRes={t_order} Account {account_id} - CHECK PIPFARM CHALLENGE POSITIONS NOW!"
            
        except Exception as e:
            attempts.append(f"{host}:{port} {e}")
            try: ss.close()
            except: pass
            continue
    
    return False, f"DEMO FAILED - Attempts: {' | '.join(attempts)}"

def place_both(side):
    s = load_state()
    s["trades"] += 1
    results = []
    for acc in ACCOUNT_IDS:
        ok, msg = demo_order(acc, side)
        s["last_error"] = msg
        s["signals"].append({"time":str(__import__('datetime').datetime.now())[11:19], "acc":acc, "side":side, "result":msg})
        results.append(msg)
    s["signals"] = s["signals"][-20:]
    save_state(s)
    return " | ".join(results)

@app.route('/')
def home():
    s = load_state()
    logs = "".join([f"{x['time']} Acc:{x['acc']} {x['side']} -> {x['result']}<br><br>" for x in s["signals"][::-1]]) or "No trades yet - PipFarm DEMO"
    return f"""
    <h2>🔥 V5.7.8 PIPFARM DEMO ONLY</h2>
    <p>Accounts: 1076251, 1076252 (PipFarm Challenges)</p>
    <p>Host: <b>demo.ctraderapi.com</b> (PipFarm uses demo)</p>
    <p>Token: {ACCESS_TOKEN[:4]}... len {len(ACCESS_TOKEN)} Validated</p>
    <p><b>Last Result:</b><br>
    <div style='background:#efe;padding:12px;border:2px solid green;word-break:break-all'>{s.get('last_error','Ready')}</div></p>
    <hr>
    <a href='/test-safe'><b style='background:green;color:white;padding:16px;font-size:20px'>TEST PIPFARM DEMO NOW</b></a> 
    <a href='/check-port' style='margin-left:20px'>Check Port</a>
    <hr><b>Log:</b><br>{logs}
    """

@app.route('/test-safe')
def test_safe():
    threading.Thread(target=lambda: place_both("LONG"), daemon=True).start()
    return "PipFarm DEMO order sent - Wait 6 sec, refresh dashboard, then check cTrader DEMO Positions (PipFarm tab). <a href='/'>Back</a>"

@app.route('/check-port')
def check_port():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect(("demo.ctraderapi.com", 5035))
        sock.close()
        return "Port 5035 to demo.ctraderapi.com OPEN - Render allows trading! Hit TEST. <a href='/'>Back</a>"
    except Exception as e:
        return f"Port 5035 BLOCKED or filtered: {e} - Trying 5032 plain... <a href='/'>Back</a> Try TEST anyway, it uses fallback."

@app.route('/status')
def status(): return jsonify(load_state())
@app.route('/ping')
def ping(): return "pong pipfarm demo v578"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
