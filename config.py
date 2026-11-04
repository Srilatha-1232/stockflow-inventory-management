
import os

class Config:

    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        "development-key-change-before-deployment"
    )

    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "sqlite:///stockflow.db"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False
