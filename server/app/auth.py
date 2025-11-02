import os
import time
import secrets
from datetime import timedelta
from bson.objectid import ObjectId
from flask import Blueprint, request, jsonify
from email_validator import validate_email, EmailNotValidError
from flask_jwt_extended import (
    create_access_token, 
    create_refresh_token,
    jwt_required, 
    get_jwt_identity, 
    get_jwt
)
from app import db, bcrypt
from .emailer import send_email

auth_bp = Blueprint("auth", __name__)

# Database collection helpers
def users():
    return db["users"]

def profiles():
    return db["profiles"]

def blacklist():
    return db["token_blacklist"]

# Verification code generator
def new_verification():
    code = f"{secrets.randbelow(1000000):06d}"  # 6-digit
    return code, int(time.time()) + 15*60       # 15 min expiry

# Email template
def email_html(code):
    return f"""
    <div style="font-family:sans-serif">
      <h2>Verify your email</h2>
      <p>Your code is:</p>
      <div style="font-size:28px;font-weight:700;letter-spacing:3px">{code}</div>
      <p>This code expires in 15 minutes.</p>
    </div>
    """

@auth_bp.route("/register", methods=["POST"])
def register():
    if not users():
        return jsonify({"error": "DB not ready"}), 500
        
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    name = data.get("name") or ""

    # Validate email
    try:
        validate_email(email)
    except EmailNotValidError as e:
        return jsonify({"error": str(e)}), 400
        
    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters."}), 400
        
    if users().find_one({"email": email}):
        return jsonify({"error": "Email already registered."}), 409

    # Hash password
    pw_hash = bcrypt.generate_password_hash(password).decode("utf-8")
    
    # Generate verification code
    code, exp = new_verification()
    
    # Create user
    res = users().insert_one({
        "email": email,
        "password": pw_hash,
        "name": name,
        "emailVerified": False,
        "verify": {"code": code, "expiresAt": exp},
        "token_version": 0,
        "createdAt": int(time.time())
    })
    
    # Create profile
    profiles().insert_one({
        "userId": str(res.inserted_id),
        "sex": None,
        "age": None,
        "height_cm": None,
        "weight_kg": None,
        "body_fat_percent": None,
        "activity_level": "moderate",
        "goals": {}
    })

    # Send verification email
    try:
        send_email(email, "Verify your WorkoutApp email", email_html(code))
    except Exception as e:
        print("Email send error:", e)

    # Issue tokens
    uid = str(res.inserted_id)
    tv = 0
    access = create_access_token(
        identity=uid, 
        additional_claims={"tv": tv}, 
        expires_delta=timedelta(minutes=int(os.getenv("JWT_ACCESS_MIN", "30")))
    )
    refresh = create_refresh_token(
        identity=uid, 
        additional_claims={"tv": tv}, 
        expires_delta=timedelta(days=int(os.getenv("JWT_REFRESH_DAYS", "14")))
    )
    
    return jsonify({
        "access": access, 
        "refresh": refresh, 
        "user": {
            "id": uid, 
            "email": email, 
            "name": name, 
            "emailVerified": False
        }
    }), 201

@auth_bp.route("/login", methods=["POST"])
def login():
    if not users():
        return jsonify({"error": "DB not ready"}), 500
        
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    
    user = users().find_one({"email": email})
    if not user or not bcrypt.check_password_hash(user["password"], password):
        return jsonify({"error": "Invalid credentials."}), 401

    tv = int(user.get("token_version", 0))
    uid = str(user["_id"])
    
    access = create_access_token(identity=uid, additional_claims={"tv": tv})
    refresh = create_refresh_token(identity=uid, additional_claims={"tv": tv})
    
    public = {
        "id": uid, 
        "email": user["email"], 
        "name": user.get("name", ""), 
        "emailVerified": user.get("emailVerified", False)
    }
    
    return jsonify({"access": access, "refresh": refresh, "user": public})

@auth_bp.route("/send-verification", methods=["POST"])
@jwt_required()
def send_verification():
    uid = get_jwt_identity()
    user = users().find_one({"_id": ObjectId(uid)})
    
    if not user:
        return jsonify({"error": "No user"}), 404
    if user.get("emailVerified"):
        return jsonify({"message": "Already verified"}), 200

    code, exp = new_verification()
    users().update_one(
        {"_id": ObjectId(uid)}, 
        {"$set": {"verify": {"code": code, "expiresAt": exp}}}
    )
    
    try:
        send_email(user["email"], "Verify your WorkoutApp email", email_html(code))
    except Exception as e:
        print("Email send error:", e)
        
    return jsonify({"message": "Verification code sent"})

@auth_bp.route("/verify", methods=["POST"])
@jwt_required()
def verify():
    uid = get_jwt_identity()
    data = request.get_json() or {}
    code = (data.get("code") or "").strip()

    user = users().find_one({"_id": ObjectId(uid)})
    if not user:
        return jsonify({"error": "No user"}), 404
    if user.get("emailVerified"):
        return jsonify({"message": "Already verified"}), 200

    v = (user.get("verify") or {})
    if not v or v.get("code") != code or int(time.time()) > int(v.get("expiresAt", 0)):
        return jsonify({"error": "Invalid or expired code"}), 400

    users().update_one(
        {"_id": ObjectId(uid)}, 
        {"$set": {"emailVerified": True}, "$unset": {"verify": ""}}
    )
    return jsonify({"message": "Email verified"})

@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    uid = get_jwt_identity()
    claims = get_jwt()
    user = users().find_one({"_id": ObjectId(uid)})
    
    if not user:
        return jsonify({"error": "No user"}), 404
    if int(claims.get("tv", 0)) != int(user.get("token_version", 0)):
        return jsonify({"error": "Token version mismatch"}), 401
        
    new_access = create_access_token(
        identity=uid, 
        additional_claims={"tv": int(user.get("token_version", 0))}
    )
    return jsonify({"access": new_access})

@auth_bp.route("/logout", methods=["POST"])
@jwt_required(verify_type=False)  # supports access or refresh
def logout():
    jti = get_jwt()["jti"]
    blacklist().insert_one({"jti": jti, "revokedAt": int(time.time())})
    return jsonify({"message": "Logged out"})

@auth_bp.route("/logout_all", methods=["POST"])
@jwt_required()
def logout_all():
    uid = get_jwt_identity()
    users().update_one({"_id": ObjectId(uid)}, {"$inc": {"token_version": 1}})
    return jsonify({"message": "All sessions revoked"})

@auth_bp.route("/me", methods=["GET", "PATCH"])
@jwt_required()
def me():
    if not users():
        return jsonify({"error": "DB not ready"}), 500
        
    uid = get_jwt_identity()
    user = users().find_one({"_id": ObjectId(uid)}, {"password": 0})
    prof = profiles().find_one({"userId": uid}, {"_id": 0}) or {}
    
    if request.method == "GET":
        user_data = {k: v for k, v in user.items() if k != "_id"}
        user_data["id"] = uid
        return jsonify({"user": user_data, "profile": prof})

    # PATCH to update profile fields
    updates = (request.get_json() or {})
    allowed = {"sex", "age", "height_cm", "weight_kg", "body_fat_percent", "activity_level"}
    payload = {k: v for k, v in updates.items() if k in allowed}
    
    if payload:
        profiles().update_one({"userId": uid}, {"$set": payload}, upsert=True)
        
    prof = profiles().find_one({"userId": uid}, {"_id": 0})
    return jsonify({"profile": prof})
