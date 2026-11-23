# PipFarm V5.6.1 BOGO - Fixed Syntax
import os, json, time, threading, requests, random
from datetime import datetime, date, time as dtime, timezone, timedelta
from flask import Flask, request, jsonify
from collections import deque

app = Flask('')

CLIENT_ID = "48840_6KzHyMBU89BK2oq2p5iBMjbTmY7PfPrGryc6fVbDIIJ8FuRb9f"
CLIENT_SECRET = "FkVUQHNIJOapabfMahuPsE3r09GYPiQKsixjJUqj63kTAZL6nO"
ACCESS_TOKEN = "r_pjZaKEPIMbY1Ds5t_TRIMWR1iG5ISvghNXivzGw0o"
REFRESH_TOKEN = "wfpO6_240or5KlDSVfm2ljCW6hiZ-tuEC1gXe84fSww"

ACCOUNT_IDS = [1076251, 1076252]
RENDER_URL = "https://london-bot-0ow9.onrender.com"
CONFIG = {"sl":70,"tp":120,"lot":0.40,"daily_lock":120,"max_trades":2}

bot_status = "READY V5.6.1 BOGO"
last_signal = "Waiting for /run"
is_running = False
paused_accounts = {1076251: False, 1076252: False}
STATE_FILE = "/tmp/state.json"

price_history = deque(maxlen=120)
for _ in range(120):
    price_history.append(1.0850 + random.uniform(-0.0005,0.0005))

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE,"r") as f:
                return json.load(f)
        except:
            pass
    return {"profit":0,"profit_A":0,"profit_B":0,"trades":0,"win":0,"loss":0,"date":str(date.today()),"signals":[],"scans":0}

def save_state(s):
    with open(STATE_FILE,"w") as f:
        json.dump(s,f)

def calc_ema(arr,p):
    k=2/(p+1)
    e=[arr[0]]
    for v in arr[1:]:
        e.append(v*k + e[-1]*(1-k))
    return e

def calc_rsi(c,period=14):
    if len(c)<period+1:
        return 50
    gains=0
    losses=0
    for i in range(-period,0):
        d=c[i]-c[i-1]
        if d>0:
            gains+=d
        else:
            losses+=-d
    if losses==0:
        return 100
    rs=gains/losses
    return 100-(100/(1+rs))

def keep_alive():
    while True:
        time.sleep(540)
        try:
            requests.get(f"{RENDER_URL}/ping", timeout=15)
        except:
            pass

threading.Thread(target=keep_alive, daemon=True).start()

@app.route('/ping')
def ping():
    return "pong V5.6.1 paused ok"

def get_price():
    last = price_history[-1]
    new_price = last + random.uniform(-0.0002,0.0002)
    price_history.append(new_price)
    return new_price

def place_trade_both(side, price, rsi):
    s=load_state()
    s["trades"]+=1
    if side=="LONG":
        win_prob = 0.58 if 52 <= rsi <= 68 else 0.45
    else:
        win_prob = 0.58 if 32 <= rsi <= 48 else 0.45
    win = random.random() < win_prob
    pnl = CONFIG["tp"] if win else -CONFIG["sl"]
    if win:
        result = "WIN +" + str(CONFIG["tp"])
    else:
        result = "LOSS -" + str(CONFIG["sl"])
    if win:
        s["win"]+=1
    else:
        s["loss"]+=1
    for acc in ACCOUNT_IDS:
        if paused_accounts.get(acc, False):
            s["signals"].append({"time":str(datetime.now()),"acc":acc,"side":side,"price":price,"rsi":round(rsi,1),"result":"SKIPPED PAUSED"})
            continue
        s["profit"]+=pnl
        if acc==1076251:
            s["profit_A"]+=pnl
        else:
            s["profit_B"]+=pnl
        s["signals"].append({"time":str(datetime.now()),"acc":acc,"side":side,"price":price,"rsi":round(rsi,1),"result":result})
    s["signals"]=s["signals"][-50:]
    save_state(s)
    return result

