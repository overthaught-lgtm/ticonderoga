from http.server import BaseHTTPRequestHandler
import json, sqlite3, hashlib
from datetime import datetime

DB = "/tmp/tj.db"
MASTER = "0x0432f766C6de3ac043721B0D38a500F3Af48c598"
KEY = "az9j80-5891"

def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.execute("""CREATE TABLE IF NOT EXISTS wallets(
        wallet_id TEXT PRIMARY KEY, balance REAL DEFAULT 0)""")
    c.execute("""CREATE TABLE IF NOT EXISTS transactions(
        tx_id TEXT PRIMARY KEY, from_wallet TEXT,
        to_wallet TEXT, amount REAL, tx_hash TEXT,
        timestamp TEXT)""")
    c.commit()
    return c

def thash(d):
    return hashlib.sha256(
        json.dumps(d,sort_keys=True).encode()).hexdigest()

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.headers.get("X-API-Key") != KEY:
            return self._out(401,{"error":"unauthorized"})
        p = self.path.split("?")[0]
        conn = db()
        if p == "/api/ledger":
            rows = conn.execute(
                "SELECT * FROM transactions ORDER BY timestamp DESC"
            ).fetchall()
            self._out(200,[dict(r) for r in rows])
        elif p.startswith("/api/balance/"):
            wid = p.split("/api/balance/")[1]
            row = conn.execute(
                "SELECT balance FROM wallets WHERE wallet_id=?",(wid,)
            ).fetchone()
            if row: self._out(200,{"wallet_id":wid,"balance":row[0]})
            else: self._out(404,{"error":"not found"})
        else:
            self._out(404,{"error":"route not found"})
        conn.close()

    def do_POST(self):
        if self.headers.get("X-API-Key") != KEY:
            return self._out(401,{"error":"unauthorized"})
        length = int(self.headers.get("Content-Length",0))
        data = json.loads(self.rfile.read(length))
        p = self.path.split("?")[0]
        conn = db()
        if p == "/api/transfer":
            fw = data.get("from_wallet")
            tw = data.get("to_wallet")
            amt = float(data.get("amount",0))
            row = conn.execute(
                "SELECT balance FROM wallets WHERE wallet_id=?",(fw,)
            ).fetchone()
            if not row:
                return self._out(404,{"error":"sender not found"})
            if row[0] < amt:
                return self._out(402,{"error":"insufficient funds"})
            conn.execute(
                "UPDATE wallets SET balance=balance-? WHERE wallet_id=?",(amt,fw))
            conn.execute("""INSERT INTO wallets(wallet_id,balance) VALUES(?,?)
                ON CONFLICT(wallet_id) DO UPDATE SET balance=balance+?""",
                (tw,amt,amt))
            ts = datetime.now().isoformat()
            h = thash({"from":fw,"to":tw,"amount":amt,"ts":ts})
            tid = "TX_"+h[:8].upper()
            conn.execute(
                "INSERT INTO transactions VALUES(?,?,?,?,?,?)",
                (tid,fw,tw,amt,h,ts))
            conn.commit(); conn.close()
            self._out(200,{"status":"ok","tx_id":tid,"teakwood":h})
        elif p == "/api/mint":
            if data.get("from_wallet") != MASTER:
                return self._out(403,{"error":"master only"})
            tw = data.get("to_wallet")
            amt = float(data.get("amount",0))
            conn.execute("""INSERT INTO wallets(wallet_id,balance) VALUES(?,?)
                ON CONFLICT(wallet_id) DO UPDATE SET balance=balance+?""",
                (tw,amt,amt))
            ts = datetime.now().isoformat()
            h = thash({"mint":True,"to":tw,"amount":amt,"ts":ts})
            tid = "TX_"+h[:8].upper()
            conn.execute(
                "INSERT INTO transactions VALUES(?,?,?,?,?,?)",
                (tid,MASTER,tw,amt,h,ts))
            conn.commit(); conn.close()
            self._out(200,{"status":"minted","tx_id":tid,"teakwood":h})
        else:
            self._out(404,{"error":"route not found"})

    def _out(self,code,data):
        self.send_response(code)
        self.send_header("Content-Type","application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
