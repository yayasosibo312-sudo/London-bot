# main.py - V5.7.3 SHOWS REAL SERVER ERROR
import os, json, time, threading, requests, random, socket, ssl, struct
from datetime import datetime, date, time as dtime, timezone, timedelta
from flask import Flask, jsonify
from collections import deque
app = Flask(__name__)
ACCESS_TOKEN = "r_pjZaKEPIMbY1Ds5t_TRIMWR1iG5ISvghNXivzGw0o"  # This is refresh token
ACCOUNT_IDS = [1076251, 1076252]
LOT_VOLUME=400000
bot_status="READY V5.7.3 DEBUG ERROR"; last_signal=""; last_logic=""; is_running=False
paused_accounts={1076251:False,1076252:False}; STATE_FILE="/tmp/v573.json"; PRICE=1.0850
price_history=deque(maxlen=120)
for _ in range(120): price_history.append(1.0850+random.uniform(-0.0005,0.0005))

def load_state():
    if os.path.exists(STATE_FILE):
        try: return json.load(open(STATE_FILE))
        except: pass
    return {"profit":0,"profit_A":0,"profit_B":0,"trades":0,"win":0,"loss":0,"date":str(date.today()),"signals":[],"scans":0,"last_error":"No error yet - hit TEST"}
def save_state(s): json.dump(s, open(STATE_FILE,"w"))
def calc_ema(a,p): k=2/(p+1); e=[a[0]]; [e.append(v*k+e[-1]*(1-k)) for v in a[1:]]; return e
def calc_rsi(c,p=14):
    if len(c)<p+1: return 50
    g=l=0
    for i in range(-p,0): d=c[i]-c[i-1]; g+=d if d>0 else 0; l+=-d if d<0 else 0
    return 100 if l==0 else 100-(100/(1+g/l))

def real_order_debug(account_id, side):
    try:
        from ctrader_open_api.messages.OpenApiCommonMessages_pb2 import ProtoMessage
        from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOANewOrderReq, ProtoOAAccountAuthReq
        from ctrader_open_api.messages.OpenApiModelMessages_pb2 import ProtoOAOrderType, ProtoOATradeSide

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ctx = ssl.create_default_context()
        ssock = ctx.wrap_socket(sock, server_hostname="live.ctraderapi.com")
        ssock.connect(("live.ctraderapi.com", 5035))
        ssock.settimeout(8)

        def send_and_read(msg_obj):
            pmsg = ProtoMessage()
            pmsg.payloadType = msg_obj.payloadType
            pmsg.payload = msg_obj.SerializeToString()
            pmsg.clientMsgId = f"{account_id}-{int(time.time()*1000)}"
            raw = pmsg.SerializeToString()
            ssock.sendall(struct.pack('>I', len(raw)) + raw)
            # Read 2 responses
            responses = ""
            for _ in range(3):
                try:
                    header = ssock.recv(4)
                    if len(header)<4: break
                    length = struct.unpack('>I', header)[0]
                    data = b""
                    while len(data) < length:
                        chunk = ssock.recv(length - len(data))
                        if not chunk: break
                        data += chunk
                    # Decode ProtoMessage
                    resp = ProtoMessage()
                    resp.ParseFromString(data)
                    responses += f" [RespType:{resp.payloadType} PayloadLen:{len(resp.payload)} ErrorCode:{resp.errorCode} Msg:{resp.payload[:200]}] "
                except Exception as e_read:
                    responses += f" ReadErr:{e_read} "
                    break
            return responses

        auth = ProtoOAAccountAuthReq()
        auth.ctidTraderAccountId = account_id
        auth.accessToken = ACCESS_TOKEN
        auth_resp = send_and_read(auth)
        time.sleep(0.5)

        req = ProtoOANewOrderReq()
        req.ctidTraderAccountId = account_id
        req.symbolId = 1
        req.volume = LOT_VOLUME
        req.orderType = ProtoOAOrderType.MARKET
        req.tradeSide = ProtoOATradeSide.BUY if side=="LONG" else ProtoOATradeSide.SELL
        req.label = "london-bot"
        order_resp = send_and_read(req)
        
        ssock.close()
        full = f"AUTH_RESP:{auth_resp} | ORDER_RESP:{order_resp}"
        # If errorCode or CH_ACCOUNT_NOT_AUTH, it will show
        if "errorCode" in full.lower() or "CH_" in full or "NOT_AUTH" in full:
            return False, full, PRICE
        return True, full, PRICE
    except Exception as e:
        import traceback
        return False, f"EXC {e} {traceback.format_exc()[:500]}", PRICE

def place_both(side, price, rsi):
    s=load_state(); s["trades"]+=1; out=[]
    for acc in ACCOUNT_IDS:
        ok,msg,_=real_order_debug(acc,side)
        s["last_error"]=msg[:800]
        if not ok: s["signals"].append({"time":str(datetime.now()),"acc":acc,"side":side,"price":price,"rsi":round(rsi,1),"result":f"FAILED: {msg[:200]}"})
        else: s["signals"].append({"time":str(datetime.now()),"acc":acc,"side":side,"price":price,"rsi":round(rsi,1),"result":f"OK: {msg[:200]}"})
        out.append(f"{acc}:{msg[:100]}")
    s["signals"]=s["signals"][-20:]; save_state(s); return " | ".join(out)

def bot_loop():
    global bot_status,last_signal,is_running,PRICE
    SAST=timezone(timedelta(hours=2))
    while is_running:
        now=datetime.now(SAST); s=load_state(); s["scans"]+=1; save_state(s)
        bot_status=f"SCANNING {now.strftime('%H:%M:%S')}"; time.sleep(25)

def safe_test_thread(): place_both("LONG", PRICE, 55)

@app.route('/')
def home():
    s=load_state()
    logs="".join([f"{str(x['time'])[11:19]} Acc:{x.get('acc','')} {x['side']} -> {x['result']}<br><br>" for x in s["signals"][::-1]]) or "No trades"
    return f"<h2>🔥 V5.7.3 DEBUG REAL CTRADER ERROR</h2><p>Status: {bot_status}</p><p><b>Last Error from cTrader Server:</b><br><div style='background:#fee;padding:10px;border:1px solid red'>{s.get('last_error','No error yet')}</div></p><p>Total: {s['trades']} Scans {s['scans']}</p><hr><a href='/test-safe'><b style='background:green;color:white;padding:12px'>TEST SAFE - SHOW REAL ERROR</b></a> | <a href='/status'>JSON</a><hr><b>Log:</b><br>{logs}"

@app.route('/test-safe')
def test_safe():
    threading.Thread(target=safe_test_thread,daemon=True).start()
    return "TEST STARTED - Wait 5 sec then refresh dashboard to see REAL error from cTrader server. <a href='/'>Back to Dashboard</a>"
@app.route('/status')
def status_route(): s=load_state(); return jsonify(s)
@app.route('/ping')
def ping(): return "pong V5.7.3 DEBUG"
@app.route('/run')
def run_bot():
    global is_running
    if not is_running: is_running=True; threading.Thread(target=bot_loop,daemon=True).start()
    return "STARTED <a href='/'>Back</a>"
if __name__=="__main__": app.run(host='0.0.0.0',port=int(os.environ.get("PORT",10000)))
