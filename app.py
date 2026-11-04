
import os

from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from config import Config
from models import db, User, Organization, Product


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
# ADD PRODUCT ROUTE
# ==================================

@app.route("/products/add", methods=["GET", "POST"])
@login_required
def add_product():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        sku = request.form.get("sku", "").strip().upper()
        description = request.form.get("description", "").strip()

        try:
            quantity = int(request.form.get("quantity", 0))
            cost_price = float(request.form.get("cost_price", 0))
            selling_price = float(request.form.get("selling_price", 0))

            threshold_input = request.form.get("low_stock_threshold", "").strip()

            threshold = (
                int(threshold_input)
                if threshold_input
                else current_user.organization.default_threshold
            )

        except (ValueError, TypeError):
            flash("Please enter valid numeric values.", "danger")
            return redirect(url_for("add_product"))

        # Validate fields
        if not name or not sku:
            flash("Product name and SKU are required.", "danger")
            return redirect(url_for("add_product"))

        if quantity < 0 or threshold < 0:
            flash("Quantity and threshold cannot be negative.", "danger")
            return redirect(url_for("add_product"))

        if cost_price < 0 or selling_price < 0:
            flash("Prices cannot be negative.", "danger")
            return redirect(url_for("add_product"))

        # Check duplicate SKU within this organization
        existing_product = Product.query.filter_by(
            organization_id=current_user.organization_id,
            sku=sku
        ).first()

        if existing_product:
            flash("This SKU already exists in your organization.", "warning")
            return redirect(url_for("add_product"))

        try:
            product = Product(
                organization_id=current_user.organization_id,
                name=name,
                sku=sku,
                description=description,
                quantity=quantity,
                cost_price=cost_price,
                selling_price=selling_price,
                low_stock_threshold=threshold
            )

            db.session.add(product)
            db.session.commit()

            flash("Product added successfully!", "success")
            return redirect(url_for("view_products"))

        except Exception:
            db.session.rollback()
            app.logger.exception("Product creation failed")
            flash("Unable to add product. Please try again.", "danger")

    return render_template("add_product.html")

@app.route("/products")
@login_required
def view_products():
    search = request.args.get("search", "").strip()

    query = Product.query.filter_by(
        organization_id=current_user.organization_id
    )

    if search:
        query = query.filter(
            db.or_(
                Product.name.ilike(f"%{search}%"),
                Product.sku.ilike(f"%{search}%")
            )
        )

    products = query.order_by(Product.created_at.desc()).all()

    return render_template(
        "products.html",
        products=products,
        search=search
    )

@app.route("/products/edit/<int:product_id>", methods=["GET", "POST"])
@login_required
def edit_product(product_id):

    product = Product.query.filter_by(
        id=product_id,
        organization_id=current_user.organization_id
    ).first_or_404()

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        sku = request.form.get("sku", "").strip().upper()
        description = request.form.get("description", "").strip()

        try:
            quantity = int(request.form.get("quantity"))
            cost_price = float(request.form.get("cost_price"))
            selling_price = float(request.form.get("selling_price"))

            threshold_input = request.form.get("low_stock_threshold", "").strip()

            threshold = (
                int(threshold_input)
                if threshold_input
                else current_user.organization.default_threshold
            )

            if not name or not sku:
                raise ValueError

            if min(quantity, cost_price, selling_price, threshold) < 0:
                raise ValueError

        except (ValueError, TypeError):
            flash("Please enter valid product details.", "danger")
            return redirect(url_for("edit_product", product_id=product.id))

        duplicate = Product.query.filter(
            Product.organization_id == current_user.organization_id,
            Product.sku == sku,
            Product.id != product.id
        ).first()

        if duplicate:
            flash("This SKU already exists.", "warning")
            return redirect(url_for("edit_product", product_id=product.id))

        product.name = name
        product.sku = sku
        product.description = description
        product.quantity = quantity
        product.cost_price = cost_price
        product.selling_price = selling_price
        product.low_stock_threshold = threshold

        try:
            db.session.commit()
            flash("Product updated successfully!", "success")
            return redirect(url_for("view_products"))

        except Exception:
            db.session.rollback()
            app.logger.exception("Product update failed")
            flash("Unable to update product.", "danger")

    return render_template("edit_product.html", product=product)

@app.route("/products/delete/<int:product_id>", methods=["POST"])
@login_required
def delete_product(product_id):

    product = Product.query.filter_by(
        id=product_id,
        organization_id=current_user.organization_id
    ).first_or_404()

    try:
        db.session.delete(product)
        db.session.commit()
        flash("Product deleted successfully!", "success")

    except Exception:
        db.session.rollback()
        app.logger.exception("Product deletion failed")
        flash("Unable to delete product.", "danger")

    return redirect(url_for("view_products"))

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