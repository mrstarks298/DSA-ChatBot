# CRITICAL FIX: app/config.py - Session Persistence Fixed

import os
from datetime import timedelta

class BaseConfig:
    # Core Flask settings
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY")
    
    if not SECRET_KEY:
        raise ValueError("FLASK_SECRET_KEY environment variable is required")

    # ✅ CRITICAL: Enhanced session configuration for persistence
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"  # CRITICAL for OAuth - not "Strict"
    SESSION_COOKIE_SECURE = os.environ.get("FLASK_ENV") == "production"
    SESSION_COOKIE_NAME = "dsa_session"
    SESSION_COOKIE_PATH = "/"
    SESSION_COOKIE_DOMAIN = None
    PERMANENT_SESSION_LIFETIME = timedelta(hours=12)  # Extended to 12 hours
    
    # ✅ NEW: Session configuration flags
    SESSION_REFRESH_EACH_REQUEST = True
    SESSION_PROTECTION = None  # Disable session protection to prevent OAuth issues
    
    # CORS configuration - essential for frontend
    ALLOWED_ORIGINS = os.environ.get(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,https://dsa-chatbot-3rll.onrender.com"
    ).split(',')

    # Database and API Keys
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
    HF_API_TOKEN = os.environ.get("HF_API_TOKEN")
    HF_API_TOKEN_BACKUP = os.environ.get("HF_API_TOKEN_BACKUP")

    # Google OAuth - required for frontend auth
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
    
    # ✅ FIXED: Dynamic redirect URI with /auth prefix
    REDIRECT_URI = os.environ.get(
        "REDIRECT_URI",
        "https://dsa-chatbot-3rll.onrender.com/auth/oauth2callback"
    )

    # API URLs
    GROQ_CHAT_API_URL = "https://api.groq.com/openai/v1/chat/completions"

    # Frontend-specific settings
    MAX_QUERY_LENGTH = int(os.environ.get("MAX_QUERY_LENGTH", "2000"))
    RATE_LIMIT_PER_MINUTE = int(os.environ.get("RATE_LIMIT_PER_MINUTE", "30"))
    STREAMING_ENABLED = os.environ.get("STREAMING_ENABLED", "true").lower() == "true"

    # Content and security settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB for file uploads
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hour

    # Logging
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

    # Template settings for frontend
    TEMPLATES_AUTO_RELOAD = True

    # JSON settings for API responses
    JSONIFY_PRETTYPRINT_REGULAR = False
    JSON_SORT_KEYS = False

    @classmethod
    def validate_config(cls):
        """Enhanced validation with better error messages"""
        required_vars = [
            "SUPABASE_URL", "SUPABASE_KEY", "GROQ_API_KEY",
            "HF_API_TOKEN", "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"
        ]

        missing_vars = [var for var in required_vars if not getattr(cls, var)]

        if missing_vars:
            print(f"⚠️ WARNING: Missing environment variables: {', '.join(missing_vars)}")
            print("⚠️ Some features may not work properly without these variables.")
            print("⚠️ Check your .env file or environment configuration.")
            return False
        else:
            print("✅ All required environment variables are configured.")

        # Validate session configuration
        print(f"🍪 Session cookie config:")
        print(f"   - Name: {cls.SESSION_COOKIE_NAME}")
        print(f"   - SameSite: {cls.SESSION_COOKIE_SAMESITE}")
        print(f"   - Secure: {cls.SESSION_COOKIE_SECURE}")
        print(f"   - HttpOnly: {cls.SESSION_COOKIE_HTTPONLY}")
        print(f"   - Lifetime: {cls.PERMANENT_SESSION_LIFETIME}")

        # Validate CORS configuration
        if cls.ALLOWED_ORIGINS:
            origins = [o.strip() for o in cls.ALLOWED_ORIGINS]
            print(f"✅ CORS configured for origins: {origins}")

        # Validate OAuth configuration
        if cls.GOOGLE_CLIENT_ID and cls.GOOGLE_CLIENT_SECRET:
            print(f"✅ Google OAuth configured with client ID: {cls.GOOGLE_CLIENT_ID[:20]}...")
            print(f"✅ OAuth redirect URI: {cls.REDIRECT_URI}")

        # Validate database configuration
        if cls.SUPABASE_URL and cls.SUPABASE_KEY:
            print(f"✅ Supabase configured with URL: {cls.SUPABASE_URL[:30]}...")

        # Validate API tokens
        if cls.GROQ_API_KEY:
            print(f"✅ Groq API configured")

        if cls.HF_API_TOKEN:
            print(f"✅ Hugging Face API configured")

        if cls.HF_API_TOKEN_BACKUP:
            print(f"✅ Hugging Face backup token available")

        return True

