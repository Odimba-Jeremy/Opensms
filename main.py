"""API de la passerelle SMS (version Flask, sans compilation sur Termux).

Lancer :  python main.py
"""
import re
import secrets

from flask import Flask, jsonify, request

import config
import storage
import worker

PHONE_RE = re.compile(r"^\+?[0-9]{6,15}$")

app = Flask(__name__)


def error(msg: str, code: int):
    return jsonify({"error": msg}), code


@app.before_request
def check_key():
    if request.path == "/health":
        return None
    key = request.headers.get("X-API-Key", "")
    if not secrets.compare_digest(key, config.API_KEY):
        return error("Clé d'API invalide", 401)
    return None


@app.get("/health")
def health():
    return jsonify({"ok": True, "sender": config.SENDER_MODE})


@app.post("/sms")
def send_sms():
    data = request.get_json(silent=True) or {}
    number = str(data.get("number", "")).replace(" ", "")
    message = str(data.get("message", ""))
    if not PHONE_RE.match(number):
        return error("Numéro invalide", 422)
    if not 1 <= len(message) <= 640:
        return error("Message vide ou trop long (max 640)", 422)
    sms_id = storage.add_sms(number, message)
    return jsonify({"id": sms_id, "status": "pending"}), 202


@app.get("/sms/<int:sms_id>")
def get_sms(sms_id: int):
    sms = storage.get_sms(sms_id)
    if not sms:
        return error("SMS introuvable", 404)
    return jsonify(sms)


@app.get("/sms")
def list_sms():
    limit = min(max(request.args.get("limit", 50, type=int), 1), 500)
    status = request.args.get("status")
    if status and status not in ("pending", "sent", "failed"):
        return error("status invalide", 422)
    return jsonify(storage.list_sms(limit, status))


if __name__ == "__main__":
    storage.init_db()
    worker.start()
    if config.API_KEY == "change-me":
        print("⚠️  Change SMS_API_KEY avant toute exposition réseau !")
    app.run(host=config.HOST, port=config.PORT)
