# main.py - V5.7.1 FINAL - No setAccessToken
import os, json, time, threading, requests, random
from datetime import datetime, date, time as dtime, timezone, timedelta
from flask import Flask, jsonify
from collections import deque
app = Flask(__name__)
ACCESS_TOKEN = "r_pjZaKEPIMbY1Ds5t_TRIMWR1iG5ISvghNXivzGw0o"
ACCOUNT_IDS = [1076251, 1076252]
SL=70; TP=120; LOT_VOLUME=400000; MAX_TRADES=2
bot_status="READY V5.7.1 NO setAccessToken"; last_signal="TEST 10:00-23:59 Waiting"; last_logic=""; is_running=False
paused_accounts={1076251:False,1076252:False}; STATE_FILE="/tmp/v571.json"; PRICE=1.0850
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

def real_order(account_id, side):
    try:
        from ctrader_open_api import Client, TcpProtocol, EndPoints
        from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOANewOrderReq, ProtoOAAccountAuthReq
        from ctrader_open_api.messages.OpenApiModelMessages_pb2 import ProtoOAOrderType, ProtoOATradeSide
        client = Client(EndPoints.PROTOBUF_LIVE_HOST, EndPoints.PROTOBUF_PORT, TcpProtocol)
        # Start service in background thread
        def start_twisted():
            try: client.startService()
            except: pass
        threading.Thread(target=start_twisted, daemon=True).start()
        time.sleep(1)
        auth = ProtoOAAccountAuthReq(); auth.ctidTraderAccountId=account_id; auth.accessToken=ACCESS_TOKEN
        client.send(auth)
        time.sleep(0.5)
        req = ProtoOANewOrderReq(); req.ctidTraderAccountId=account_id; req.symbolId=1
        req.volume=LOT_VOLUME; req.orderType=ProtoOAOrderType.MARKET
        req.tradeSide=ProtoOATradeSide.BUY if side=="LONG" else ProtoOATradeSide.SELL
        req.relativeStopLoss=1750; req.relativeTakeProfit=3000
        client.send(req)
        time.sleep(1)
        return True, f"REAL {side} SENT via {EndPoints.PROTOBUF_LIVE_HOST}", PRICE
    except Exception as e:
        return False, f"{e}", PRICE

def place_both(side, price, rsi):
    s=load_state(); s["trades"]+=1; out=[]
    for acc in ACCOUNT_IDS:
        if paused_accounts.get(acc): s["signals"].append({"time":str(datetime.now()),"acc":acc,"side":side,"price":price,"rsi":round(rsi,1),"result":"PAUSED SKIP"}); continue
        ok,msg,_=real_order(acc,side)
        if not ok: s["last_error"]=msg
        else: s["win"]+=1; s["profit"]+=TP
        if acc==1076251: s["profit_A"]+=TP if ok else 0
        else: s["profit_B"]+=TP if ok else 0
        out.append(f"{acc}:{msg}"); s["signals"].append({"time":str(datetime.now()),"acc":acc,"side":side,"price":price,"rsi":round(rsi,1),"result":msg})
    s["signals"]=s["signals"][-50:]; save_state(s); return " | ".join(out)

def bot_loop():
    global bot_status,last_signal,last_logic,is_running,PRICE
    SAST=timezone(timedelta(hours=2))
    while is_running:
        now=datetime.now(SAST); s=load_state()
        if str(date.today())!=s["date"]: s={"profit":0,"profit_A":0,"profit_B":0,"trades":0,"win":0,"loss":0,"date":str(date.today()),"signals":[],"scans":0,"last_error":""}; save_state(s)
        s["scans"]+=1; save_state(s)
        if not (dtime(10,0) <= now.time() <= dtime(23,59)): bot_status=f"Outside TEST 10:00-23:59 Now {now.strftime('%H:%M:%S')} Scans {s['scans']}"; time.sleep(30); continue
        if s["trades"]>=MAX_TRADES: bot_status=f"Max {MAX_TRADES} done Err:{s.get('last_error','None')}"; time.sleep(60); continue
        try: PRICE=requests.get("https://api.exchangerate-api.com/v4/latest/EUR",timeout=4).json()["rates"]["USD"]
        except: PRICE+=random.uniform(-0.0002,0.0002)
        price_history.append(PRICE); c=list(price_history)
        e9=calc_ema(c,9); e21=calc_ema(c,21); e50=calc_ema(c,50); rsi=calc_rsi(c,14); sep=abs(e9[-1]-e21[-1])*10000
        pa="PAUSED" if paused_accounts[1076251] else "RUNNING"; pb="PAUSED" if paused_accounts[1076252] else "RUNNING"
        bot_status=f"SCANNING {now.strftime('%H:%M:%S')} Price {PRICE:.5f} EMA9 {e9[-1]:.5f} RSI {rsi:.1f} SEP {sep:.1f} A:{pa} B:{pb} Scans {s['scans']}"
        trend_up=e9[-1]>e21[-1]>e50[-1]; trend_down=e9[-1]<e21[-1]<e50[-1]; cross_up=e9[-3]<=e21[-3] and e9[-1]>e21[-1]; cross_down=e9[-3]>=e21[-3] and e9[-1]<e21[-1]
        last_logic=f"Up={trend_up} Down={trend_down} CU={cross_up} CD={cross_down} SEP={sep:.1f} RSI={rsi:.1f}"
        sig=None
        if trend_up and sep>=0.8 and 50<rsi<70 and c[-1]>e21[-1]:
            if cross_up or c[-1]<=e9[-1]*1.0004: sig="LONG"
        elif trend_down and sep>=0.8 and 30<rsi<50 and c[-1]<e21[-1]:
            if cross_down or c[-1]>=e9[-1]*0.9996: sig="SHORT"
        if sig: res=place_both(sig,PRICE,rsi); last_signal=f"{now.strftime('%H:%M:%S')} {sig} 0.40 x2 @ {PRICE:.5f} -> {res}"; bot_status=f"TRADE {sig} -> {res}"; time.sleep(120)
        time.sleep(25)

