# FIXED app/config.py - Added ALLOWED_ORIGINS and Security Improvements

import os
from datetime import timedelta

class BaseConfig:
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY")
    if not SECRET_KEY:
        raise ValueError("FLASK_SECRET_KEY environment variable is required")

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("FLASK_ENV") == "production"
    PERMANENT_SESSION_LIFETIME = timedelta(hours=1)

    # FIXED: Flexible CORS configuration
    ALLOWED_ORIGINS = os.environ.get(
        "ALLOWED_ORIGINS", 
        "http://localhost:3000,http://127.0.0.1:3000,https://dsa-chatbot-3rll.onrender.com"
    )

    # Database and API Keys
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
    HF_API_TOKEN = os.environ.get("HF_API_TOKEN")
    HF_API_TOKEN_BACKUP = os.environ.get("HF_API_TOKEN_BACKUP")

    # Google OAuth
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")

    # IMPROVED: Dynamic redirect URI with fallback
    REDIRECT_URI = os.environ.get(
        "REDIRECT_URI", 
        "https://dsa-chatbot-3rll.onrender.com/oauth2callback"
    )

    # API URLs
    GROQ_CHAT_API_URL = "https://api.groq.com/openai/v1/chat/completions"

    # ADDED: Security and rate limiting settings
    MAX_QUERY_LENGTH = int(os.environ.get("MAX_QUERY_LENGTH", "2000"))
    RATE_LIMIT_PER_MINUTE = int(os.environ.get("RATE_LIMIT_PER_MINUTE", "30"))
    
    # Logging
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

    # Validate required environment variables (warnings only, don't crash)
    @classmethod
    def validate_config(cls):
        required_vars = [
            "SUPABASE_URL", "SUPABASE_KEY", "GROQ_API_KEY",
            "HF_API_TOKEN", "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"
        ]
        
        missing_vars = [var for var in required_vars if not getattr(cls, var)]
        if missing_vars:
            print(f"⚠️ WARNING: Missing environment variables: {', '.join(missing_vars)}")
            print("⚠️ Some features may not work properly without these variables.")
        
        # IMPROVED: Better validation feedback
        if cls.ALLOWED_ORIGINS:
            origins = [o.strip() for o in cls.ALLOWED_ORIGINS.split(',')]
            print(f"✅ CORS configured for origins: {origins}")
        
        return True

class DevelopmentConfig(BaseConfig):
    DEBUG = True
    OAUTHLIB_INSECURE_TRANSPORT = "1"
    
    # More permissive settings for development
    SESSION_COOKIE_SECURE = False
    MAX_QUERY_LENGTH = 5000  # Allow longer queries in development
    RATE_LIMIT_PER_MINUTE = 100  # More generous rate limiting

class ProductionConfig(BaseConfig):
    DEBUG = False
    
    # Ensure secure cookies in production
    SESSION_COOKIE_SECURE = True
    
    # Stricter settings for production
    MAX_QUERY_LENGTH = 1500
    RATE_LIMIT_PER_MINUTE = 20

def get_config(name: str):
    config_class = ProductionConfig if name == "production" else DevelopmentConfig
    config_class.validate_config()
    return config_class
