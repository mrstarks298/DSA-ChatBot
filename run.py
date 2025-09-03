# run.py - Production-ready entry point for DSA Mentor
import os
import logging
from app import create_app

# Configure logging for production
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log', mode='a')
    ]
)

logger = logging.getLogger(__name__)

def create_application():
    """Create and configure the Flask application"""
    try:
        # Get configuration from environment
        config_name = os.environ.get("FLASK_CONFIG", "production")
        
        # Create app with proper configuration
        app = create_app(config_name)
        
        # Log startup information
        logger.info(f"🚀 DSA Mentor starting with {config_name} configuration")
        logger.info(f"📊 Environment: {os.environ.get('FLASK_ENV', 'production')}")
        logger.info(f"🌐 Port: {os.environ.get('PORT', '50017')}")
        
        return app
        
    except Exception as e:
        logger.error(f"❌ Failed to create application: {e}")
        raise

# Create the application instance
app = create_application()

if __name__ == "__main__":
    try:
        # Get port from environment (Render sets PORT automatically)
        port = int(os.environ.get("PORT", 50017))
        
        # Get host (0.0.0.0 for production)
        host = os.environ.get("HOST", "0.0.0.0")
        
        # Determine if debug mode should be enabled
        debug_mode = os.environ.get("FLASK_ENV") == "development"
        
        logger.info(f"🎯 Starting server on {host}:{port}")
        logger.info(f"🔧 Debug mode: {debug_mode}")
        
        # Start the application
        app.run(
            host=host,
            port=port,
            debug=debug_mode,
            threaded=True,  # Enable threading for better performance
            use_reloader=debug_mode  # Only use reloader in development
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to start application: {e}")
        exit(1)