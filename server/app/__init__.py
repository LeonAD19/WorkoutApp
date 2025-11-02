import os
from flask import Flask, send_from_directory
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from pymongo import MongoClient

# Initialize extensions WITHOUT app context
bcrypt = Bcrypt()
jwt = JWTManager()

# Global variables for MongoDB
mongo_client = None
db = None
workouts = None  # Add this

def create_app():
    global mongo_client, db, workouts  # Add workouts here

    build_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "client", "build"))

    app = Flask(__name__, static_folder=build_path, static_url_path="/")
    
    # Configuration
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "default-secret-key")
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "jwt-secret")
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = int(os.getenv("JWT_ACCESS_MIN", "30")) * 60
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = int(os.getenv("JWT_REFRESH_DAYS", "14")) * 86400
    
    if os.getenv("FLASK_ENV") == "development":
        CORS(app)

    # Initialize extensions with app
    bcrypt.init_app(app)
    jwt.init_app(app)

    # MongoDB connection
    MONGO_URI = os.getenv("MONGO_URI")
    if MONGO_URI:
        try:
            mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            mongo_client.server_info()
            db = mongo_client["fitnessApp"]
            workouts = db["workouts"]  # Add this line
            print("✅ Connected to MongoDB!")
        except Exception as e:
            print(f"⚠️ MongoDB connection failed: {e}")
            mongo_client = None
            db = None
            workouts = None  # Add this
    else:
        print("⚠️ MongoDB URI not found")
        workouts = None  # Add this

    # Cleanup on app shutdown
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        if mongo_client:
            mongo_client.close()

    # IMPORTANT: Import blueprints AFTER db is created
    from app.auth import auth_bp
    from app.routes import api
    from app.nutrition import nutrition_bp
    from app.planner import planner_bp

    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(api)
    app.register_blueprint(nutrition_bp, url_prefix="/nutrition")
    app.register_blueprint(planner_bp, url_prefix="/planner")

    # Serve React build
    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve(path):
        if path and os.path.exists(os.path.join(app.static_folder, path)):
            return send_from_directory(app.static_folder, path)
        return send_from_directory(app.static_folder, "index.html")

    return app

