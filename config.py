import os
from dotenv import load_dotenv
from datetime import timedelta


class Config:
    SQLALCHEMY_DATABASE_URI = 'sqlite:///flyin.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv('APP_SECRET_KEY', 'fallback_secret_key')
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)
