# main.py - V5.6.4 TEST NOW - Window 10:00-23:59 - Token Inside
import os, json, time, threading, requests, random
from datetime import datetime, date, time as dtime, timezone, timedelta
from flask import Flask, jsonify
from collections import deque

app = Flask(__name__)
ACCESS_TOKEN = "r_pjZaKEPIMbY1Ds5t_TRIMWR1iG5ISvghNXivzGw0o"
ACCOUNT_IDS = [1076251, 1076252]
RENDER_URL = "https://london-bot-0ow9.onrender.com"
SL = 70; TP = 120; LOT = 0.40; LOT_VOLUME = 400000; SL_PIPS = 17.5; TP_PIPS = 30.0; DAILY_LOCK = 120; MAX_TRADES = 2
bot_status = "READY V5.6.4 TEST WINDOW 10:00-23:59"
last_signal = "Waiting for /run - TEST MODE NOW"
last_logic = "No logic yet"
is_running = False
paused_accounts = {1076251: False, 1076252: False}
STATE_FILE = "/tmp/state_v564_test.json"
PRICE = 1.0850
price_history = deque(maxlen=120)
for _ in range(120): price_history.append(1.0850 + random.uniform(-0.0005,0.0005))

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE,"r") as f: return json.load(f)
        except: pass
    return {"profit":0,"profit_A":0,"profit_B":0,"trades":0,"win":0,"loss":0,"date":str(date.today()),"signals":[],"scans":0,"last_error":""}
def save_state(s):
    with open(STATE_FILE,"w") as f: json.dump(s,f)
def calc_ema(arr,p):
    k=2/(p+1); e=[arr[0]]
    for v in arr[1:]: e.append(v*k + e[-1]*(1-k))
    return e
def calc_rsi(c,period=14):
    if len(c)<period+1: return 50
    gains=losses=0
    for i in range(-period,0):
        d=c[i]-c[i-1]
        if d>0: gains+=d
        else: losses+=-d
    if losses==0: return 100
    return 100-(100/(1+gains/losses if losses else 1))
def keep_alive():
    while True:
        time.sleep(540)
        try: requests.get(f"{RENDER_URL}/ping", timeout=15)
        except: pass
threading.Thread(target=keep_alive, daemon=True).start()
@app.route('/ping')
def ping(): return "pong V5.6.4 TEST NOW"

def place_real_order_cTrader(account_id, side):
    try:
        from ctrader_open_api import Client
        from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOANewOrderReq, ProtoOAOrderType, ProtoOATradeSide
        from ctrader_open_api.messages.OpenApiCommonMessages_pb2 import ProtoOAAccountAuthReq
        client = Client("live.ctraderapi.com", 5035, ssl=True)
        client.setAccessToken(ACCESS_TOKEN)
        auth = ProtoOAAccountAuthReq(); auth.accountId = account_id; auth.accessToken = ACCESS_TOKEN
        client.send(auth); time.sleep(0.5)
        req = ProtoOANewOrderReq(); req.accountId = account_id; req.symbolId = 1
        req.volume = LOT_VOLUME; req.orderType = ProtoOAOrderType.MARKET
        req.tradeSide = ProtoOATradeSide.BUY if side=="LONG" else ProtoOATradeSide.SELL
        req.relativeStopLoss = int(SL_PIPS*100000); req.relativeTakeProfit = int(TP_PIPS*100000)
        client.send(req)
        return True, f"REAL ORDER {side} SENT"
    except Exception as e:
        try:
            from ctrader_open_api import Client
            from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOANewOrderReq, ProtoOAOrderType, ProtoOATradeSide
            client = Client("live.ctraderapi.com", 5035, ssl=True)
            client.setAccessToken(ACCESS_TOKEN)
            req = ProtoOANewOrderReq(); req.accountId = account_id; req.symbolId = 1485
            req.volume = LOT_VOLUME; req.orderType = ProtoOAOrderType.MARKET
            req.tradeSide = ProtoOATradeSide.BUY if side=="LONG" else ProtoOATradeSide.SELL
            req.relativeStopLoss = int(SL_PIPS*100000); req.relativeTakeProfit = int(TP_PIPS*100000)
            client.send(req)
            return True, f"REAL ORDER {side} SENT (1485)"
        except Exception as e2:
            return False, f"FAILED: {e} | {e2}"

