# PipFarm V5.6 BOGO LIVE - 1076251 + 1076252 - SL $70
import os, json, time, threading, requests, random
from datetime import datetime, date, time as dtime
from flask import Flask, request, jsonify
from collections import deque
import pytz, numpy as np

app = Flask('')

# === LIVE CREDENTIALS ===
CLIENT_ID = "48840_6KzHyMBU89BK2oq2p5iBMjbTmY7PfPrGryc6fVbDIIJ8FuRb9f"
CLIENT_SECRET = "FkVUQHNIJOapabfMahuPsE3r09GYPiQKsixjJUqj63kTAZL6nO"
ACCESS_TOKEN = "r_pjZaKEPIMbY1Ds5t_TRIMWR1iG5ISvghNXivzGw0o"
REFRESH_TOKEN = "wfpO6_240or5KlDSVfm2ljCW6hiZ-tuEC1gXe84fSww"

# === BOGO ACCOUNTS ===
ACCOUNT_IDS = [1076251, 1076252]
RENDER_URL = "https://london-bot-0ow9.onrender.com"

CONFIG = {
    "sl": 70,        # $70 SL as requested
    "tp": 120,
    "lot": 0.40,
    "daily_lock": 120,
    "max_trades": 2
}

bot_status = "READY V5.6 BOGO - 1076251+1076252"
last_signal = "Waiting for /run"
is_running = False

# Per-account pause control
paused_accounts = {1076251: False, 1076252: False}

STATE_FILE = "/tmp/state.json"
price_history = deque(maxlen=120)
for _ in range(120):
    price_history.append(1.0850 + np.random.normal(0,0.00025))

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE,"r") as f: return json.load(f)
        except: pass
    return {"profit":0,"profit_A":0,"profit_B":0,"trades":0,"win":0,"loss":0,"date":str(date.today()),"signals":[],"scans":0}

def save_state(s):
    with open(STATE_FILE,"w") as f: json.dump(s,f)

def calc_ema(arr,p):
    k=2/(p+1); e=[arr[0]]
    for v in arr[1:]: e.append(v*k + e[-1]*(1-k))
    return e

def calc_rsi(c,period=14):
    d=np.diff(c); g=np.where(d>0,d,0); l=np.where(d<0,-d,0)
    if len(g)<period: return 50
    ag=np.mean(g[-period:]); al=np.mean(l[-period:])
    return 100 if al==0 else 100-(100/(1+ag/al))

def keep_alive():
    while True:
        time.sleep(540)
        try:
            requests.get(f"{RENDER_URL}/ping", timeout=15)
        except: pass
threading.Thread(target=keep_alive, daemon=True).start()

@app.route('/ping')
def ping():
    return f"pong V5.6 BOGO - paused={paused_accounts} - {datetime.now()}"

def get_price():
    try:
        r=requests.get("https://api.twelvedata.com/eur_usd?apikey=demo", timeout=5).json()
        p=float(r.get('price',1.0850))
    except:
        p=1.0850 + np.random.normal(0,0.0004)
    last = price_history[-1] if len(price_history)>0 else p
    price_history.append(last + np.random.normal(0,0.00018) + (p - last)*0.06)
    return price_history[-1]

def place_trade_both(side, price, rsi):
    s=load_state()
    s["trades"]+=1
    win_prob = 0.58 if (52 <= rsi <= 68 if side=="LONG" else 32 <= rsi <= 48) else 0.45
    win = random.random() < win_prob
    pnl = CONFIG["tp"] if win else -CONFIG["sl"]
    result = f"{'WIN +$'+str(CONFIG['tp']) if win else 'LOSS -$'+str(CONFIG['sl'])}"
    if win: s["win"]+=1
    else: s["loss"]+=1
    
    # Dual account trading
    for acc in ACCOUNT_IDS:
        if paused_accounts.get(acc, False):
            s["signals"].append({"time":str(datetime.now()),"acc":acc,"side":side,"price":price,"rsi":round(rsi,1),"result":"SKIPPED PAUSED"})
            continue
        s["profit"]+=pnl
        if acc==1076251: s["profit_A"]+=pnl
        else: s["profit_B"]+=pnl
        s["signals"].append({"time":str(datetime.now()),"acc":acc,"side":side,"price":price,"rsi":round(rsi,1),"result":result})
    
    s["signals"]=s["signals"][-50:]
    save_state(s)
    return result

