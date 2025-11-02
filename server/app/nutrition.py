import os, requests
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from utils.calc import tdee, goal_calories, macro_targets

nutrition_bp = Blueprint("nutrition", __name__)

profiles = lambda: db["profiles"] if db else None

@nutrition_bp.route("/nutrition/targets", methods=["POST"])
@jwt_required()
def targets():
    uid = get_jwt_identity()
    data = request.get_json() or {}

    # allow using stored profile as defaults
    prof = profiles().find_one({"userId": uid}, {"_id": 0}) or {}

    sex = data.get("sex", prof.get("sex"))
    age = float(data.get("age", prof.get("age") or 0))
    height_cm = float(data.get("height_cm", prof.get("height_cm") or 0))
    weight_kg = float(data.get("weight_kg", prof.get("weight_kg") or 0))
    body_fat_percent = data.get("body_fat_percent", prof.get("body_fat_percent"))
    activity_level = data.get("activity_level", prof.get("activity_level", "moderate"))
    goal = (data.get("goal") or "maintain").lower()   # "cut"/"maintain"/"bulk"
    pace_lbs_per_week = float(data.get("pace_lbs_per_week") or 0.0)  # e.g., 2 for 2lb/week

    for k, v in [("sex", sex), ("age", age), ("height_cm", height_cm), ("weight_kg", weight_kg)]:
        if not v:
            return jsonify({"error": f"Missing field: {k}"}), 400

    tdee_kcal = tdee(sex, age, height_cm, weight_kg, activity_level, body_fat_percent)
    cals = goal_calories(tdee_kcal, goal, pace_lbs_per_week)
    macros = macro_targets(cals, weight_kg, goal)

    # optional: remember last computed targets
    profiles().update_one({"userId": uid}, {"$set": {"goals.lastTargets": macros, "goals.lastGoal": goal}}, upsert=True)

    return jsonify({
        "tdee_kcal": round(tdee_kcal),
        "targets": macros,
        "assumptions": {
            "formula": "Katch-McArdle if body_fat provided else Mifflin-St Jeor",
            "activity_level": activity_level,
            "pace_lbs_per_week": pace_lbs_per_week
        }
    })

@nutrition_bp.route("/foods/search", methods=["GET"])
@jwt_required()
def foods_search():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"error": "Missing q"}), 400

    # Example with Nutritionix instant endpoint
    app_id = os.getenv("NUTRITIONIX_APP_ID")
    api_key = os.getenv("NUTRITIONIX_API_KEY")
    if not (app_id and api_key):
        return jsonify({"error": "Nutrition API keys not configured"}), 500

    url = "https://trackapi.nutritionix.com/v2/search/instant"
    headers = {"x-app-id": app_id, "x-app-key": api_key}
    resp = requests.get(url, headers=headers, params={"query": q, "detailed": True}, timeout=10)

    if resp.status_code != 200:
        return jsonify({"error": "nutrition provider error", "status": resp.status_code}), 502

    data = resp.json()
    # return a minimal shape (foods + macros per serving)
    items = []
    for item in data.get("common", []) + data.get("branded", []):
        nf = {
            "name": item.get("food_name") or item.get("brand_name_item_name"),
            "brand": item.get("brand_name"),
            "serving_qty": item.get("serving_qty"),
            "serving_unit": item.get("serving_unit"),
            "calories": item.get("nf_calories"),
            "protein_g": item.get("nf_protein"),
            "carbs_g": item.get("nf_total_carbohydrate"),
            "fat_g": item.get("nf_total_fat")
        }
        items.append({k:v for k,v in nf.items() if v is not None})

    return jsonify({"query": q, "items": items[:25]})
