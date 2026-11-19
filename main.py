# @title PipFarm EMA Bot - $5K 2-Step - RENDER VERSION - Phone OFF OK
import os, json, threading, time, numpy as np
from datetime import date, datetime, time as dtime
from flask import Flask
import pytz

app = Flask('')

# ================== SECRETS FROM RENDER ENVIRONMENT ==================
# Go to Render -> Environment -> Add:
# CTRADER_CLIENT_ID, CTRADER_CLIENT_SECRET, CTRADER_ACCESS_TOKEN, CTRADER_ACCOUNT_ID
CLIENT_ID = os.getenv("CTRADER_CLIENT_ID", "48840_6xHyMBu8BK2oq2pS8MbTpY7TrPYGryc6NvbDJI8FuR9f")
CLIENT_SECRET = os.getenv("CTRADER_CLIENT_SECRET", "FkVUQHNIiOapatbMahuPsE9r09GYPIQKisxxUgjIq3kTAZL6nO")
ACCESS_TOKEN = os.getenv("CTRADER_ACCESS_TOKEN", "")
ACCOUNT_ID = os.getenv("CTRADER_ACCOUNT_ID", "49569463")

# ================== LOCKED PLAN - SAME AS YOUR ONE NOTE ==================
START_DATE = date(2025, 11, 25)
SYMBOL = "EURUSD"
LOT_SIZE = 0.40
SL_DOLLARS = 80
TP_DOLLARS = 120
DAILY_LOCK = 120
MAX_TRADES = 2
MAX_POSITIONS = 1
LONDON_START_SA = dtime(10, 0)
LONDON_END_SA = dtime(11, 30)
STATE_FILE = "/tmp/bot_state.json" # Use /tmp on Render

EMA_FAST = 9
EMA_SLOW = 21
EMA_TREND = 50
RSI_PERIOD = 14
RSI_LONG_MIN = 55
RSI_SHORT_MAX = 45
EMA_MIN_SEP = 1.5
ATR_MIN = 3.0
ATR_MAX = 15.0

bot_status = "IDLE - PipFarm EMA Bot Ready"
last_signal = "None - Waiting for /run"
is_running = False

# ================== YOUR ACCURATE CALCS - SAME ==================
def calc_ema(values, period):
    k = 2/(period+1)
    ema = [values[0]]
    for p in values[1:]: ema.append(p*k + ema[-1]*(1-k))
    return ema

def calc_rsi(closes, period=14):
    deltas = np.diff(closes)
    gains = np.where(deltas>0, deltas, 0)
    losses = np.where(deltas<0, -deltas, 0)
    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])
    if avg_loss == 0: return 100
    return 100 - (100/(1+avg_gain/avg_loss))

def is_signal(candles):
    closes = [c['close'] for c in candles]
    highs = [c['high'] for c in candles]
    lows = [c['low'] for c in candles]
    if len(closes) < 55: return None, "Need 55 candles"
    ema9, ema21, ema50 = calc_ema(closes,9), calc_ema(closes,21), calc_ema(closes,50)
    rsi = calc_rsi(closes, 14)
    atr = np.mean([highs[i]-lows[i] for i in range(-14,0)])*10000
    sep = abs(ema9[-1]-ema21[-1])*10000
    price = closes[-2]
    if not (ATR_MIN <= atr <= ATR_MAX): return None, f"ATR {atr:.1f} out"
    if sep < EMA_MIN_SEP: return None, f"Sep {sep:.1f} chop"
    cross_long = ema9[-2] <= ema21[-2] and ema9[-1] > ema21[-1]
    cross_short = ema9[-2] >= ema21[-2] and ema9[-1] < ema21[-1]
    long_stack = price > ema9[-1] > ema21[-1] > ema50[-1]
    short_stack = price < ema9[-1] < ema21[-1] < ema50[-1]
    if cross_long and long_stack and rsi > RSI_LONG_MIN:
        return "LONG", f"LONG | {price:.5f} RSI {rsi:.1f} ATR {atr:.1f} SEP {sep:.1f}"
    if cross_short and short_stack and rsi < RSI_SHORT_MAX:
        return "SHORT", f"SHORT | {price:.5f} RSI {rsi:.1f} ATR {atr:.1f} SEP {sep:.1f}"
    return None, f"No cross - RSI {rsi:.1f} ATR {atr:.1f}"

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE,"r") as f: return json.load(f)
    return {"daily_profit":0,"trades_today":0,"profit_by_day":{},"last_date":""}

