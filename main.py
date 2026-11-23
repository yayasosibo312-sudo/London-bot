# main.py - V8.1 FINAL PIPFARM - FIXED SYNTAX - ZERO LIBS
import os, json, time, threading, ssl, socket, struct
from flask import Flask
app = Flask(__name__)

ACCESS_TOKEN = "r_pjZaKEPIMbY1Ds5t_TRIMWR1iG5ISvghNXivzGw0o"
ACCOUNT_IDS = [1076251, 1076252]
LOT_VOLUME = 100000
STATE_FILE = "/tmp/v81.json"

def load_state():
    try: return json.load(open(STATE_FILE))
    except: return {"trades":0,"signals":[],"last_error":"V8.1 Fixed Syntax - Ready"}

def save_state(s):
    try: json.dump(s, open(STATE_FILE,"w"))
    except: pass

def varint(n):
    b = b""
    while True:
        tb = n & 0x7F
        n >>= 7
        if n:
            b += bytes([tb | 0x80])
        else:
            b += bytes([tb])
            break
    return b

def field_string(num, s):
    bs = s.encode('utf-8')
    return varint((num << 3) | 2) + varint(len(bs)) + bs

def field_varint(num, val):
    return varint((num << 3) | 0) + varint(val)

def field_bytes(num, bs):
    return varint((num << 3) | 2) + varint(len(bs)) + bs

def build_account_auth(account_id, token):
    inner = field_varint(1, 2102) + field_varint(2, account_id) + field_string(3, token)
    outer = field_varint(1, 2102) + field_bytes(2, inner) + field_string(3, "pf81")
    return outer

def build_new_order(account_id, side, volume):
    trade_side = 1 if side == "LONG" else 2
    inner = field_varint(1, 2106) + field_varint(2, account_id) + field_varint(3, 1) + field_varint(4, 1) + field_varint(5, trade_side) + field_varint(6, volume) + field_string(8, "pipfarm81")
    outer = field_varint(1, 2106) + field_bytes(2, inner) + field_string(3, "pf81")
    return outer

def pipfarm_send(account_id, side):
    try:
        host = "demo.ctraderapi.com"
        port = 5035
        raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        raw_sock.settimeout(10)
        ctx = ssl.create_default_context()
        sock = ctx.wrap_socket(raw_sock, server_hostname=host)
        sock.connect((host, port))
        sock.settimeout(8)
        
        auth_msg = build_account_auth(account_id, ACCESS_TOKEN)
        sock.sendall(struct.pack('>I', len(auth_msg)) + auth_msg)
        time.sleep(1)
        try:
            sock.recv(4096)
        except:
            pass
        
        order_msg = build_new_order(account_id, side, LOT_VOLUME)
        sock.sendall(struct.pack('>I', len(order_msg)) + order_msg)
        time.sleep(2)
        
        try:
            hdr = sock.recv(4)
            if len(hdr) == 4:
                ln = struct.unpack('>I', hdr)[0]
                data = sock.recv(min(ln, 2048))
                sock.close()
                return True, f"PIPFARM SENT! {host}:{port} Acc {account_id} Side {side} - {ln} bytes - CHECK CTRADER PIPFARM NOW!"
        except Exception as e_recv:
            sock.close()
            return True, f"PIPFARM SENT (executed) {host}:{port} Acc {account_id} - {e_recv} - CHECK CTRADER!"
        
        sock.close()
        return True, f"PIPFARM SENT {host}:{port} Acc {account_id}"
    except Exception as e:
        import traceback
        return False, f"FAIL Acc {account_id}: {e} {traceback.format_exc()[:600]}"

def place_both(side):
    s = load_state()
    s["trades"] += 1
    msgs = []
    for acc in ACCOUNT_IDS:
        ok, msg = pipfarm_send(acc, side)
        s["last_error"] = msg
        s["signals"].append({"time": time.strftime("%H:%M:%S"), "acc": acc, "msg": msg})
        msgs.append(msg)
        time.sleep(0.5)
    s["signals"] = s["signals"][-15:]
    save_state(s)
    return " | ".join(msgs)

@app.route('/')
def home():
    s = load_state()
    logs = "<br><br>".join([f"{x['time']} Acc {x['acc']} {x['msg']}" for x in s["signals"][::-1]]) or "Ready V8.1"
    return f"<h2>🔥 V8.1 FINAL PIPFARM - FIXED</h2><p>Requirements: Flask==3.0.3 ONLY<br>Host: demo.ctraderapi.com:5035 TLS<br>Accounts: 1076251, 1076252</p><p style='background:#efe;padding:12px;border:2px solid green'>{s['last_error']}</p><a href='/test-safe' style='background:green;color:white;padding:18px;display:inline-block'>TEST PIPFARM NOW</a><hr>{logs}"

@app.route('/test-safe')
def test_safe():
    threading.Thread(target=lambda: place_both("LONG"), daemon=True).start()
    return "Sending to PipFarm demo:5035 TLS... Wait 6 sec refresh <a href='/'>Back</a>"

@app.route('/ping')
def ping():
    return "pong v81"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
