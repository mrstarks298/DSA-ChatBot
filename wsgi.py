# wsgi.py - WSGI entry point for production deployment
import os
import logging
from app import create_app

# Configure logging for production WSGI
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s'
)

logger = logging.getLogger(__name__)

def create_wsgi_application():
    """Create WSGI application for production"""
    try:
        # Always use production config for WSGI
        config_name = os.environ.get("FLASK_CONFIG", "production")
        
        # Create the application
        application = create_app(config_name)
        
        logger.info(f"🚀 WSGI application created with {config_name} configuration")
        
        return application
        
    except Exception as e:
        logger.error(f"❌ Failed to create WSGI application: {e}")
        raise

# Create the WSGI application instance
application = create_wsgi_application()

# For Gunicorn compatibility
if __name__ == "__main__":
    application.run()