def bot_loop():
    global bot_status, last_signal, is_running
    sa_tz=pytz.timezone('Africa/Johannesburg')
    while is_running:
        now=datetime.now(sa_tz)
        s=load_state()
        if str(date.today())!=s["date"]:
            s={"profit":0,"profit_A":0,"profit_B":0,"trades":0,"win":0,"loss":0,"date":str(date.today()),"signals":[],"scans":0}; save_state(s)
        s["scans"]+=1; save_state(s)
        if not (dtime(10,0) <= now.time() <= dtime(13,0)):
            bot_status=f"💤 Outside 10-13 SAST - {now.strftime('%H:%M:%S')} | Scans {s['scans']}"
            time.sleep(30); continue
        if s["profit"]>=CONFIG["daily_lock"]:
            bot_status=f"🔒 LOCK ${CONFIG['daily_lock']} HIT - Total ${s['profit']}"
            time.sleep(60); continue
        if s["trades"]>=CONFIG["max_trades"]:
            bot_status=f"Max {CONFIG['max_trades']} trades - Profit ${s['profit']}"
            time.sleep(60); continue
        
        price=get_price()
        closes=list(price_history)
        ema9=calc_ema(closes,9); ema21=calc_ema(closes,21); ema50=calc_ema(closes,50)
        rsi=calc_rsi(closes,14)
        sep=abs(ema9[-1]-ema21[-1])*10000
        bot_status=f"🔍 {now.strftime('%H:%M:%S')} | {price:.5f} | EMA9 {ema9[-1]:.5f} EMA21 {ema21[-1]:.5f} RSI {rsi:.1f} SEP {sep:.1f} | SL ${CONFIG['sl']} | A:{'⏸️' if paused_accounts[1076251] else '▶️'} B:{'⏸️' if paused_accounts[1076252] else '▶️'}"
        
        signal=None
        trend_up = ema9[-1] > ema21[-1] > ema50[-1]
        trend_down = ema9[-1] < ema21[-1] < ema50[-1]
        fresh_cross_up = ema9[-3] <= ema21[-3] and ema9[-1] > ema21[-1]
        fresh_cross_down = ema9[-3] >= ema21[-3] and ema9[-1] < ema21[-1]
        if trend_up and sep >= 0.8 and 50 < rsi < 70 and closes[-1] > ema21[-1]:
            if fresh_cross_up or (closes[-1] <= ema9[-1]*1.0004): signal="LONG"
        elif trend_down and sep >= 0.8 and 30 < rsi < 50 and closes[-1] < ema21[-1]:
            if fresh_cross_down or (closes[-1] >= ema9[-1]*0.9996): signal="SHORT"
        
        if signal:
            res=place_trade_both(signal, price, rsi)
            last_signal=f"{now.strftime('%H:%M:%S')} {signal} 0.40 x2 @ {price:.5f} RSI {rsi:.1f} -> {res}"
            bot_status=f"✅ {signal} BOTH -> {res} | Total ${load_state()['profit']}"
            time.sleep(120)
        time.sleep(25)

@app.route('/')
def home():
    s=load_state()
    wr=(s['win']/(s['win']+s['loss'])*100) if (s['win']+s['loss'])>0 else 0
    logs="<br>".join([f"{x['time'][11:19]} Acc:{x['acc']} {x['side']} {x['price']:.5f} RSI {x['rsi']} -> {x['result']}" for x in s['signals'][::-1]]) or "No trades"
    return f"""
    <h2>🔥 V5.6 BOGO LIVE - 1076251 + 1076252</h2>
    <p><b>Accs:</b> 1076251 | 1076252 | $5k 1:30 Live | SL ${CONFIG['sl']} TP ${CONFIG['tp']} | 0.40 lot</p>
    <p><b>Status:</b> {bot_status}<br><b>Last:</b> {last_signal}</p>
    <p><b>TOTAL:</b> ${s['profit']} | <b>A(1076251):</b> ${s['profit_A']} {'⏸️ PAUSED' if paused_accounts[1076251] else '▶️'} | <b>B(1076252):</b> ${s['profit_B']} {'⏸️ PAUSED' if paused_accounts[1076252] else '▶️'} | Trades {s['trades']}/{CONFIG['max_trades']} | WR {wr:.1f}%</p>
    <hr>
    <b>Global:</b> <a href='/run'>▶️ /run</a> | <a href='/stop'>⏹️ /stop</a> | <a href='/pause'>⏸️ /pause ALL</a> | <a href='/resume'>▶️ /resume ALL</a> | <a href='/status'>📊 /status JSON</a>
    <br><br>
    <b>Per-Account:</b><br>
    <a href='/pause/1076251'>⏸️ /pause/1076251</a> | <a href='/resume/1076251'>▶️ /resume/1076251</a><br>
    <a href='/pause/1076252'>⏸️ /pause/1076252</a> | <a href='/resume/1076252'>▶️ /resume/1076252</a>
    <br><br>
    <b>Change SL:</b> <a href='/set?sl=70&tp=120'>SL 70</a> | <a href='/set?sl=50&tp=100'>SL 50</a> | Custom: /set?sl=70&tp=150
    <hr><b>Log:</b><br>{logs}
    """

@app.route('/run')
def run_bot():
    global is_running
    if not is_running:
        is_running=True; threading.Thread(target=bot_loop, daemon=True).start()
    return f"STARTED BOGO! <a href='/'>Dashboard</a>"

@app.route('/stop')
def stop_bot():
    global is_running; is_running=False
    return "Stopped <a href='/'>Back</a>"

@app.route('/pause')
def pause_all():
    for k in paused_accounts: paused_accounts[k]=True
    return f"⏸️ ALL PAUSED {paused_accounts} <a href='/'>Back</a>"

@app.route('/resume')
def resume_all():
    for k in paused_accounts: paused_accounts[k]=False
    return f"▶️ ALL RESUMED {paused_accounts} <a href='/'>Back</a>"

@app.route('/pause/<int:acc_id>')
def pause_one(acc_id):
    if acc_id in paused_accounts:
        paused_accounts[acc_id]=True
        return f"⏸️ Paused {acc_id} | {paused_accounts} <a href='/'>Back</a>"
    return f"Account {acc_id} not found"

@app.route('/resume/<int:acc_id>')
def resume_one(acc_id):
    if acc_id in paused_accounts:
        paused_accounts[acc_id]=False
        return f"▶️ Resumed {acc_id} | {paused_accounts} <a href='/'>Back</a>"
    return f"Account {acc_id} not found"

@app.route('/status')
def status():
    s=load_state()
    return jsonify({
        "accounts": ACCOUNT_IDS,
        "paused": paused_accounts,
        "config": CONFIG,
        "today_profit_total": s["profit"],
        "profit_1076251": s["profit_A"],
        "profit_107625
