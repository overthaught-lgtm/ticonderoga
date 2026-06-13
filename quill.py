"""
Quill — TicoJitsu Ledger API
Ticonderoga Systems Holdings LLC
Railway deploy target
"""

import os
import sqlite3
import hashlib
import datetime
from flask import Flask, jsonify, request

app = Flask(__name__)

DB_PATH = os.environ.get("DB_PATH", "ticojitsu_ledger.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS wallets (
        wallet_id TEXT PRIMARY KEY,
        balance INTEGER NOT NULL DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS transactions (
        tx_id TEXT PRIMARY KEY,
        from_wallet TEXT,
        to_wallet TEXT,
        amount INTEGER,
        timestamp TEXT,
        tx_hash TEXT
    );
    """)
    # Seed genesis if empty
    row = conn.execute("SELECT COUNT(*) FROM wallets").fetchone()
    if row[0] == 0:
        genesis = {
            "INDYBLOC_MASTER_WALLET": 982500,
            "TICONDEROGA_EDGE_NODE_01": 0,
            "WALSENBURG_TERTIARY_NODE": 2500,
            "JSONS_WYLD_WALLET": 5000,
            "DAP_ENGINE_ESCROW": 10000,
        }
        for wallet, balance in genesis.items():
            conn.execute("INSERT INTO wallets VALUES (?,?)", (wallet, balance))
        conn.commit()
    conn.close()


# --- Routes ---

@app.route("/")
def index():
    return jsonify({"status": "Quill online", "version": "1.0.0"})


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/ledger", methods=["GET"])
def ledger():
    conn = get_db()
    rows = conn.execute(
        "SELECT wallet_id, balance FROM wallets ORDER BY balance DESC"
    ).fetchall()
    conn.close()
    return jsonify({row["wallet_id"]: row["balance"] for row in rows})


@app.route("/ledger/<wallet_id>", methods=["GET"])
def wallet_balance(wallet_id):
    conn = get_db()
    row = conn.execute(
        "SELECT balance FROM wallets WHERE wallet_id=?", (wallet_id,)
    ).fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "wallet not found"}), 404
    return jsonify({"wallet": wallet_id, "balance": row["balance"]})


@app.route("/transfer", methods=["POST"])
def transfer():
    api_key = request.headers.get("X-API-Key")
    if api_key != os.environ.get("QUILL_API_KEY", ""):
        return jsonify({"error": "unauthorized"}), 401

    data = request.get_json()
    src = data.get("from")
    dst = data.get("to")
    amt = int(data.get("amount", 0))

    if amt <= 0:
        return jsonify({"error": "invalid amount"}), 400

    conn = get_db()
    src_row = conn.execute(
        "SELECT balance FROM wallets WHERE wallet_id=?", (src,)
    ).fetchone()
    dst_row = conn.execute(
        "SELECT balance FROM wallets WHERE wallet_id=?", (dst,)
    ).fetchone()

    if not src_row or not dst_row:
        conn.close()
        return jsonify({"error": "wallet not found"}), 404
    if src_row["balance"] < amt:
        conn.close()
        return jsonify({"error": "insufficient balance"}), 400

    ts = datetime.datetime.now(datetime.UTC).isoformat()
    raw = f"{src}:{dst}:{amt}:{ts}"
    h = hashlib.sha256(raw.encode()).hexdigest()
    tx_id = f"TX_{h[:12].upper()}"

    conn.execute("UPDATE wallets SET balance=balance-? WHERE wallet_id=?", (amt, src))
    conn.execute("UPDATE wallets SET balance=balance+? WHERE wallet_id=?", (amt, dst))
    conn.execute(
        "INSERT OR IGNORE INTO transactions VALUES (?,?,?,?,?,?)",
        (tx_id, src, dst, amt, ts, h)
    )
    conn.commit()
    conn.close()

    return jsonify({
        "tx_id": tx_id,
        "from": src,
        "to": dst,
        "amount": amt,
        "timestamp": ts
    })


@app.route("/transactions", methods=["GET"])
def transactions():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM transactions ORDER BY timestamp DESC"
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