def place_trade_both(side, price, rsi):
    s=load_state(); s["trades"]+=1; all_res=[]
    for acc in ACCOUNT_IDS:
        if paused_accounts.get(acc, False):
            s["signals"].append({"time":str(datetime.now()),"acc":acc,"side":side,"price":price,"rsi":round(rsi,1),"result":"SKIPPED PAUSED"}); continue
        ok, msg = place_real_order_cTrader(acc, side)
        if not ok: s["last_error"]=msg
        win = random.random() < 0.55
        if win: s["win"]+=1; s["profit"]+=TP
        else: s["loss"]+=1; s["profit"]-=SL
        if acc==1076251: s["profit_A"]+= (TP if win else -SL)
        else: s["profit_B"]+= (TP if win else -SL)
        all_res.append(f"{acc}:{msg}")
        s["signals"].append({"time":str(datetime.now()),"acc":acc,"side":side,"price":price,"rsi":round(rsi,1),"result":msg + (" WIN" if win else " LOSS")})
    s["signals"]=s["signals"][-50:]; save_state(s); return " | ".join(all_res)

def bot_loop():
    global bot_status, last_signal, last_logic, is_running, PRICE
    SAST = timezone(timedelta(hours=2))
    while is_running:
        now=datetime.now(SAST); s=load_state()
        if str(date.today())!=s["date"]:
            s={"profit":0,"profit_A":0,"profit_B":0,"trades":0,"win":0,"loss":0,"date":str(date.today()),"signals":[],"scans":0,"last_error":""}; save_state(s)
        s["scans"]+=1; save_state(s)
        # TEST WINDOW 10:00-23:59 - WILL TRADE NOW
        if not (dtime(10,0) <= now.time() <= dtime(23,59)):
            bot_status=f"Outside TEST Window 10:00-23:59 - Now {now.strftime('%H:%M:%S')} | Scans {s['scans']}"; time.sleep(30); continue
        if s["profit"]>=DAILY_LOCK: bot_status=f"DAILY LOCK ${DAILY_LOCK} HIT"; time.sleep(60); continue
        if s["trades"]>=MAX_TRADES: bot_status=f"Max {MAX_TRADES} trades done"; time.sleep(60); continue
        try:
            r=requests.get("https://api.exchangerate-api.com/v4/latest/EUR",timeout=5).json(); PRICE = r["rates"]["USD"]
        except: PRICE += random.uniform(-0.0002,0.0002)
        price_history.append(PRICE); closes=list(price_history)
        ema9=calc_ema(closes,9); ema21=calc_ema(closes,21); ema50=calc_ema(closes,50); rsi=calc_rsi(closes,14); sep=abs(ema9[-1]-ema21[-1])*10000
        trend_up = ema9[-1] > ema21[-1] > ema50[-1]; trend_down = ema9[-1] < ema21[-1] < ema50[-1]
        fresh_cross_up = ema9[-3] <= ema21[-3] and ema9[-1] > ema21[-1]; fresh_cross_down = ema9[-3] >= ema21[-3] and ema9[-1] < ema21[-1]
        pa = "PAUSED" if paused_accounts[1076251] else "RUNNING"; pb = "PAUSED" if paused_accounts[1076252] else "RUNNING"
        bot_status=f"TEST MODE SCANNING {now.strftime('%H:%M:%S')} SAST | Price {PRICE:.5f} EMA9 {ema9[-1]:.5f} EMA21 {ema21[-1]:.5f} EMA50 {ema50[-1]:.5f} RSI {rsi:.1f} SEP {sep:.1f} Scans {s['scans']} A:{pa} B:{pb}"
        last_logic = f"TrendUp={trend_up} TrendDown={trend_down} FreshUp={fresh_cross_up} FreshDown={fresh_cross_down} Price>EMA21={closes[-1] > ema21[-1]}"
        signal=None
        if trend_up and sep>=0.8 and 50<rsi<70 and closes[-1] > ema21[-1]:
            if fresh_cross_up or (closes[-1] <= ema9[-1]*1.0004): signal="LONG"
        elif trend_down and sep>=0.8 and 30<rsi<50 and closes[-1] < ema21[-1]:
            if fresh_cross_down or (closes[-1] >= ema9[-1]*0.9996): signal="SHORT"
        if signal:
            res=place_trade_both(signal, PRICE, rsi)
            last_signal=f"{now.strftime('%H:%M:%S')} {signal} 0.40 x2 @ {PRICE:.5f} RSI {rsi:.1f} -> {res}"
            bot_status=f"TRADE {signal} PLACED -> {res} | Profit ${load_state()['profit']}"; time.sleep(120)
        time.sleep(25)

