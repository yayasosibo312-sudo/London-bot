import os, json, uuid
from flask import Flask, jsonify, request
import requests, websocket

app = Flask(__name__)

CLIENT_ID = "48840_6KzHyMBU89BK2oq2p5iBMjbTmY7PfPrGryc6fVbDIIJ8FuRb9f"
CLIENT_SECRET = "FkVUQHNIJOapabfMahuPsE3r09GYPiQKsixjJUqj63kTAZL6nO"
REDIRECT_URI = "https://london-bot-0ow9.onrender.com/callback"
HOST = "wss://live.ctraderapi.com:5036"

LIVE_TOKEN = {"access": None}

@app.route("/")
def home():
    return jsonify({"V": "V7.2 FINAL LIVE REAL SECRET", "ID": CLIENT_ID, "token": LIVE_TOKEN["access"] is not None})

@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return jsonify({"error": "no code"})
    r = requests.get("https://openapi.ctrader.com/apps/token",
        params={"grant_type": "authorization_code", "code": code,
                "redirect_uri": REDIRECT_URI,
                "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET}, timeout=20)
    try:
        data = r.json()
    except:
        return jsonify({"raw": r.text, "code": r.status_code})
    if "accessToken" in data:
        LIVE_TOKEN["access"] = data["accessToken"]
        return jsonify({"SUCCESS_LIVE_TOKEN_SAVED": True, "preview": data["accessToken"][:50], "full_data": data})
    return jsonify({"EXCHANGE_FAILED": data})

@app.route("/accounts")
def accounts():
    if not LIVE_TOKEN["access"]:
        return jsonify({"error": "No token - do auth first"})
    ws = websocket.create_connection(HOST, timeout=15)
    ws.send(json.dumps({"clientMsgId": str(uuid.uuid4()), "payloadType": 2100, "payload": {"clientId": CLIENT_ID, "clientSecret": CLIENT_SECRET}}))
    a1 = json.loads(ws.recv())
    if a1.get("payloadType") != 2101:
        ws.close()
        return jsonify({"APP_AUTH_FAIL": a1})
    ws.send(json.dumps({"clientMsgId": str(uuid.uuid4()), "payloadType": 2149, "payload": {"accessToken": LIVE_TOKEN["access"]}}))
    a2 = json.loads(ws.recv())
    ws.close()
    return jsonify({"LIVE_APP_AUTH": "OK 2101", "YOUR_PIPFARM_ACCOUNTS": a2})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
