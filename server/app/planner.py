from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from utils.calc import tdee, goal_calories, macro_targets

planner_bp = Blueprint("planner", __name__)

profiles = lambda: db["profiles"]

@planner_bp.route("/planner/day-summary", methods=["POST"])
@jwt_required()
def day_summary():
    uid = get_jwt_identity()
    data = request.get_json() or {}
    items = data.get("items") or []  # [{name, servings, calories, protein_g, carbs_g, fat_g}, ...]

    # targets can be passed or derived from stored profile + goal inputs
    targets = data.get("targets")
    if not targets:
        # derive from profile (maintain by default)
        prof = profiles().find_one({"userId": uid}, {"_id":0}) or {}
        required = ["sex","age","height_cm","weight_kg","activity_level"]
        if not all(k in prof and prof[k] for k in required):
            return jsonify({"error":"Missing profile fields to compute targets. Provide 'targets' or complete profile."}), 400
        td = tdee(prof["sex"], float(prof["age"]), float(prof["height_cm"]), float(prof["weight_kg"]), prof.get("activity_level", "moderate"), prof.get("body_fat_percent"))
        cals = goal_calories(td, data.get("goal","maintain"), float(data.get("pace_lbs_per_week") or 0))
        targets = macro_targets(cals, float(prof["weight_kg"]), data.get("goal","maintain"))

    total = {"calories":0, "protein_g":0, "carbs_g":0, "fat_g":0}
    clean_items = []
    for it in items:
        s = float(it.get("servings", 1))
        entry = {
            "name": it.get("name","item"),
            "servings": s,
            "calories": float(it.get("calories",0))*s,
            "protein_g": float(it.get("protein_g",0))*s,
            "carbs_g": float(it.get("carbs_g",0))*s,
            "fat_g": float(it.get("fat_g",0))*s
        }
        clean_items.append(entry)
        for k in total:
            total[k] += entry[k]

    remaining = {k: round(max(0.0, targets[k] - total[k])) for k in total.keys() if k in targets}
    over = {k: round(max(0.0, total[k] - targets[k])) for k in total.keys() if k in targets}

    return jsonify({
        "targets": {k:int(v) for k,v in targets.items()},
        "consumed": {k:int(round(v)) for k,v in total.items()},
        "remaining": remaining,
        "over_by": over,
        "items": clean_items
    })

@planner_bp.route("/planner/split", methods=["POST"])
@jwt_required()
def split():
    data = request.get_json() or {}
    targets = data.get("targets")
    meals = int(data.get("meals", 3))
    if not targets:
        return jsonify({"error":"Missing targets (calories, protein_g, carbs_g, fat_g)"}), 400

    per = {k: round(float(targets[k])/meals) for k in ["calories","protein_g","carbs_g","fat_g"] if k in targets}
    return jsonify({"per_meal": per, "meals": meals})