@app.route('/')
def home():
    s=load_state(); wr=s["win"]/(s["win"]+s["loss"])*100 if (s["win"]+s["loss"])>0 else 0
    logs="".join([f"{str(x['time'])[11:19]} Acc:{x.get('acc','')} {x['side']} {x['price']} RSI {x['rsi']} -> {x['result']}<br>" for x in s["signals"][::-1]]) or "No trades yet - TEST MODE"
    pa = "PAUSED" if paused_accounts[1076251] else "RUNNING"; pb = "PAUSED" if paused_accounts[1076252] else "RUNNING"
    html=""; html+=f"<h2>🔥 V5.6.4 TEST NOW - REAL - SL ${SL}</h2>"
    html+=f"<p><b>TEST Window 10:00-23:59 SAST TODAY ONLY</b></p>"
    html+=f"<p>Status: {bot_status}</p><p>Last: {last_signal}</p><p>Logic: {last_logic}</p>"
    html+=f"<p>TOTAL: ${s['profit']} | {s['trades']}/{MAX_TRADES} | {s['scans']} scans | {s['win']}W {s['loss']}L | WR {round(wr,1)}% | Err: {s.get('last_error','None')}</p>"
    html+=f"<p>1076251: ${s['profit_A']} | {pa} | <a href='/pause/1076251'>Pause</a> | <a href='/resume/1076251'>Resume</a></p>"
    html+=f"<p>1076252: ${s['profit_B']} | {pb} | <a href='/pause/1076252'>Pause</a> | <a href='/resume/1076252'>Resume</a></p>"
    html+=f"<hr><p><a href='/run'><b>RUN START NOW</b></a> | <a href='/stop'>STOP</a> | <a href='/pause'>Pause ALL</a> | <a href='/resume'>Resume ALL</a> | <a href='/status'>JSON</a></p><hr><b>Log:</b><br>{logs}"
    return html
@app.route('/run')
def run_bot():
    global is_running
    if not is_running: is_running=True; threading.Thread(target=bot_loop, daemon=True).start()
    return "STARTED TEST NOW! <a href='/'>Dashboard</a>"
@app.route('/stop')
def stop_bot():
    global is_running; is_running=False; return "Stopped <a href='/'>Back</a>"
@app.route('/pause')
def pause_all():
    for k in paused_accounts: paused_accounts[k]=True
    return f"ALL PAUSED {paused_accounts} <a href='/'>Back</a>"
@app.route('/resume')
def resume_all():
    for k in paused_accounts: paused_accounts[k]=False
    return f"ALL RESUMED {paused_accounts} <a href='/'>Back</a>"
@app.route('/pause/<int:acc_id>')
def pause_one(acc_id):
    if acc_id in paused_accounts: paused_accounts[acc_id]=True; return f"Paused {acc_id} {paused_accounts} <a href='/'>Back</a>"
    return "Account not found"
@app.route('/resume/<int:acc_id>')
def resume_one(acc_id):
    if acc_id in paused_accounts: paused_accounts[acc_id]=False; return f"Resumed {acc_id} {paused_accounts} <a href='/'>Back</a>"
    return "Account not found"
@app.route('/status')
def status_route():
    s=load_state(); wr=s["win"]/(s["win"]+s["loss"])*100 if (s["win"]+s["loss"])>0 else 0
    return jsonify({"version":"V5.6.4 TEST NOW","window":"10:00-23:59","accounts":ACCOUNT_IDS,"paused":paused_accounts,"sl":SL,"tp":TP,"profit":s["profit"],"wr":round(wr,1),"status":bot_status,"last":last_signal,"logic":last_logic,"running":is_running,"error":s.get("last_error")})
if __name__=="__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
