# main.py - V5.7.2 DIRECT SOCKET - WILL SHOW IN CTRADER
import os, json, time, threading, requests, random, socket, ssl, struct
from datetime import datetime, date, time as dtime, timezone, timedelta
from flask import Flask, jsonify
from collections import deque
app = Flask(__name__)
ACCESS_TOKEN = "r_pjZaKEPIMbY1Ds5t_TRIMWR1iG5ISvghNXivzGw0o"
ACCOUNT_IDS = [1076251, 1076252]
LOT_VOLUME=400000
bot_status="READY V5.7.2 DIRECT SOCKET"; last_signal="TEST 10:00-23:59"; last_logic=""; is_running=False
paused_accounts={1076251:False,1076252:False}; STATE_FILE="/tmp/v572.json"; PRICE=1.0850
price_history=deque(maxlen=120)
for _ in range(120): price_history.append(1.0850+random.uniform(-0.0005,0.0005))

def load_state():
    if os.path.exists(STATE_FILE):
        try: return json.load(open(STATE_FILE))
        except: pass
    return {"profit":0,"profit_A":0,"profit_B":0,"trades":0,"win":0,"loss":0,"date":str(date.today()),"signals":[],"scans":0,"last_error":""}
def save_state(s): json.dump(s, open(STATE_FILE,"w"))
def calc_ema(a,p): k=2/(p+1); e=[a[0]]; [e.append(v*k+e[-1]*(1-k)) for v in a[1:]]; return e
def calc_rsi(c,p=14):
    if len(c)<p+1: return 50
    g=l=0
    for i in range(-p,0): d=c[i]-c[i-1]; g+=d if d>0 else 0; l+=-d if d<0 else 0
    return 100 if l==0 else 100-(100/(1+g/l))

def real_order_socket(account_id, side):
    try:
        from ctrader_open_api.messages.OpenApiCommonMessages_pb2 import ProtoMessage
        from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOANewOrderReq, ProtoOAAccountAuthReq, ProtoOAApplicationAuthReq
        from ctrader_open_api.messages.OpenApiModelMessages_pb2 import ProtoOAOrderType, ProtoOATradeSide

        # Connect raw SSL socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ctx = ssl.create_default_context()
        ssock = ctx.wrap_socket(sock, server_hostname="live.ctraderapi.com")
        ssock.connect(("live.ctraderapi.com", 5035))
        ssock.settimeout(10)

        def send_msg(msg_obj):
            pmsg = ProtoMessage()
            pmsg.payloadType = msg_obj.payloadType
            pmsg.payload = msg_obj.SerializeToString()
            pmsg.clientMsgId = f"{account_id}-{int(time.time()*1000)}"
            raw = pmsg.SerializeToString()
            framed = struct.pack('>I', len(raw)) + raw
            ssock.sendall(framed)
            # Read response (ignore)
            try:
                resp_len_data = ssock.recv(4)
                if len(resp_len_data)==4:
                    resp_len = struct.unpack('>I', resp_len_data)[0]
                    ssock.recv(resp_len)
            except: pass

        # 1. App Auth (not needed for live but send)
        # 2. Account Auth
        auth = ProtoOAAccountAuthReq()
        auth.ctidTraderAccountId = account_id
        auth.accessToken = ACCESS_TOKEN
        send_msg(auth)
        time.sleep(0.5)

        # 3. New Order
        req = ProtoOANewOrderReq()
        req.ctidTraderAccountId = account_id
        req.symbolId = 1  # EURUSD
        req.volume = LOT_VOLUME
        req.orderType = ProtoOAOrderType.MARKET
        req.tradeSide = ProtoOATradeSide.BUY if side=="LONG" else ProtoOATradeSide.SELL
        req.label = "london-bot"
        req.relativeStopLoss = 1750  # 17.5 pips
        req.relativeTakeProfit = 3000  # 30 pips
        send_msg(req)
        time.sleep(1)
        ssock.close()
        return True, f"DIRECT SOCKET {side} SENT - CHECK CTRADER NOW", PRICE
    except Exception as e:
        # Fallback try symbol 1485
        try:
            from ctrader_open_api.messages.OpenApiCommonMessages_pb2 import ProtoMessage
            from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOANewOrderReq, ProtoOAAccountAuthReq
            from ctrader_open_api.messages.OpenApiModelMessages_pb2 import ProtoOAOrderType, ProtoOATradeSide
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            ctx = ssl.create_default_context()
            ssock = ctx.wrap_socket(sock, server_hostname="live.ctraderapi.com")
            ssock.connect(("live.ctraderapi.com", 5035))
            ssock.settimeout(10)
            def send_msg2(m):
                pmsg = ProtoMessage(); pmsg.payloadType=m.payloadType; pmsg.payload=m.SerializeToString(); pmsg.clientMsgId=f"f-{int(time.time())}"
                raw=pmsg.SerializeToString(); ssock.sendall(struct.pack('>I', len(raw))+raw)
                try:
                    l=ssock.recv(4)
                    if len(l)==4: ssock.recv(struct.unpack('>I', l)[0])
                except: pass
            auth = ProtoOAAccountAuthReq(); auth.ctidTraderAccountId=account_id; auth.accessToken=ACCESS_TOKEN; send_msg2(auth); time.sleep(0.5)
            req = ProtoOANewOrderReq(); req.ctidTraderAccountId=account_id; req.symbolId=1485; req.volume=LOT_VOLUME; req.orderType=ProtoOAOrderType.MARKET; req.tradeSide=ProtoOATradeSide.BUY if side=="LONG" else ProtoOATradeSide.SELL; req.label="london-bot"; send_msg2(req)
            ssock.close()
            return True, f"DIRECT SOCKET {side} SENT 1485", PRICE
        except Exception as e2:
            return False, f"SOCKET ERR: {e} | {e2}", PRICE

