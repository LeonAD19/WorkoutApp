import os
from flask import current_app, Blueprint, jsonify, request, send_from_directory
from app import db, workouts

api = Blueprint("api", __name__)  # Changed from "routes" to "api"

@api.route("/")
def serve_react_app():
    index_path = os.path.join(current_app.static_folder, "index.html")
    if os.path.exists(index_path):
        return send_from_directory(current_app.static_folder, "index.html")
    else:
        return "⚠️ React build not found. Run 'npm run build' inside the client folder.", 404
    
@api.route("/api")
def api_home():
    return jsonify({"message": "Flask backend is running!"})

@api.route("/api/workouts", methods=["POST"])
def add_workout():
    if not workouts:
        return jsonify({"error": "MongoDB not connected"}), 500
    data = request.get_json()
    workouts.insert_one(data)
    return jsonify({"message": "Workout added!"}), 201

@api.route("/api/workouts", methods=["GET"])
def get_workouts():
    if not workouts:
        return jsonify({"error": "MongoDB not connected"}), 500
    data = list(workouts.find({}, {"_id": 0}))
    return jsonify(data)
