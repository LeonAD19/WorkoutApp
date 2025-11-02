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
    
    if os.getenv("FLASK_ENV") == "development":
        CORS(app)

    # MongoDB connection
    MONGO_URI = os.getenv("MONGO_URI")
    if MONGO_URI:
        try:
            mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            # Test connection
            mongo_client.server_info()
            db = mongo_client["fitnessApp"]
            workouts = db["workouts"]
            print("✅ Connected to MongoDB!")
        except Exception as e:
            print(f"⚠️ MongoDB connection failed: {e}")
            mongo_client = None
            db = None
            workouts = None
    else:
        print("⚠️ MongoDB URI not found")

    # Register cleanup
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        if mongo_client:
            mongo_client.close()

    # Import routes (register blueprints)
    from app.routes import routes
    app.register_blueprint(routes)

    return app
