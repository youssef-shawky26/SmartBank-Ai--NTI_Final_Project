import random
import secrets
from functools import wraps
from datetime import datetime, timezone

from flask import Flask, request, session, jsonify, render_template, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash

import db
import seed
import models

app = Flask(__name__)
app.secret_key = "verdict-bank-demo-secret-key-change-me"

MANAGER_ACCESS_CODE = "VERDICT-STAFF-2026"

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------
db.init_db()
seed.seed_if_empty()

# ---------------------------------------------------------------------------
# Helpers / Decorators
# ---------------------------------------------------------------------------
def login_required(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        if "user_id" not in session:
            return jsonify({"error": "not authenticated"}), 401
        return fn(*a, **kw)
    return wrapper

def role_required(role):
    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            if "user_id" not in session:
                return jsonify({"error": "not authenticated"}), 401
            if session.get("role") != role:
                return jsonify({"error": "forbidden"}), 403
            return fn(*a, **kw)
        return wrapper
    return deco

def current_user_row():
    conn = db.get_db()
    row = conn.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    conn.close()
    return row

def user_public(row):
    if not row:
        return {}
    return {
        "id": row["id"], "username": row["username"], "role": row["role"],
        "full_name": row["full_name"], "age": row["age"], "gender": row["gender"],
        "phone": row["phone"], "email": row["email"], "state": row["state"], "job": row["job"],
        "account_number": row["account_number"], "balance": float(row["balance"] or 0.0), "income": row["income"],
        "employment_years": row["employment_years"], "home_ownership": row["home_ownership"],
        "credit_score": row["credit_score"], "credit_history_years": row["credit_history_years"],
        "has_prior_default": row["has_prior_default"], "geography": row["geography"],
        "tenure_years": row["tenure_years"], "num_of_products": row["num_of_products"],
    }

def gen_account_number(conn):
    """Generates a random account number and ensures it does not exist in the database."""
    while True:
        part1 = secrets.randbelow(9000) + 1000
        part2 = secrets.randbelow(9000) + 1000
        acc_num = f"AUR-{part1}-{part2}"
        existing = conn.execute("SELECT id FROM users WHERE account_number=?", (acc_num,)).fetchone()
        if not existing:
            return acc_num

# ---------------------------------------------------------------------------
# Page routes
# ---------------------------------------------------------------------------
@app.route("/")
def welcome():
    if "user_id" in session:
        return redirect(url_for("client_home") if session["role"] == "client" else url_for("manager_home"))
    return render_template("welcome.html")

@app.route("/app")
def client_home():
    if "user_id" not in session or session["role"] != "client":
        return redirect(url_for("welcome"))
    return render_template("client.html")

@app.route("/manager")
def manager_home():
    if "user_id" not in session or session["role"] != "manager":
        return redirect(url_for("welcome"))
    return render_template("manager.html")

# ---------------------------------------------------------------------------
# Auth API
# ---------------------------------------------------------------------------
@app.route("/api/auth/register", methods=["POST"])
def register():
    d = request.get_json(force=True)
    role = d.get("role", "client")
    if role == "manager" and d.get("access_code") != MANAGER_ACCESS_CODE:
        return jsonify({"error": "Invalid staff access code."}), 400

    conn = db.get_db()
    try:
        username = (d.get("username") or "").strip()
        full_name = (d.get("full_name") or "").strip()
        password = d.get("password")

        if not username or not password or not full_name:
            return jsonify({"error": "Username, password and full name are required."}), 400

        existing = conn.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
        if existing:
            return jsonify({"error": "That username is already taken."}), 400

        def _num(key, default=None):
            v = d.get(key)
            if v is None or v == "":
                return default
            try:
                return float(v) if key in ("income", "balance") else int(float(v))
            except (TypeError, ValueError):
                return default

        balance_val = _num("balance", 0.0) if role == "client" else 0.0
        income_val = _num("income", 65000.0)
        credit_score_val = _num("credit_score", 680)
        cred_hist = _num("credit_history_years", 4)
        emp_exp = _num("employment_years", 3)
        age_val = _num("age", 28)
        account_number = gen_account_number(conn)

        conn.execute(
            """INSERT INTO users (username, password_hash, role, full_name, age, gender, phone, email,
               state, job, account_number, balance, income, employment_years, home_ownership,
               credit_score, credit_history_years, has_prior_default, geography, tenure_years,
               num_of_products, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (username, generate_password_hash(password), role, full_name,
             age_val, d.get("gender", "female"), d.get("phone", ""), d.get("email", ""),
             d.get("state", "NY"), d.get("job", "Professional"), account_number,
             balance_val, income_val, emp_exp, d.get("home_ownership", "RENT"),
             credit_score_val, cred_hist, d.get("has_prior_default", "No"),
             d.get("geography", "France"), _num("tenure_years", 2), _num("num_of_products", 1),
             db.now()),
        )
        conn.commit()
        user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    finally:
        conn.close()

    session["user_id"] = user["id"]
    session["role"] = user["role"]
    return jsonify({"user": user_public(user)})

@app.route("/api/auth/login", methods=["POST"])
def login():
    d = request.get_json(force=True)
    conn = db.get_db()
    try:
        user = conn.execute("SELECT * FROM users WHERE username=?", (d.get("username", "").strip(),)).fetchone()
    finally:
        conn.close()

    if not user or not check_password_hash(user["password_hash"], d.get("password", "")):
        return jsonify({"error": "Incorrect username or password."}), 401
    if d.get("role") and d["role"] != user["role"]:
        return jsonify({"error": f"This account is registered as a {user['role']}, not a {d['role']}."}), 400

    session["user_id"] = user["id"]
    session["role"] = user["role"]
    return jsonify({"user": user_public(user)})

@app.route("/api/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"ok": True})

@app.route("/api/auth/me")
@login_required
def me():
    return jsonify({"user": user_public(current_user_row())})

# ---------------------------------------------------------------------------
# Account API
# ---------------------------------------------------------------------------
@app.route("/api/account", methods=["GET", "PUT"])
@login_required
def account():
    conn = db.get_db()
    try:
        if request.method == "GET":
            row = conn.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
            return jsonify({"user": user_public(row)})

        d = request.get_json(force=True)
        editable = ["full_name", "age", "gender", "phone", "email", "state", "job", "income",
                    "employment_years", "home_ownership", "credit_score", "credit_history_years",
                    "has_prior_default", "geography", "tenure_years", "num_of_products", "balance"]
        fields, values = [], []
        for k in editable:
            if k in d:
                val = d[k]
                if k in ("income", "balance"):
                    try:
                        val = float(val)
                    except (TypeError, ValueError):
                        continue
                fields.append(f"{k}=?")
                values.append(val)
        if fields:
            values.append(session["user_id"])
            conn.execute(f"UPDATE users SET {', '.join(fields)} WHERE id=?", values)
            conn.commit()
        row = conn.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
        return jsonify({"user": user_public(row)})
    finally:
        conn.close()

# ---------------------------------------------------------------------------
# Loan Flow
# ---------------------------------------------------------------------------
def build_loan_features(user_row, amount, intent, interest_rate, overrides=None):
    overrides = overrides or {}
    income = float(user_row["income"] or 65000.0)
    return {
        "person_gender": overrides.get("gender") or user_row["gender"] or "female",
        "person_education": overrides.get("education") or "Bachelor",
        "person_home_ownership": overrides.get("home_ownership") or user_row["home_ownership"] or "RENT",
        "loan_intent": intent,
        "previous_loan_defaults_on_file": overrides.get("prior_default") or user_row["has_prior_default"] or "No",
        "person_age": int(user_row["age"] or 28),
        "person_income": income,
        "person_emp_exp": int(user_row["employment_years"] or 4),
        "loan_amnt": float(amount),
        "loan_int_rate": float(interest_rate),
        "loan_percent_income": round(float(amount) / max(income, 1.0), 4),
        "cb_person_cred_hist_length": int(user_row["credit_history_years"] or 4),
        "credit_score": int(user_row["credit_score"] or 680),
    }

@app.route("/api/loans", methods=["GET", "POST"])
@login_required
@role_required("client")
def loans():
    conn = db.get_db()
    try:
        if request.method == "GET":
            rows = conn.execute(
                "SELECT * FROM loans WHERE user_id=? ORDER BY created_at DESC", (session["user_id"],)
            ).fetchall()
            return jsonify({"loans": [dict(r) for r in rows]})

        d = request.get_json(force=True)
        user_row = current_user_row()
        amount = float(d["amount"])
        intent = d["intent"]
        interest_rate = float(d.get("interest_rate", 9.9))
        overrides = {
            "gender": d.get("gender"), "education": d.get("education"),
            "home_ownership": d.get("home_ownership"), "prior_default": d.get("prior_default"),
        }
        feats = build_loan_features(user_row, amount, intent, interest_rate, overrides)
        result = models.predict_loan(feats)

        conn.execute(
            """INSERT INTO loans (user_id, amount, intent, interest_rate, percent_income,
               applicant_gender, applicant_education, applicant_home_ownership, applicant_prior_default,
               status, model_probability, model_recommend, model_reasons, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (session["user_id"], amount, intent, interest_rate, feats["loan_percent_income"],
             feats["person_gender"], feats["person_education"], feats["person_home_ownership"],
             feats["previous_loan_defaults_on_file"],
             "pending", result["probability"], int(result["approved"]), "; ".join(result["reasons"]), db.now()),
        )
        conn.commit()
        return jsonify({"submitted": True, "preliminary_assessment": result})
    finally:
        conn.close()

# ---------------------------------------------------------------------------
# Transactions Flow (Balance Check + Real-Time Fraud Interception)
# ---------------------------------------------------------------------------
@app.route("/api/transactions", methods=["GET", "POST"])
@login_required
@role_required("client")
def transactions():
    conn = db.get_db()
    try:
        if request.method == "GET":
            rows = conn.execute(
                "SELECT * FROM transactions WHERE sender_id=? ORDER BY created_at DESC", (session["user_id"],)
            ).fetchall()
            return jsonify({"transactions": [dict(r) for r in rows]})

        d = request.get_json(force=True)
        user_row = current_user_row()
        amount = float(d["amount"])
        receiver_account = d["receiver_account"].strip()
        merchant = d.get("merchant", "Peer Transfer").strip() or "Peer Transfer"
        category = d.get("category", "misc_pos")

        if amount <= 0:
            return jsonify({"error": "Amount must be greater than zero."}), 400
        if amount > float(user_row["balance"] or 0.0):
            return jsonify({"error": "Insufficient balance."}), 400

        prior = conn.execute(
            "SELECT AVG(amount) as a FROM transactions WHERE sender_id=? AND status IN ('cleared','manager_approved')",
            (session["user_id"],),
        ).fetchone()
        avg_amt = prior["a"] if prior and prior["a"] else None

        # --- FIX IS HERE: Parse frontend overrides, fallback to current time if blank ---
        now_dt = datetime.now(timezone.utc)

        def get_time_val(key, default_val):
            val = d.get(key)
            if val is not None and str(val).strip() != "":
                return int(float(val))
            return default_val

        # Using exact keys sent by client.js: trans_hour, trans_day, trans_month
        trans_hour = get_time_val("trans_hour", now_dt.hour)
        trans_day = get_time_val("trans_day", now_dt.day)
        trans_month = get_time_val("trans_month", now_dt.month)
        
        # Estimate day of week so it matches the simulated date
        try:
            trans_dow = datetime(now_dt.year, trans_month, trans_day).weekday()
        except ValueError:
            trans_dow = now_dt.weekday()

        fraud_feats = {
            "merchant": merchant,
            "category": category,
            "amt": amount,
            "gender": "M" if (user_row["gender"] or "").lower().startswith("m") else "F",
            "state": (user_row["state"] or "NY").strip()[:2].upper(),
            "job": user_row["job"] or "Unknown",
            "trans_hour": trans_hour,
            "trans_dayofweek": trans_dow,
            "trans_day": trans_day,
            "trans_month": trans_month,
            "age": int(user_row["age"] or 30),
        }
        # --------------------------------------------------------------------------------

        fraud_result = models.predict_fraud(fraud_feats, sender_avg_amt=avg_amt)

        receiver = conn.execute("SELECT * FROM users WHERE account_number=?", (receiver_account,)).fetchone()
        receiver_name = receiver["full_name"] if receiver else "External Account"

        if fraud_result["flagged"]:
            status = "pending_review"
        else:
            status = "cleared"
            conn.execute("UPDATE users SET balance = balance - ? WHERE id=?", (amount, session["user_id"]))
            if receiver:
                conn.execute("UPDATE users SET balance = balance + ? WHERE id=?", (amount, receiver["id"]))

        conn.execute(
            """INSERT INTO transactions (sender_id, receiver_account, receiver_name, amount, merchant,
               category, status, fraud_probability, fraud_reasons, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (session["user_id"], receiver_account, receiver_name, amount, merchant, category, status,
             fraud_result["probability"], "; ".join(fraud_result["reasons"]), db.now()),
        )
        conn.commit()

        if status == "pending_review":
            return jsonify({
                "status": "pending_review",
                "flagged": True,
                "probability": fraud_result["probability"],
                "reasons": fraud_result["reasons"],
                "message": "This transaction triggered a security review. Funds will not transfer until manager approval."
            })
        return jsonify({"status": "cleared", "message": "Transaction completed successfully."})
    finally:
        conn.close()

# ---------------------------------------------------------------------------
# Currency
# ---------------------------------------------------------------------------
def get_currency_history(conn, pair="EUR/USD"):
    rows = conn.execute(
        "SELECT close_price FROM currency_history WHERE pair=? ORDER BY day_index ASC", (pair,)
    ).fetchall()
    return [r["close_price"] for r in rows]

@app.route("/api/currency")
@login_required
def currency():
    conn = db.get_db()
    try:
        history = get_currency_history(conn)
        prediction = models.predict_currency(history)
        user_row = current_user_row()

        suggestions = []
        balance = float(user_row["balance"] or 0.0) if user_row["role"] == "client" else 50000.0
        if prediction["direction"] == "up":
            suggestions.append({"title": "EUR/USD term deposit",
                                 "detail": "The model expects EUR/USD to strengthen. Locking part of your balance "
                                           "into a fixed-term EUR deposit could benefit from the move."})
        else:
            suggestions.append({"title": "USD-denominated term deposit",
                                 "detail": "The model expects EUR/USD to soften. A USD-based term deposit avoids "
                                           "that currency drag while still earning a fixed rate."})
        if balance >= 20000:
            suggestions.append({"title": "Premium 12-month term deposit — 4.2% APY",
                                 "detail": "Available to balances over $20,000. No fraud or credit flags required."})
        else:
            suggestions.append({"title": "Fresh Start campaign loan — 6.9% APR",
                                 "detail": "A promotional rate on personal loans up to $5,000 for accounts building "
                                           "their balance."})

        return jsonify({"history": history[-45:], "prediction": prediction, "suggestions": suggestions})
    finally:
        conn.close()

@app.route("/api/currency/advance", methods=["POST"])
@login_required
def currency_advance():
    conn = db.get_db()
    try:
        history = get_currency_history(conn)
        prediction = models.predict_currency(history)
        noise = random.gauss(0, 0.0015)
        new_price = round(prediction["predicted_next"] + noise, 5)
        next_index = conn.execute(
            "SELECT MAX(day_index) as m FROM currency_history WHERE pair='EUR/USD'"
        ).fetchone()["m"] + 1
        conn.execute(
            "INSERT INTO currency_history (pair, day_index, close_price) VALUES (?,?,?)",
            ("EUR/USD", next_index, new_price),
        )
        conn.commit()
        history = get_currency_history(conn)
        new_prediction = models.predict_currency(history)
        return jsonify({"history": history[-45:], "prediction": new_prediction})
    finally:
        conn.close()

# ---------------------------------------------------------------------------
# Manager Routes
# ---------------------------------------------------------------------------
@app.route("/api/manager/notifications")
@login_required
@role_required("manager")
def manager_notifications():
    conn = db.get_db()
    try:
        pending_loans = conn.execute("SELECT COUNT(*) c FROM loans WHERE status='pending'").fetchone()["c"]
        pending_fraud = conn.execute("SELECT COUNT(*) c FROM transactions WHERE status='pending_review'").fetchone()["c"]
        return jsonify({"pending_loans": pending_loans, "pending_fraud": pending_fraud})
    finally:
        conn.close()

@app.route("/api/manager/loans")
@login_required
@role_required("manager")
def manager_loans():
    status = request.args.get("status", "pending")
    conn = db.get_db()
    try:
        rows = conn.execute(
            """SELECT loans.*, users.full_name, users.account_number, users.credit_score, users.income, users.balance
               FROM loans JOIN users ON loans.user_id = users.id
               WHERE loans.status=? ORDER BY loans.created_at DESC""",
            (status,),
        ).fetchall()
        return jsonify({"loans": [dict(r) for r in rows]})
    finally:
        conn.close()

@app.route("/api/manager/loans/<int:loan_id>/decide", methods=["POST"])
@login_required
@role_required("manager")
def manager_decide_loan(loan_id):
    d = request.get_json(force=True)
    approve = bool(d.get("approve"))
    conn = db.get_db()
    try:
        conn.execute(
            "UPDATE loans SET status=?, decided_by=?, decided_at=? WHERE id=?",
            ("approved" if approve else "rejected", session["user_id"], db.now(), loan_id),
        )
        if approve:
            loan = conn.execute("SELECT * FROM loans WHERE id=?", (loan_id,)).fetchone()
            conn.execute("UPDATE users SET balance = balance + ? WHERE id=?", (loan["amount"], loan["user_id"]))
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()

@app.route("/api/manager/fraud")
@login_required
@role_required("manager")
def manager_fraud():
    status = request.args.get("status", "pending_review")
    conn = db.get_db()
    try:
        rows = conn.execute(
            """SELECT transactions.*, users.full_name, users.account_number, users.balance as sender_balance
               FROM transactions JOIN users ON transactions.sender_id = users.id
               WHERE transactions.status=? ORDER BY transactions.created_at DESC""",
            (status,),
        ).fetchall()
        return jsonify({"transactions": [dict(r) for r in rows]})
    finally:
        conn.close()

@app.route("/api/manager/fraud/<int:tx_id>/decide", methods=["POST"])
@login_required
@role_required("manager")
def manager_decide_fraud(tx_id):
    d = request.get_json(force=True)
    accept = bool(d.get("accept"))
    conn = db.get_db()
    try:
        tx = conn.execute("SELECT * FROM transactions WHERE id=?", (tx_id,)).fetchone()
        if not tx:
            return jsonify({"error": "Transaction not found."}), 404

        new_status = "manager_approved" if accept else "manager_rejected"
        conn.execute(
            "UPDATE transactions SET status=?, decided_by=?, decided_at=? WHERE id=?",
            (new_status, session["user_id"], db.now(), tx_id),
        )
        if accept:
            conn.execute("UPDATE users SET balance = balance - ? WHERE id=?", (tx["amount"], tx["sender_id"]))
            receiver = conn.execute("SELECT * FROM users WHERE account_number=?", (tx["receiver_account"],)).fetchone()
            if receiver:
                conn.execute("UPDATE users SET balance = balance + ? WHERE id=?", (tx["amount"], receiver["id"]))
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()

@app.route("/api/manager/clients")
@login_required
@role_required("manager")
def manager_clients():
    conn = db.get_db()
    try:
        rows = conn.execute("SELECT * FROM users WHERE role='client' ORDER BY full_name").fetchall()
        clients = []
        for r in rows:
            d = user_public(r)
            d["segment"] = models.predict_segment(
                credit_score=r["credit_score"], age=r["age"], tenure=r["tenure_years"],
                balance=r["balance"], salary=r["income"], num_products=r["num_of_products"],
                geography=r["geography"], gender=r["gender"]
            )["segment_label"]
            clients.append(d)
        return jsonify({"clients": clients})
    finally:
        conn.close()

@app.route("/api/manager/dashboard")
@login_required
@role_required("manager")
def manager_dashboard():
    conn = db.get_db()
    try:
        clients = conn.execute("SELECT * FROM users WHERE role='client'").fetchall()
        total_clients = len(clients)
        total_users = conn.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]
        total_balance = sum(float(c["balance"] or 0) for c in clients)

        loan_counts = {r["status"]: r["c"] for r in conn.execute(
            "SELECT status, COUNT(*) c FROM loans GROUP BY status")}
        decided = loan_counts.get("approved", 0) + loan_counts.get("rejected", 0)
        approval_rate = round(100 * loan_counts.get("approved", 0) / decided, 1) if decided else None

        tx_counts = {r["status"]: r["c"] for r in conn.execute(
            "SELECT status, COUNT(*) c FROM transactions GROUP BY status")}
        total_tx = sum(tx_counts.values())
        flagged_tx = tx_counts.get("pending_review", 0) + tx_counts.get("manager_approved", 0) + tx_counts.get("manager_rejected", 0)

        signup_rows = conn.execute(
            "SELECT substr(created_at,1,10) AS day, COUNT(*) c FROM users GROUP BY day ORDER BY day"
        ).fetchall()
        signups = [{"day": r["day"], "count": r["c"]} for r in signup_rows]

        client_segments = [
            dict(credit_score=c["credit_score"], age=c["age"], tenure=c["tenure_years"],
                 balance=c["balance"], salary=c["income"], num_products=c["num_of_products"],
                 geography=c["geography"], gender=c["gender"])
            for c in clients
        ]
        segments = models.cluster_distribution(client_segments)
        history = get_currency_history(conn)
        currency_pred = models.predict_currency(history) if len(history) >= 30 else None

        live_stats = {
            "loan": {"label": "Approval rate at this bank", "value": f"{approval_rate}%" if approval_rate is not None else "No decisions yet"},
            "fraud": {"label": "Transactions flagged", "value": f"{flagged_tx} / {total_tx}" if total_tx else "No transactions yet"},
            "currency": {"label": "Latest predicted move", "value": f"{currency_pred['pct_change']:+.2f}%" if currency_pred else "—"},
            "segmentation": {"label": "Premium-segment clients", "value": f"{segments.get('Premium Relationship', 0)} of {total_clients}"},
        }

        return jsonify({
            "total_users": total_users,
            "total_clients": total_clients,
            "total_balance": round(total_balance, 2),
            "loan_counts": loan_counts,
            "approval_rate": approval_rate,
            "tx_counts": tx_counts,
            "segments": segments,
            "signups": signups,
            "currency_prediction": currency_pred,
            "model_metrics": getattr(models, "MODEL_METRICS", {}),
            "live_stats": live_stats,
        })
    finally:
        conn.close()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)