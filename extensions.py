# extensions.py - Database and External Services Configuration
import logging
import os
from typing import Optional
from supabase import create_client, Client
from dotenv import load_dotenv
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Load environment variables
load_dotenv()

logger = logging.getLogger("dsa-mentor")


class SupabaseService:
    """Singleton service for Supabase database operations"""
    
    _instance: Optional['SupabaseService'] = None
    _client: Optional[Client] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SupabaseService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._initialize()
            self._initialized = True
    
    def _initialize(self):
        """Initialize Supabase client"""
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        
        if not url or not key:
            logger.error("SUPABASE_URL and SUPABASE_KEY environment variables are required")
            self._client = None
            return
        
        try:
            self._client = create_client(url, key)
            logger.info(f"✅ Supabase client initialized successfully")
            logger.info(f"🔗 Connected to: {url[:30]}...")
        except Exception as e:
            logger.error(f"❌ Failed to create Supabase client: {e}")
            self._client = None
    
    @property
    def client(self) -> Optional[Client]:
        """Get the Supabase client instance"""
        return self._client
    
    def is_connected(self) -> bool:
        """Check if Supabase client is connected"""
        return self._client is not None
    
    def get_table(self, table_name: str):
        """Get a table reference"""
        if not self.is_connected():
            raise RuntimeError("Supabase client not connected")
        return self._client.table(table_name)
    
    def health_check(self) -> bool:
        """Perform a health check on the database connection"""
        try:
            if not self.is_connected():
                return False
            
            # Try a simple query to verify connection
            result = self._client.table("text_embeddings").select("id").limit(1).execute()
            return True
            
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


class CacheService:
    """Simple in-memory cache for embeddings and API responses"""
    
    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        self.cache = {}
        self.max_size = max_size
        self.ttl = ttl
        
    def get(self, key: str):
        """Get item from cache"""
        import time
        
        if key in self.cache:
            data, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return data
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, value):
        """Set item in cache"""
        import time
        import hashlib
        
        # Clean cache if at max capacity
        if len(self.cache) >= self.max_size:
            # Remove oldest entry
            oldest_key = min(self.cache.keys(), 
                           key=lambda k: self.cache[k][1])
            del self.cache[oldest_key]
        
        self.cache[key] = (value, time.time())
    
    def clear(self):
        """Clear all cache entries"""
        self.cache.clear()
    
    def size(self) -> int:
        """Get current cache size"""
        return len(self.cache)


# Global service instances
supabase_service = SupabaseService()
cache_service = CacheService()

# Flask extensions
cors = CORS()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["1000 per day", "100 per hour"],
    storage_uri="memory://",
    strategy="fixed-window"
)


def init_extensions(app):
    """Initialize Flask extensions with app context"""
    
    # Configure logging
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=getattr(logging, app.config.get('LOG_LEVEL', 'INFO')),
            format='%(asctime)s %(levelname)s %(name)s %(message)s'
        )
    
    logger.setLevel(getattr(logging, app.config.get('LOG_LEVEL', 'INFO')))
    
    # OAuth insecure transport for development
    if app.config.get("OAUTHLIB_INSECURE_TRANSPORT"):
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
        logger.info("🔓 OAuth insecure transport enabled for development")
    
    # Initialize CORS
    cors.init_app(app, 
                  origins=app.config.get('ALLOWED_ORIGINS', '').split(','),
                  supports_credentials=True,
                  allow_headers=['Content-Type', 'Authorization'],
                  methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
    logger.info("✅ CORS initialized")
    
    # Initialize rate limiter
    try:
        # Use Redis if available, otherwise fall back to in-memory
        redis_url = app.config.get('REDIS_URL') or app.config.get('RATELIMIT_STORAGE_URL')
        if redis_url and redis_url != "memory://":
            limiter.storage_uri = redis_url
            logger.info("✅ Rate limiter initialized with Redis")
        else:
            logger.info("ℹ️ Rate limiter using in-memory storage")
            
        limiter.init_app(app)
        
    except Exception as e:
        logger.warning(f"⚠️ Rate limiter initialization failed: {e}")
    
    # Verify services
    logger.info(f"🔗 Supabase service connected: {supabase_service.is_connected()}")
    
    if not supabase_service.is_connected():
        logger.error("❌ CRITICAL: Supabase client is not connected!")
        
    # Perform health checks
    try:
        if supabase_service.health_check():
            logger.info("✅ Database health check passed")
        else:
            logger.warning("⚠️ Database health check failed")
    except Exception as e:
        logger.error(f"❌ Database health check error: {e}")
    
    logger.info(f"📊 Cache service initialized (max size: {cache_service.max_size})")
    logger.info("🎯 All extensions initialized successfully")


def get_supabase_client() -> Optional[Client]:
    """Get Supabase client (backward compatibility)"""
    return supabase_service.client


def get_cache() -> CacheService:
    """Get cache service"""
    return cache_service


# Export for backward compatibility
supabase = supabase_service.client