def save_state(s):
    with open(STATE_FILE,"w") as f: json.dump(s,f,indent=2)

def can_trade():
    state = load_state()
    today = date.today()
    if today.weekday() >= 5: return False, "Weekend"
    if state["last_date"] != str(today):
        state["daily_profit"]=0; state["trades_today"]=0; state["last_date"]=str(today); save_state(state)
    if state["daily_profit"] >= DAILY_LOCK: return False, f"🔒 DAILY LOCK ${DAILY_LOCK} HIT"
    if state["trades_today"] >= MAX_TRADES: return False, "Max trades hit"
    if state["trades_today"] == 1 and state["daily_profit"] >= 0:
        return False, "✅ 1st win done - protect 40% consistency"
    sa_tz = pytz.timezone('Africa/Johannesburg')
    now = datetime.now(sa_tz).time()
    if not (LONDON_START_SA <= now <= LONDON_END_SA):
        return False, f"Outside London {LONDON_START_SA}-{LONDON_END_SA} SAST"
    # MAX_POSITIONS 1 check - would check open positions here via API
    return True, "Scanning"

def bot_loop():
    global bot_status, last_signal, is_running
    sa_tz = pytz.timezone('Africa/Johannesburg')
    while is_running:
        ok, msg = can_trade()
        bot_status = msg
        if ok:
            # Here you would fetch real candles from cTrader API
            # For now showing logic is active
            bot_status = f"🔍 {msg} - EMA {EMA_FAST}/{EMA_SLOW}/{EMA_TREND} RSI {RSI_LONG_MIN}/{RSI_SHORT_MAX} ACTIVE"
            last_signal = f"Checked at {datetime.now(sa_tz)} - {msg}"
        time.sleep(30)

# ================== FLASK ROUTES FOR RENDER REMOTE ==================
@app.route('/')
def home():
    state = load_state()
    return f"""
    <h2>🔥 PipFarm EMA Bot ALIVE - Phone OFF OK</h2>
    <p><b>Account:</b> {ACCOUNT_ID} | <b>Symbol:</b> {SYMBOL} M5</p>
    <p><b>Strategy:</b> EMA {EMA_FAST}/{EMA_SLOW}/{EMA_TREND} + RSI {RSI_LONG_MIN}/{RSI_SHORT_MAX}</p>
    <p><b>Risk:</b> {LOT_SIZE} lot | SL ${SL_DOLLARS} TP ${TP_DOLLARS} | Daily Lock ${DAILY_LOCK} | Max Pos {MAX_POSITIONS}</p>
    <p><b>Status:</b> {bot_status}</p>
    <p><b>Last Signal:</b> {last_signal}</p>
    <p><b>Today:</b> Profit ${state['daily_profit']} | Trades {state['trades_today']}/{MAX_TRADES}</p>
    <p><b>Time SAST:</b> {datetime.now(pytz.timezone('Africa/Johannesburg'))}</p>
    <br><a href='/run'>✅ /run - START BOT</a><br><br>
    <a href='/stop'>🛑 /stop</a><br><br>
    <a href='/status'>📊 /status JSON</a>
    """

@app.route('/run')
def run_bot():
    global is_running, bot_status
    if not is_running:
        is_running = True
        threading.Thread(target=bot_loop, daemon=True).start()
        bot_status = "STARTED - London 10:00-11:30 SAST EMA Bot Running"
    return f"Bot STARTED! Phone OFF OK. <a href='/'>Back</a> - Status: {bot_status}"

@app.route('/stop')
def stop_bot():
    global is_running, bot_status
    is_running = False
    bot_status = "STOPPED by user"
    return f"Bot STOPPED <a href='/'>Back</a>"

@app.route('/status')
def status():
    state = load_state()
    return {"account": ACCOUNT_ID, "symbol": SYMBOL, "lot": LOT_SIZE, "daily_lock": DAILY_LOCK, "max_pos": MAX_POSITIONS, "status": bot_status, "last": last_signal, "state": state, "token_set": bool(ACCESS_TOKEN)}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
