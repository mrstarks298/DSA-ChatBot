# config.py - Enhanced Configuration for DSA Mentor Production Deployment
import os
import logging
from datetime import timedelta
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class BaseConfig:
    """Base configuration class with common settings"""
    
    # Core Flask settings
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY")
    if not SECRET_KEY:
        raise ValueError("FLASK_SECRET_KEY environment variable is required")
    
    # Session configuration
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("FLASK_ENV") == "production"
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)
    
    # CORS configuration for frontend integration
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
    
    # Google OAuth configuration
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
    
    # Dynamic redirect URI with environment-based fallback
    REDIRECT_URI = os.environ.get(
        "REDIRECT_URI",
        "https://dsa-chatbot-3rll.onrender.com/oauth2callback"
    )
    
    # API URLs
    GROQ_CHAT_API_URL = "https://api.groq.com/openai/v1/chat/completions"
    
    # Application settings
    MAX_QUERY_LENGTH = int(os.environ.get("MAX_QUERY_LENGTH", "2000"))
    RATE_LIMIT_PER_MINUTE = int(os.environ.get("RATE_LIMIT_PER_MINUTE", "30"))
    STREAMING_ENABLED = os.environ.get("STREAMING_ENABLED", "true").lower() == "true"
    
    # Security settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hour
    
    # Logging configuration
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    
    # Template settings
    TEMPLATES_AUTO_RELOAD = False  # Disable in production
    
    # JSON settings
    JSONIFY_PRETTYPRINT_REGULAR = False
    JSON_SORT_KEYS = False
    
    # Redis configuration (optional for caching)
    REDIS_URL = os.environ.get("REDIS_URL")
    
    # Rate limiting configuration
    RATELIMIT_STORAGE_URL = REDIS_URL or "memory://"
    RATELIMIT_STRATEGY = "fixed-window"
    RATELIMIT_HEADERS_ENABLED = True
    
    @classmethod
    def validate_config(cls):
        """Validate required environment variables"""
        required_vars = [
            "SUPABASE_URL", "SUPABASE_KEY", "GROQ_API_KEY",
            "HF_API_TOKEN", "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"
        ]
        
        missing_vars = []
        for var in required_vars:
            if not getattr(cls, var):
                missing_vars.append(var)
        
        if missing_vars:
            logger.warning(f"⚠️ Missing environment variables: {', '.join(missing_vars)}")
            logger.warning("⚠️ Some features may not work without these variables")
            return False
        
        logger.info("✅ All required environment variables are configured")
        
        # Validate configurations
        if cls.ALLOWED_ORIGINS:
            origins = [o.strip() for o in cls.ALLOWED_ORIGINS.split(',')]
            logger.info(f"✅ CORS configured for origins: {origins}")
        
        if cls.GOOGLE_CLIENT_ID and cls.GOOGLE_CLIENT_SECRET:
            logger.info(f"✅ Google OAuth configured")
            logger.info(f"✅ OAuth redirect URI: {cls.REDIRECT_URI}")
        
        if cls.SUPABASE_URL and cls.SUPABASE_KEY:
            logger.info(f"✅ Supabase configured")
        
        if cls.GROQ_API_KEY:
            logger.info(f"✅ Groq API configured")
        
        if cls.HF_API_TOKEN:
            logger.info(f"✅ HuggingFace API configured")
            if cls.HF_API_TOKEN_BACKUP:
                logger.info(f"✅ HuggingFace backup token available")
        
        if cls.REDIS_URL:
            logger.info(f"✅ Redis configured for caching and rate limiting")
        else:
            logger.info("ℹ️ Using in-memory rate limiting (Redis recommended for production)")
        
        return True


class DevelopmentConfig(BaseConfig):
    """Development configuration with relaxed settings"""
    
    DEBUG = True
    OAUTHLIB_INSECURE_TRANSPORT = "1"  # Allow HTTP for OAuth in development
    
    # More permissive settings for development
    SESSION_COOKIE_SECURE = False
    MAX_QUERY_LENGTH = 5000
    RATE_LIMIT_PER_MINUTE = 100
    TEMPLATES_AUTO_RELOAD = True
    JSONIFY_PRETTYPRINT_REGULAR = True
    
    # Extended session for development
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    
    # Development CORS (more permissive)
    ALLOWED_ORIGINS = os.environ.get(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5000,http://127.0.0.1:5000"
    )
    
    # Development redirect URI
    REDIRECT_URI = os.environ.get(
        "REDIRECT_URI",
        "http://localhost:5000/oauth2callback"
    )


class ProductionConfig(BaseConfig):
    """Production configuration with enhanced security"""
    
    DEBUG = False
    
    # Enhanced security for production
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    
    # Stricter settings
    MAX_QUERY_LENGTH = 1500
    RATE_LIMIT_PER_MINUTE = 20
    
    # Production session settings
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)
    
    # Production CORS (restrictive)
    ALLOWED_ORIGINS = os.environ.get(
        "ALLOWED_ORIGINS",
        "https://dsa-chatbot-3rll.onrender.com"
    )
    
    # Enhanced logging for production
    LOG_LEVEL = "WARNING"


class TestingConfig(BaseConfig):
    """Testing configuration"""
    
    TESTING = True
    DEBUG = True
    WTF_CSRF_ENABLED = False  # Disable CSRF for testing
    
    # Test-specific settings
    SESSION_COOKIE_SECURE = False
    OAUTHLIB_INSECURE_TRANSPORT = "1"
    
    # Test overrides
    MAX_QUERY_LENGTH = 1000
    RATE_LIMIT_PER_MINUTE = 1000  # No rate limiting in tests
    
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
    
    config_class = config_classes.get(name, ProductionConfig)
    
    # Validate configuration
    config_class.validate_config()
    logger.info(f"🚀 Loading {name} configuration: {config_class.__name__}")
    
    return config_class


# Helper functions
def get_database_url():
    """Get database URL with fallback"""
    url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_URL")
    if not url:
        logger.warning("⚠️ No database URL configured")
    return url


def get_redis_url():
    """Get Redis URL for caching"""
    return os.environ.get("REDIS_URL")


def is_production():
    """Check if running in production"""
    return os.environ.get("FLASK_ENV") == "production"


def is_development():
    """Check if running in development"""
    return os.environ.get("FLASK_ENV", "production") == "development"


# Export commonly used values
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