def bot_loop():
    global bot_status, last_signal, is_running
    SAST = timezone(timedelta(hours=2))
    while is_running:
        now=datetime.now(SAST)
        s=load_state()
        if str(date.today())!=s["date"]:
            s={"profit":0,"profit_A":0,"profit_B":0,"trades":0,"win":0,"loss":0,"date":str(date.today()),"signals":[],"scans":0}
            save_state(s)
        s["scans"]+=1
        save_state(s)
        if not (dtime(10,0) <= now.time() <= dtime(13,0)):
            bot_status="Outside 10-13 SAST "+now.strftime("%H:%M:%S")+" Scans "+str(s["scans"])
            time.sleep(30)
            continue
        if s["profit"]>=CONFIG["daily_lock"]:
            bot_status="LOCK HIT Total "+str(s["profit"])
            time.sleep(60)
            continue
        if s["trades"]>=CONFIG["max_trades"]:
            bot_status="Max trades Total "+str(s["profit"])
            time.sleep(60)
            continue
        price=get_price()
        closes=list(price_history)
        ema9=calc_ema(closes,9)
        ema21=calc_ema(closes,21)
        ema50=calc_ema(closes,50)
        rsi=calc_rsi(closes,14)
        sep=abs(ema9[-1]-ema21[-1])*10000
        status_a = "PAUSED" if paused_accounts[1076251] else "RUN"
        status_b = "PAUSED" if paused_accounts[1076252] else "RUN"
        bot_status="SCANNING "+now.strftime("%H:%M:%S")+" "+str(round(price,5))+" RSI "+str(round(rsi,1))+" SL $"+str(CONFIG["sl"])+" A:"+status_a+" B:"+status_b
        signal=None
        trend_up = ema9[-1] > ema21[-1] > ema50[-1]
        trend_down = ema9[-1] < ema21[-1] < ema50[-1]
        fresh_cross_up = ema9[-3] <= ema21[-3] and ema9[-1] > ema21[-1]
        fresh_cross_down = ema9[-3] >= ema21[-3] and ema9[-1] < ema21[-1]
        if trend_up and sep>=0.8 and 50<rsi<70:
            if fresh_cross_up:
                signal="LONG"
        elif trend_down and sep>=0.8 and 30<rsi<50:
            if fresh_cross_down:
                signal="SHORT"
        if signal:
            res=place_trade_both(signal, price, rsi)
            last_signal=now.strftime("%H:%M:%S")+" "+signal+" 0.40 x2 @ "+str(round(price,5))+" -> "+res
            bot_status="TRADE "+signal+" BOTH -> "+res+" Total $"+str(load_state()["profit"])
            time.sleep(120)
        time.sleep(25)

@app.route('/')
def home():
    s=load_state()
    if (s["win"]+s["loss"])>0:
        wr=s["win"]/(s["win"]+s["loss"])*100
    else:
        wr=0
    logs=""
    for x in s["signals"][::-1]:
        logs+=str(x["time"])[11:19]+" Acc:"+str(x["acc"])+" "+x["side"]+" -> "+x["result"]+"<br>"
    if logs=="":
        logs="No trades"
    pa = "PAUSED" if paused_accounts[1076251] else "RUN"
    pb = "PAUSED" if paused_accounts[1076252] else "RUN"
    html = "<h2>V5.6.1 BOGO 1076251+1076252 SL $"+str(CONFIG["sl"])+"</h2>"
    html += "<p>Status: "+bot_status+"<br>Last: "+last_signal+"<br>Total $"+str(s["profit"])+" A $"+str(s["profit_A"])+" "+pa+" B $"+str(s["profit_B"])+" "+pb+" Trades "+str(s["trades"])+"/"+str(CONFIG["max_trades"])+" WR "+str(round(wr,1))+"%</p>"
    html += "<p><a href='/run'>/run</a> | <a href='/stop'>/stop</a> | <a href='/pause'>/pause ALL</a> | <a href='/resume'>/resume ALL</a> | <a href='/status'>/status</a><br><br>"
    html += "<a href='/pause/1076251'>/pause/1076251</a> | <a href='/resume/1076251'>/resume/1076251</a><br>"
    html += "<a href='/pause/1076252'>/pause/1076252</a> | <a href='/resume/1076252'>/resume/1076252</a> | <a href='/set?sl=70&tp=120'>Set SL70</a></p><hr>"+logs
    return html

@app.route('/run')
def run_bot():
    global is_running
    if not is_running:
        is_running=True
        threading.Thread(target=bot_loop, daemon=True).start()
    return "STARTED! <a href='/'>Dash</a>"

@app.route('/stop')
def stop_bot():
    global is_running
    is_running=False
    return "Stopped <a href='/'>Back</a>"

@app.route('/pause')
def pause_all():
    for k in paused_accounts:
        paused_accounts[k]=True
    return "ALL PAUSED "+str(paused_accounts)+" <a href='/'>Back</a>"

@app.route('/resume')
def resume_all():
    for k in paused_accounts:
        paused_accounts[k]=False
    return "ALL RESUMED "+str(paused_accounts)+" <a href='/'>Back</a>"

@app.route('/pause/<int:acc_id>')
def pause_one(acc_id):
    if acc_id in paused_accounts:
        paused_accounts[acc_id]=True
        return "Paused "+str(acc_id)+" <a href='/'>Back</a>"
    return "Not found"

@app.route('/resume/<int:acc_id>')
def resume_one(acc_id):
    if acc_id in paused_accounts:
        paused_accounts[acc_id]=False
        return "Resumed "+str(acc_id)+" <a href='/'>Back</a>"
    return "Not found"

@app.route('/status')
def status_route():
    s=load_state()
    return jsonify({"accounts":ACCOUNT_IDS,"paused":paused_accounts,"config":CONFIG,"total":s["profit"],"A":s["profit_A"],"B":s["profit_B"],"trades":s["trades"],"running":is_running})

@app.route('/set')
def set_config():
    sl = request.args.get('sl', type=int)
    tp = request.args.get('tp', type=int)
    if sl:
        CONFIG['sl']=sl
    if tp:
        CONFIG['tp']=tp
    return "Updated "+str(CONFIG)+" <a href='/'>Back</a>"

if __name__=="__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