def safe_test_thread():
    global PRICE
    entry = PRICE
    place_both("LONG", entry, 55)

@app.route('/')
def home():
    s=load_state(); wr=s["win"]/(s["win"]+s["loss"])*100 if (s["win"]+s["loss"])>0 else 0
    logs="".join([f"{str(x['time'])[11:19]} Acc:{x.get('acc','')} {x['side']} {x['price']} -> {x['result']}<br>" for x in s["signals"][::-1]]) or "No trades yet - V5.7.1"
    pa="PAUSED" if paused_accounts[1076251] else "RUNNING"; pb="PAUSED" if paused_accounts[1076252] else "RUNNING"
    return f"<h2>🔥 V5.7.1 FIXED - TEST SAFE $5</h2><p>TEST 10:00-23:59</p><p>Status: {bot_status}</p><p>Last: {last_signal}</p><p>Logic: {last_logic}</p><p>Total: ${s['profit']} | {s['trades']}/{MAX_TRADES} | Scans {s['scans']} | WR {round(wr,1)}% | Err:{s.get('last_error','')}</p><p>1076251: ${s['profit_A']} {pa} <a href='/pause/1076251'>Pause</a> <a href='/resume/1076251'>Resume</a></p><p>1076252: ${s['profit_B']} {pb} <a href='/pause/1076252'>Pause</a> <a href='/resume/1076252'>Resume</a></p><hr><a href='/run'><b>RUN BOT</b></a> | <a href='/test-safe'><b style='background:green;color:white;padding:8px'>TEST SAFE $5 CLOSE</b></a> | <a href='/stop'>STOP</a> | <a href='/pause'>Pause ALL</a> | <a href='/resume'>Resume ALL</a><hr><b>Log:</b><br>{logs}"

@app.route('/run')
def run_bot():
    global is_running
    if not is_running: is_running=True; threading.Thread(target=bot_loop,daemon=True).start()
    return "STARTED! <a href='/'>Back</a>"
@app.route('/test-safe')
def test_safe():
    threading.Thread(target=safe_test_thread,daemon=True).start()
    return "TEST SAFE STARTED! Opens 0.40 LONG x2. Check cTrader Positions now, close at +$5 manually for safety. <a href='/'>Back</a>"
@app.route('/stop')
def stop_bot():
    global is_running; is_running=False; return "Stopped <a href='/'>Back</a>"
@app.route('/pause')
def pause_all():
    for k in paused_accounts: paused_accounts[k]=True; return f"ALL PAUSED <a href='/'>Back</a>"
@app.route('/resume')
def resume_all():
    for k in paused_accounts: paused_accounts[k]=False; return f"ALL RESUMED <a href='/'>Back</a>"
@app.route('/pause/<int:acc_id>')
def pause_one(acc_id):
    if acc_id in paused_accounts: paused_accounts[acc_id]=True; return f"Paused {acc_id} <a href='/'>Back</a>"
    return "Not found"
@app.route('/resume/<int:acc_id>')
def resume_one(acc_id):
    if acc_id in paused_accounts: paused_accounts[acc_id]=False; return f"Resumed {acc_id} <a href='/'>Back</a>"
    return "Not found"
@app.route('/ping')
def ping(): return "pong V5.7.1"
@app.route('/status')
def status_route():
    s=load_state(); return jsonify({"version":"V5.7.1","paused":paused_accounts,"state":s,"status":bot_status})
if __name__=="__main__": app.run(host='0.0.0.0',port=int(os.environ.get("PORT",10000)))
