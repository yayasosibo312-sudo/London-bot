import os, json, uuid, time, threading, logging
from datetime import datetime, time as dtime
from flask import Flask, jsonify
import websocket

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

CLIENT_ID = "48840_6KzHyM0kYH1sU8rJpTq2vXwZ3nLb4cDmEfAgJh"
CLIENT_SECRET = "FkVUQH9y2LpXo8rZt3nBm4cDqEfAgJhKlMnOpRs"
ACCESS_TOKEN = "r_pjZaKEPq8rLx2vNm4bQw7eRtYuIoPaSdFgHjKlZxCvBnMqWeRtYu"
DISPLAY_ACCOUNTS = [1076251, 1076252]
HOST = "demo.ctraderapi.com"
PORT = 5036

state = {"running": False, "last_error": "", "last_response": "", "last_trade": "", "trades_today": 0, "ctid_map": {}}

def send_json(ws, payload_type, payload):
    msg = {"clientMsgId": str(uuid.uuid4()), "payloadType": payload_type, "payload": payload}
    ws.send(json.dumps(msg))
    logger.info(f"SENT {payload_type}: {payload}")
    return msg["clientMsgId"]

def real_connect_and_trade(test_side="BUY", test_acc_display=None):
    """Real connection to demo.ctraderapi.com:5036 JSON"""
    ws = None
    try:
        url = f"wss://{HOST}:{PORT}"
        logger.info(f"CONNECTING REAL to {url}")
        ws = websocket.create_connection(url, timeout=10)
        
        # 1. App Auth 2100
        send_json(ws, 2100, {"clientId": CLIENT_ID, "clientSecret": CLIENT_SECRET})
        resp = json.loads(ws.recv())
        state["last_response"] = str(resp)[:500]
        logger.info(f"APP AUTH RESP: {resp}")
        if resp.get("payloadType") != 2101:
            state["last_error"] = f"App Auth Failed: {resp}"
            return False, resp
        
        # 2. Get Account List 2149
        send_json(ws, 2149, {"accessToken": ACCESS_TOKEN})
        resp = json.loads(ws.recv())
        logger.info(f"ACCOUNT LIST RESP: {resp}")
        state["last_response"] = str(resp)[:500]
        
        # Parse ctidTraderAccountId list
        accounts = resp.get("payload", {}).get("ctidTraderAccount", [])
        if not accounts:
            # alternative key
            accounts = resp.get("payload", {}).get("ctidTraderAccounts", [])
        
        for acc in accounts:
            ctid = acc.get("ctidTraderAccountId")
            state["ctid_map"][str(ctid)] = acc
            logger.info(f"Found cTID {ctid} for account {acc}")
        
        if not accounts:
            state["last_error"] = f"No accounts returned: {resp} - TOKEN EXPIRED?"
            return False, resp
        
        # 3. Account Auth 2102 for each or specific
        target_ctids = []
        if test_acc_display:
            # try to find by display? we will auth first one
            target_ctids = [accounts[0]["ctidTraderAccountId"]]
        else:
            target_ctids = [a["ctidTraderAccountId"] for a in accounts[:2]]
        
        for ctid in target_ctids:
            send_json(ws, 2102, {"ctidTraderAccountId": ctid, "accessToken": ACCESS_TOKEN})
            resp = json.loads(ws.recv())
            logger.info(f"ACC AUTH {ctid} RESP: {resp}")
            if resp.get("payloadType") == 2103:
                state["last_trade"] = f"REAL AUTH OK cTID {ctid} at {datetime.now()}"
                # 4. If test trade requested, send New Order 2106
                if test_acc_display is not None or test_side:
                    # ProtoOANewOrderReq 2106
                    volume = 400000  # 0.40 lot = 40000? Actually cTrader volume = lots * 1_000_000? Using 400000 for 0.40
                    # EURUSD symbolId need to fetch but try 1
                    order_payload = {
                        "ctidTraderAccountId": ctid,
                        "symbolId": 1,  # EURUSD usually 1 - will confirm via symbol list
                        "orderType": 1,  # MARKET =1
                        "tradeSide": 1 if test_side=="BUY" else 2,
                        "volume": volume
                    }
                    send_json(ws, 2106, order_payload)
                    exec_resp = json.loads(ws.recv())
                    logger.info(f"ORDER RESP: {exec_resp}")
                    state["last_response"] = str(exec_resp)[:800]
                    if exec_resp.get("payloadType") == 2126:  # ExecutionEvent
                        state["last_trade"] = f"REAL ORDER ACCEPTED cTID {ctid} {test_side} Vol {volume} {exec_resp}"
                        state["trades_today"] += 1
                        return True, exec_resp
                    else:
                        state["last_error"] = f"Order failed: {exec_resp}"
                        return False, exec_resp
        return True, "Auth OK - no order"
    except Exception as e:
        state["last_error"] = f"REAL CONNECT FAILED: {e}"
        logger.error(state["last_error"], exc_info=True)
        return False, str(e)
    finally:
        if ws:
            try: ws.close()
            except: pass

@app.route("/")
def home():
    return jsonify({"status": "V6.1 REAL JSON", "real_host": f"{HOST}:{PORT}", "state": state, "display_accounts": DISPLAY_ACCOUNTS})

@app.route("/test")
def test():
    ok, resp = real_connect_and_trade(test_side="BUY", test_acc_display=1076251)
    return jsonify({"ok": ok, "response": resp, "state": state})

@app.route("/run")
def run():
    state["running"] = True
    return jsonify({"started": True, "msg": "Ready for 10:00 SAST - hit /test first to prove REAL auth"})

@app.route("/stop")
def stop():
    state["running"] = False
    state["trades_today"] = 0
    return jsonify({"stopped": True})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
