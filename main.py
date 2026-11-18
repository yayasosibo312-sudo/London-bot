import os
import threading
import time
from flask import Flask
from datetime import datetime

# cTrader imports
from ctrader_open_api import Client, EndPoints
from ctrader_open_api.messages.OpenApiCommonMessages_pb2 import *
from ctrader_open_api.messages.OpenApiMessages_pb2 import *
from twisted.internet import reactor

# --- CONFIG - PUT YOUR DETAILS HERE ---
CLIENT_ID = os.getenv("CTRADER_CLIENT_ID", "YOUR_CLIENT_ID")
CLIENT_SECRET = os.getenv("CTRADER_CLIENT_SECRET", "YOUR_CLIENT_SECRET")
ACCESS_TOKEN = os.getenv("CTRADER_ACCESS_TOKEN", "YOUR_TOKEN")
ACCOUNT_ID = int(os.getenv("CTRADER_ACCOUNT_ID", "0"))  # your cTrader account ID

SYMBOL_ID = 1  # 1 = EURUSD, 2 = GBPUSD - change if needed
LOT_SIZE = 0.40
# ----------------------------------------

app = Flask('')
bot_status = "IDLE - Not running"
last_action = "None"

@app.route('/')
def home():
    return f"""
    <h2>London Bot ALIVE - Phone OFF OK</h2>
    <p>Status: {bot_status}</p>
    <p>Last: {last_action}</p>
    <p>Time: {datetime.now()}</p>
    <a href='/run'>/run - Start Bot</a><br>
    <a href='/stop'>/stop - Stop Bot</a><br>
    <a href='/status'>/status - JSON status</a>
    """

@app.route('/run')
def run_bot_endpoint():
    global bot_status
    bot_status = "STARTED - Connecting to cTrader"
    threading.Thread(target=start_ctrader_logic, daemon=True).start()
    return f"Bot STARTED - {LOT_SIZE} lot - Phone can be OFF now. <a href='/'>back</a>"

@app.route('/stop')
def stop_bot_endpoint():
    global bot_status
    bot_status = "STOPPED by user"
    return "Bot STOPPED <a href='/'>back</a>"

@app.route('/status')
def status():
    return {"status": bot_status, "last": last_action, "lot": LOT_SIZE, "time": str(datetime.now())}

def start_ctrader_logic():
    global bot_status, last_action
    try:
        # --- YOUR LONDON BREAKOUT LOGIC HERE ---
        # This is the skeleton - connect to cTrader
        client = Client(EndPoints.PROTOBUF_LIVE_HOST, EndPoints.PROTOBUF_LIVE_PORT, Client.TCP)
        # For demo use: EndPoints.PROTOBUF_DEMO_HOST
        bot_status = "Connected - Waiting for London 10:00 SAST"
        last_action = f"Connected account {ACCOUNT_ID} - Lot {LOT_SIZE}"
        
        # TODO: Add your high/low breakout detection here
        # Example: place order
        # client.send(ProtoOAOrder...)
        
        # Keep alive
        while True:
            time.sleep(60)
            
    except Exception as e:
        bot_status = f"ERROR: {e}"
        last_action = str(e)

# Run Flask (keeps Render awake)
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
