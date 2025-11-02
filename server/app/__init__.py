import os
from flask import Flask, app
from flask_cors import CORS
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

mongo_client = None
db = None
workouts = None

def create_app():
    global mongo_client, db, workouts

    build_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "client", "build"))

    app = Flask(__name__, static_folder=build_path, static_url_path="/")
    CORS(app)

    # MongoDB connection
    MONGO_URI = os.getenv("MONGO_URI")
    if MONGO_URI:
        mongo_client = MongoClient(MONGO_URI)
        db = mongo_client["fitnessApp"]
        workouts = db["workouts"]
        print("✅ Connected to MongoDB!")
    else:
        print("⚠️ MongoDB URI not found")

    # Import routes (register blueprints)
    from app.routes import routes
    app.register_blueprint(routes)

    return app
