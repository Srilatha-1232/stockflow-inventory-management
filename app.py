
import os

from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from config import Config
from models import db, User, Organization


# APPLICATION SETUP

app = Flask(__name__)
app.config.from_object(Config)
os.makedirs(app.instance_path, exist_ok=True)
db.init_app(app)

csrf = CSRFProtect(app)


# LOGIN MANAGER SETUP

login_manager = LoginManager()
login_manager.init_app(app)

login_manager.login_view = "login"
login_manager.login_message = "Please log in to access this page."


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# DATABASE INITIALIZATION

with app.app_context():
    db.create_all()
    print("Database initialized successfully!")

# ==================================
# HOME ROUTE
# ==================================

@app.route("/")
def home():

    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    return redirect(url_for("login"))


# ==================================
# SIGNUP ROUTE
# ==================================

@app.route("/signup", methods=["GET", "POST"])
def signup():

    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()

        password = request.form.get("password", "")

        confirm_password = request.form.get(
            "confirm_password", ""
        )

        organization_name = request.form.get(
            "organization_name", ""
        ).strip()

        # Basic validation

        if not email or not organization_name or not password:
            flash("All fields are required.", "danger")
            return redirect(url_for("signup"))

        if "@" not in email or "." not in email.split("@")[-1]:
            flash("Please enter a valid email address.", "danger")
            return redirect(url_for("signup"))

        if len(password) < 8:
            flash("Password must contain at least 8 characters.", "danger")
            return redirect(url_for("signup"))

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("signup"))

        # Check duplicate email

        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            flash("This email is already registered.", "warning")
            return redirect(url_for("signup"))

        try:

            # Create organization
            organization = Organization(
                name=organization_name,
                default_threshold=5
            )

            db.session.add(organization)

            db.session.flush()

            # Create user

            user = User(
                email=email,
                organization_id=organization.id
            )

            user.set_password(password)

            db.session.add(user)

            # Save both records together

            db.session.commit()

            # Automatically log in

            login_user(user)

            flash("Account created successfully!", "success")

            return redirect(url_for("dashboard"))

        except IntegrityError:

            db.session.rollback()

            flash(
                "This email or organization account could not be created. Please check your details.",
                "danger"
            )

            return redirect(url_for("signup"))

        except Exception:

            db.session.rollback()

            app.logger.exception("Signup failed")

            flash(
                "Something went wrong. Please try again.",
                "danger"
            )

            return redirect(url_for("signup"))

    return render_template("signup.html")


# ==================================
# LOGIN ROUTE
# ==================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()

        password = request.form.get("password", "")

        if not email or not password:

            flash("Please enter email and password.", "danger")

            return redirect(url_for("login"))

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):

            login_user(user)

            flash("Login successful!", "success")

            return redirect(url_for("dashboard"))

        flash("Invalid email or password.", "danger")

        return redirect(url_for("login"))

    return render_template("login.html")


# ==================================
# DASHBOARD ROUTE
# ==================================

@app.route("/dashboard")
@login_required
def dashboard():

    return render_template(
        "dashboard.html",
        user=current_user
    )


# ==================================
# LOGOUT ROUTE
# ==================================

@app.route("/logout", methods=["POST"])
@login_required
def logout():

    logout_user()

    flash("You have logged out successfully.", "success")

    return redirect(url_for("login"))


# ==================================
# HEALTH CHECK
# ==================================

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


# ==================================
# RUN APPLICATION
# ==================================

if __name__ == "__main__":

    app.run(debug=True)
