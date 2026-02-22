import os
import time
import uuid
import datetime
import psycopg2
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")

def db():
    return psycopg2.connect(DATABASE_URL)

def now():
    return int(time.time())

# =========================
# CREATE FREE KEY (1 IP / day)
# =========================
@app.route("/get-free", methods=["POST"])
def get_free():

    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    today = datetime.date.today()

    conn = db()
    cur = conn.cursor()

    # Check daily claim
    cur.execute(
        "SELECT * FROM daily_claims WHERE ip=%s AND claim_date=%s",
        (ip, today)
    )
    if cur.fetchone():
        conn.close()
        return jsonify({"status":"already_claimed_today"})

    key = "FREE-" + str(uuid.uuid4())[:8]

    expire = int(datetime.datetime.combine(
        today + datetime.timedelta(days=1),
        datetime.time.min
    ).timestamp())

    cur.execute(
        "INSERT INTO licenses (key,type,ip,expire) VALUES (%s,%s,%s,%s)",
        (key,"FREE",ip,expire)
    )

    cur.execute(
        "INSERT INTO daily_claims (ip,claim_date) VALUES (%s,%s)",
        (ip,today)
    )

    conn.commit()
    conn.close()

    return jsonify({
        "status":"success",
        "key":key,
        "expire":expire
    })

# =========================
# VERIFY KEY
# =========================
@app.route("/verify", methods=["POST"])
def verify():

    data = request.json
    key = data.get("key")
    hwid = data.get("hwid")

    conn = db()
    cur = conn.cursor()

    cur.execute(
        "SELECT type,hwid,expire FROM licenses WHERE key=%s",
        (key,)
    )

    row = cur.fetchone()

    if not row:
        conn.close()
        return jsonify({"status":"invalid_key"})

    type_, saved_hwid, expire = row

    if now() > expire:
        conn.close()
        return jsonify({"status":"expired"})

    # Bind HWID first time
    if saved_hwid is None:
        cur.execute(
            "UPDATE licenses SET hwid=%s WHERE key=%s",
            (hwid,key)
        )
        conn.commit()
    elif saved_hwid != hwid:
        conn.close()
        return jsonify({"status":"hwid_mismatch"})

    conn.close()

    return jsonify({
        "status":"valid",
        "type":type_,
        "expire":expire
    })

# =========================
# CREATE VIP KEY (Admin only demo)
# =========================
@app.route("/create-vip", methods=["POST"])
def create_vip():

    data = request.json
    days = int(data.get("days",30))

    key = "VIP-" + str(uuid.uuid4())[:10]
    expire = now() + (days * 86400)

    conn = db()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO licenses (key,type,expire) VALUES (%s,%s,%s)",
        (key,"VIP",expire)
    )

    conn.commit()
    conn.close()

    return jsonify({
        "status":"vip_created",
        "key":key,
        "expire":expire
    })

# =========================
# ADMIN DASHBOARD
# =========================
@app.route("/admin")
def admin():

    conn = db()
    cur = conn.cursor()

    cur.execute("SELECT key,type,expire FROM licenses ORDER BY id DESC")
    keys = cur.fetchall()

    conn.close()

    return render_template("admin.html", keys=keys)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)