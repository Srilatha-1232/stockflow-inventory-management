
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy import UniqueConstraint, CheckConstraint

db = SQLAlchemy()


# ==================================
# ORGANIZATION MODEL
# ==================================

class Organization(db.Model):

    __tablename__ = "organizations"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(
        db.String(120),
        nullable=False
    )

    default_threshold = db.Column(
        db.Integer,
        nullable=False,
        default=5
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    users = db.relationship(
        "User",
        backref="organization",
        cascade="all, delete-orphan"
    )

    products = db.relationship(
        "Product",
        backref="organization",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"Organization('{self.name}')"


# ==================================
# USER MODEL
# ==================================

class User(UserMixin, db.Model):

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    organization_id = db.Column(
        db.Integer,
        db.ForeignKey("organizations.id"),
        nullable=False,
        unique=True
    )

    email = db.Column(
        db.String(120),
        nullable=False,
        unique=True
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    def set_password(self, password):

        self.password_hash = generate_password_hash(password)

    def check_password(self, password):

        return check_password_hash(
            self.password_hash,
            password
        )

    def __repr__(self):
        return f"User('{self.email}')"


# ==================================
# PRODUCT MODEL
# ==================================

class Product(db.Model):

    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)

    organization_id = db.Column(
        db.Integer,
        db.ForeignKey("organizations.id"),
        nullable=False,
        index=True
    )

    name = db.Column(
        db.String(120),
        nullable=False
    )

    sku = db.Column(
        db.String(80),
        nullable=False
    )

    description = db.Column(
        db.Text,
        nullable=True
    )

    quantity = db.Column(
        db.Integer,
        nullable=False,
        default=0
    )

    cost_price = db.Column(
        db.Numeric(10, 2),
        nullable=True
    )

    selling_price = db.Column(
        db.Numeric(10, 2),
        nullable=True
    )

    low_stock_threshold = db.Column(
        db.Integer,
        nullable=True
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "sku",
            name="unique_sku_per_organization"
        ),
        CheckConstraint(
            "quantity >= 0",
            name="non_negative_quantity"
        ),
    )

    def __repr__(self):
        return f"Product('{self.name}', '{self.sku}')"
