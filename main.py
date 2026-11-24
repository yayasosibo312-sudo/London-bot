import os, json, uuid, logging
from flask import Flask, jsonify, request
import requests, websocket

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

CLIENT_ID = "48840_6KzHyM0kYH1sU8rJpTq2vXwZ3nLb4cDmEfAgJh"
CLIENT_SECRET = "FkVUQH9y2LpXo8rZt3nBm4cDqEfAgJhKlMnOpRs"
REDIRECT_URI = "https://london-bot-0ow9.onrender.com/callback"
HOST = "wss://live.ctraderapi.com:5036"

LIVE_TOKEN = {"access": None, "accounts": []}

@app.route("/")
def home():
    return jsonify({"status": "V7 LIVE", "client_id": CLIENT_ID, "host": HOST, "live_token_set": LIVE_TOKEN["access"] is not None, "accounts": LIVE_TOKEN["accounts"]})

@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return jsonify({"error": "no code", "url": request.url})
    # Exchange code for accessToken
    try:
        r = requests.get("https://openapi.ctrader.com/apps/token",
            params={"grant_type": "authorization_code", "code": code,
                    "redirect_uri": REDIRECT_URI,
                    "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET}, timeout=20)
        data = r.json()
        # data has accessToken
        if "accessToken" in data:
            LIVE_TOKEN["access"] = data["accessToken"]
            return jsonify({"SUCCESS": "LIVE TOKEN SAVED", "token": data["accessToken"][:30]+"...", "full": data, "next": "Go to /accounts to see PipFarm Live accounts"})
        return jsonify(data)
    except Exception as e:
        return jsonify({"exchange_error": str(e), "code": code})

@app.route("/accounts")
def accounts():
    if not LIVE_TOKEN["access"]:
        return jsonify({"error": "No LIVE_TOKEN - go to /callback first", "hint": "Use auth link"})
    try:
        ws = websocket.create_connection(HOST, timeout=10)
        ws.send(json.dumps({"clientMsgId": str(uuid.uuid4()), "payloadType": 2100, "payload": {"clientId": CLIENT_ID, "clientSecret": CLIENT_SECRET}}))
        app_auth = json.loads(ws.recv())
        if app_auth.get("payloadType") != 2101:
            return jsonify({"error": "APP AUTH FAILED", "resp": app_auth})
        ws.send(json.dumps({"clientMsgId": str(uuid.uuid4()), "payloadType": 2149, "payload": {"accessToken": LIVE_TOKEN["access"]}}))
        acc_resp = json.loads(ws.recv())
        LIVE_TOKEN["accounts"] = acc_resp
        ws.close()
        return jsonify({"APP_AUTH": "OK 2101", "ACCOUNTS_RESPONSE": acc_resp, "YOUR_LIVE_ACCOUNTS": "Should show 1076251 and 1076252 here"})
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
