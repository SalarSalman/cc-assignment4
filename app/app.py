"""Loan EMI Calculator - Flask application backed by MongoDB.

Configuration comes from environment variables only:
  MONGO_URL  MongoDB connection string (required)
  PORT       port to listen on (default 8080)
  HOSTNAME   pod name, set automatically by Kubernetes
"""
import math
import os
import socket
from datetime import datetime, timezone

from flask import Flask, jsonify, render_template, request
from pymongo import DESCENDING, MongoClient
from pymongo.errors import PyMongoError

MONGO_URL = os.environ.get("MONGO_URL")
if not MONGO_URL:
    raise RuntimeError("The MONGO_URL environment variable is not set")

POD_NAME = os.environ.get("HOSTNAME") or socket.gethostname()
try:
    POD_IP = socket.gethostbyname(socket.gethostname())
except OSError:
    POD_IP = "unknown"

# Limits keep the formula numerically safe.
MAX_PRINCIPAL = 1_000_000_000_000
MAX_RATE = 100
MAX_MONTHS = 600


def make_client(timeout_ms):
    # primaryPreferred: use the PRIMARY when there is one, otherwise any member,
    # so reads and the health check keep working during an election.
    return MongoClient(MONGO_URL, serverSelectionTimeoutMS=timeout_ms,
                       readPreference="primaryPreferred", tz_aware=True)


main_client = make_client(15000)    # long enough to ride out a PRIMARY election
health_client = make_client(2000)   # the readiness probe must answer quickly
calculations = main_client.get_default_database("emidb")["calculations"]

app = Flask(__name__)


def parse_inputs(data):
    """Return ((principal, rate, months), None) or (None, error message)."""
    try:
        principal = float(data.get("principal"))
        rate = float(data.get("rate"))
        months = float(data.get("months"))
    except (TypeError, ValueError):
        return None, "Loan amount, interest rate and tenure must be numbers."
    if not all(math.isfinite(v) for v in (principal, rate, months)):
        return None, "Loan amount, interest rate and tenure must be finite numbers."
    if principal <= 0 or rate <= 0 or months <= 0:
        return None, "Loan amount, interest rate and tenure must be positive numbers."
    if months != int(months):
        return None, "Tenure must be a whole number of months."
    if principal > MAX_PRINCIPAL or rate > MAX_RATE or months > MAX_MONTHS:
        return None, "Values are too large (maximum: 1e12 amount, 100% rate, 600 months)."
    return (principal, rate, int(months)), None


def compute_emi(principal, rate, months):
    """EMI = P*r*(1+r)^n / ((1+r)^n - 1), with r the monthly rate."""
    r = rate / 12 / 100
    factor = (1 + r) ** months
    emi = principal * r * factor / (factor - 1)
    total = emi * months
    return emi, total, total - principal


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/emi")
def api_emi():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        data = request.form.to_dict()
    values, error = parse_inputs(data)
    if error:
        return jsonify(error=error), 400
    principal, rate, months = values
    emi, total, interest = compute_emi(principal, rate, months)
    try:
        calculations.insert_one({
            "principal": principal, "rate": rate, "months": months,
            "emi": round(emi, 2), "servedBy": POD_NAME,
            "createdAt": datetime.now(timezone.utc),
        })
    except PyMongoError:
        return jsonify(error="Database unavailable, please try again."), 503
    return jsonify(principal=principal, rate=rate, months=months,
                   emi=round(emi, 2), totalPayment=round(total, 2),
                   totalInterest=round(interest, 2),
                   servedBy=POD_NAME, ip=POD_IP)


@app.get("/api/history")
def api_history():
    try:
        rows = list(calculations.find({}, {"_id": 0})
                    .sort("createdAt", DESCENDING).limit(10))
    except PyMongoError:
        return jsonify(error="Database unavailable, please try again."), 503
    for row in rows:
        row["createdAt"] = row["createdAt"].isoformat()
    return jsonify(rows)


@app.get("/health")
def health():
    try:
        health_client.admin.command("ping")
    except PyMongoError:
        return jsonify(status="unhealthy", database="unreachable"), 503
    return jsonify(status="ok", database="reachable", servedBy=POD_NAME)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