class DevelopmentConfig(BaseConfig):
    """Development configuration with relaxed security for local development"""
    DEBUG = True
    OAUTHLIB_INSECURE_TRANSPORT = "1"
    
    # ✅ IMPORTANT: More permissive session settings for development
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_PROTECTION = None
    
    # Development-specific settings
    MAX_QUERY_LENGTH = 5000
    RATE_LIMIT_PER_MINUTE = 100
    TEMPLATES_AUTO_RELOAD = True
    JSONIFY_PRETTYPRINT_REGULAR = True
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)  # Longer for development

    # Development CORS (more permissive)
    ALLOWED_ORIGINS = os.environ.get(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5000,http://127.0.0.1:5000"
    ).split(',')

    # ✅ FIXED: Override redirect URI for development
    REDIRECT_URI = os.environ.get(
        "REDIRECT_URI",
        "http://localhost:5000/auth/oauth2callback"
    )

class ProductionConfig(BaseConfig):
    """Production configuration with enhanced security"""
    DEBUG = False

    # ✅ CRITICAL: Production session settings - secure but OAuth-compatible
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"  # CRITICAL: Not "Strict"
    SESSION_PROTECTION = None  # Disable session protection for OAuth compatibility
    
    # Production settings
    MAX_QUERY_LENGTH = 1500
    RATE_LIMIT_PER_MINUTE = 20
    WTF_CSRF_ENABLED = True
    JSON_SORT_KEYS = False
    JSONIFY_PRETTYPRINT_REGULAR = False
    PERMANENT_SESSION_LIFETIME = timedelta(hours=12)

    # Production CORS (restrictive)
    ALLOWED_ORIGINS = os.environ.get(
        "ALLOWED_ORIGINS",
        "https://dsa-chatbot-3rll.onrender.com"
    ).split(',')

class TestingConfig(BaseConfig):
    """Testing configuration"""
    TESTING = True
    DEBUG = True
    WTF_CSRF_ENABLED = False
    SESSION_COOKIE_SECURE = False
    SESSION_PROTECTION = None
    OAUTHLIB_INSECURE_TRANSPORT = "1"
    
    # Test-specific settings
    MAX_QUERY_LENGTH = 1000
    RATE_LIMIT_PER_MINUTE = 1000
    PERMANENT_SESSION_LIFETIME = timedelta(hours=1)

    # Test credentials
    GOOGLE_CLIENT_ID = os.environ.get("TEST_GOOGLE_CLIENT_ID", "test_client_id")
    GOOGLE_CLIENT_SECRET = os.environ.get("TEST_GOOGLE_CLIENT_SECRET", "test_client_secret")

def get_config(name: str = None):
    """Get configuration class based on environment"""
    if name is None:
        name = os.environ.get("FLASK_ENV", "production")

    config_classes = {
        "development": DevelopmentConfig,
        "production": ProductionConfig,
        "testing": TestingConfig
    }

    config_class = config_classes.get(name, DevelopmentConfig)

    # Validate configuration
    is_valid = config_class.validate_config()
    if not is_valid:
        print("⚠️ Configuration validation failed!")

    print(f"🚀 Loading {name} configuration: {config_class.__name__}")
    return config_class

# Additional helper functions
def get_database_url():
    """Get database URL with fallback"""
    url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_URL")
    if not url:
        print("⚠️ No database URL configured")
    return url

def get_redis_url():
    """Get Redis URL for caching (if needed)"""
    return os.environ.get("REDIS_URL")

def is_production():
    """Check if running in production"""
    return os.environ.get("FLASK_ENV") == "production"

def is_development():
    """Check if running in development"""
    return os.environ.get("FLASK_ENV", "development") == "development"

# Export commonly used config values
__all__ = [
    'BaseConfig',
    'DevelopmentConfig', 
    'ProductionConfig',
    'TestingConfig',
    'get_config',
    'get_database_url',
    'get_redis_url',
    'is_production',
    'is_development'
]
