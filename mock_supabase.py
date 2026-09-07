"""Minimal stand-in for Supabase Auth (GoTrue) so sign-up tests never hit
production. See docs/automation-guide.md, section 2, Option B.

    pip install flask
    python mock_supabase.py          # http://127.0.0.1:54321
"""
import datetime
import uuid

from flask import Flask, jsonify, request

app = Flask(__name__)
users = {}


@app.post("/auth/v1/signup")
def signup():
    body = request.get_json(silent=True) or {}
    email, pw = body.get("email", "").lower(), body.get("password", "")
    if email in users:
        return jsonify(code=422, msg="User already registered"), 422
    if len(pw) < 6:
        return jsonify(code=422, msg="Password should be at least 6 characters"), 422
    now = datetime.datetime.utcnow().isoformat() + "Z"
    users[email] = {
        "id": str(uuid.uuid4()), "email": email, "aud": "authenticated",
        "role": "authenticated", "created_at": now, "updated_at": now,
        "confirmation_sent_at": now, "app_metadata": {"provider": "email"},
        "user_metadata": {}, "identities": [],
    }
    # No access_token in the response -> app shows "verify your email".
    return jsonify(users[email]), 200


@app.post("/auth/v1/token")
def token():
    return jsonify(error="invalid_grant", error_description="Email not confirmed"), 400


@app.get("/auth/v1/user")
def user():
    return jsonify(msg="Invalid JWT"), 401


@app.post("/__reset")
def reset():
    users.clear()
    return "", 204


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=54321)