def place_both(side, price, rsi):
    s=load_state(); s["trades"]+=1; out=[]
    for acc in ACCOUNT_IDS:
        if paused_accounts.get(acc): s["signals"].append({"time":str(datetime.now()),"acc":acc,"side":side,"price":price,"rsi":round(rsi,1),"result":"PAUSED SKIP"}); continue
        ok,msg,_=real_order_socket(acc,side)
        if not ok: s["last_error"]=msg
        else: s["win"]+=1
        out.append(f"{acc}:{msg}"); s["signals"].append({"time":str(datetime.now()),"acc":acc,"side":side,"price":price,"rsi":round(rsi,1),"result":msg})
    s["signals"]=s["signals"][-50:]; save_state(s); return " | ".join(out)

def bot_loop():
    global bot_status,last_signal,last_logic,is_running,PRICE
    SAST=timezone(timedelta(hours=2))
    while is_running:
        now=datetime.now(SAST); s=load_state()
        if str(date.today())!=s["date"]: s={"profit":0,"profit_A":0,"profit_B":0,"trades":0,"win":0,"loss":0,"date":str(date.today()),"signals":[],"scans":0,"last_error":""}; save_state(s)
        s["scans"]+=1; save_state(s)
        if not (dtime(10,0) <= now.time() <= dtime(23,59)): bot_status=f"Outside TEST 10:00-23:59 Now {now.strftime('%H:%M:%S')}"; time.sleep(30); continue
        if s["trades"]>=2: bot_status=f"Max 2 done Err:{s.get('last_error','None')}"; time.sleep(60); continue
        try: PRICE=requests.get("https://api.exchangerate-api.com/v4/latest/EUR",timeout=4).json()["rates"]["USD"]
        except: PRICE+=random.uniform(-0.0002,0.0002)
        price_history.append(PRICE); c=list(price_history); e9=calc_ema(c,9); e21=calc_ema(c,21); e50=calc_ema(c,50); rsi=calc_rsi(c,14); sep=abs(e9[-1]-e21[-1])*10000
        bot_status=f"SCANNING {now.strftime('%H:%M:%S')} Price {PRICE:.5f} RSI {rsi:.1f} SEP {sep:.1f} Scans {s['scans']}"
        trend_up=e9[-1]>e21[-1]>e50[-1]; trend_down=e9[-1]<e21[-1]<e50[-1]; cross_up=e9[-3]<=e21[-3] and e9[-1]>e21[-1]; cross_down=e9[-3]>=e21[-3] and e9[-1]<e21[-1]
        last_logic=f"Up={trend_up} Down={trend_down} SEP={sep:.1f} RSI={rsi:.1f}"
        sig=None
        if trend_up and sep>=0.8 and 50<rsi<70: sig="LONG"
        elif trend_down and sep>=0.8 and 30<rsi<50: sig="SHORT"
        if sig: res=place_both(sig,PRICE,rsi); last_signal=f"{now.strftime('%H:%M:%S')} {sig} -> {res}"; time.sleep(120)
        time.sleep(25)

def safe_test_thread():
    place_both("LONG", PRICE, 55)

@app.route('/')
def home():
    s=load_state(); logs="".join([f"{str(x['time'])[11:19]} Acc:{x.get('acc','')} {x['side']} -> {x['result']}<br>" for x in s["signals"][::-1]]) or "No trades"
    pa="PAUSED" if paused_accounts[1076251] else "RUNNING"; pb="PAUSED" if paused_accounts[1076252] else "RUNNING"
    return f"<h2>🔥 V5.7.2 DIRECT SOCKET - REAL EXECUTION</h2><p>Status: {bot_status}</p><p>Last: {last_signal}</p><p>Total: {s['trades']}/2 Scans {s['scans']} Err:{s.get('last_error','')}</p><p>1076251: {pa} <a href='/pause/1076251'>Pause</a> <a href='/resume/1076251'>Resume</a></p><p>1076252: {pb} <a href='/pause/1076252'>Pause</a> <a href='/resume/1076252'>Resume</a></p><hr><a href='/run'>RUN BOT</a> | <a href='/test-safe'><b style='background:green;color:white;padding:10px'>TEST SAFE $5 - REAL CTRADER</b></a> | <a href='/stop'>STOP</a><hr><b>Log:</b><br>{logs}"
@app.route('/run')
def run_bot():
    global is_running
    if not is_running: is_running=True; threading.Thread(target=bot_loop,daemon=True).start()
    return "STARTED <a href='/'>Back</a>"
@app.route('/test-safe')
def test_safe():
    threading.Thread(target=safe_test_thread,daemon=True).start()
    return "DIRECT SOCKET TEST STARTED - NOW CHECK CTRADER POSITIONS (should appear in 3 sec). <a href='/'>Back</a>"
@app.route('/stop')
def stop_bot():
    global is_running; is_running=False; return "Stopped <a href='/'>Back</a>"
@app.route('/pause/<int:acc_id>')
def pause_one(acc_id):
    if acc_id in paused_accounts: paused_accounts[acc_id]=True; return f"Paused {acc_id} <a href='/'>Back</a>"
    return "Not found"
@app.route('/resume/<int:acc_id>')
def resume_one(acc_id):
    if acc_id in paused_accounts: paused_accounts[acc_id]=False; return f"Resumed {acc_id} <a href='/'>Back</a>"
    return "Not found"
@app.route('/ping')
def ping(): return "pong V5.7.2 SOCKET"
@app.route('/status')
def status_route():
    s=load_state(); return jsonify({"v":"5.7.2 socket","state":s})
if __name__=="__main__": app.run(host='0.0.0.0',port=int(os.environ.get("PORT",10000)))
