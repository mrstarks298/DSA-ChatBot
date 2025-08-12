import os
from datetime import timedelta

class BaseConfig:
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "supersecret_dev_key")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("FLASK_ENV") == "production"
    PERMANENT_SESSION_LIFETIME = timedelta(hours=1)

    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
    REDIRECT_URI = os.environ.get("REDIRECT_URI", "https://dsa-chatbot-3rll.onrender.com/oauth2callback")

    GROQ_CHAT_API_URL = "https://api.groq.com/openai/v1/chat/completions"


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    OAUTHLIB_INSECURE_TRANSPORT = "1"


class ProductionConfig(BaseConfig):
    DEBUG = False


def get_config(name: str):
    return ProductionConfig if name == "production" else DevelopmentConfig
