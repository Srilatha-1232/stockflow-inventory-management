
import os

from flask import Flask, jsonify
from dotenv import load_dotenv
from sqlalchemy import text

from config import Config
from models import db

# Load environment variables
load_dotenv()


# Create Flask application
app = Flask(__name__)

# Load configuration
app.config.from_object(Config)

# Create instance folder if it does not exist
os.makedirs(app.instance_path, exist_ok=True)

# Initialize database
db.init_app(app)


# Create database tables
with app.app_context():
    db.create_all()

    print("Database initialized successfully!")


# Home route
@app.route("/")
def home():

    return """
    <h1>Welcome to StockFlow!</h1>
    <p>SaaS Inventory Management System</p>
    <p>Application is running successfully.</p>
    """


# Health check route
@app.route("/health")
def health():

    try:
        db.session.execute(text("SELECT 1"))

        return jsonify({
            "status": "success",
            "message": "StockFlow is running",
            "database": "Connected"
        }), 200

    except Exception:
        app.logger.exception("Database health check failed")

        return jsonify({
            "status": "error",
            "database": "Disconnected"
        }), 500


if __name__ == "__main__":

    app.run(debug=True)
