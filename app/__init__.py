# app/__init__.py - Flask Application Factory with Enhanced Features
import os
import time
import logging
from flask import Flask, request, jsonify, make_response, render_template
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

logger = logging.getLogger(__name__)


def create_app(config_name="production"):
    """Create and configure the Flask application"""
    
    # Create Flask app
    app = Flask(__name__, 
                template_folder="templates", 
                static_folder="static",
                instance_relative_config=True)
    
    try:
        # Load configuration
        from .config import get_config
        app.config.from_object(get_config(config_name))
        
        # Initialize extensions
        from .extensions import init_extensions
        init_extensions(app)
        
        # Register blueprints
        register_blueprints(app)
        
        # Configure error handlers
        configure_error_handlers(app)
        
        # Configure middleware
        configure_middleware(app)
        
        # Add utility routes
        add_utility_routes(app, config_name)
        
        logger.info(f"🎯 Flask application created successfully with {config_name} config")
        
    except Exception as e:
        logger.error(f"❌ Failed to create Flask application: {e}")
        raise
    
    return app


def register_blueprints(app):
    """Register application blueprints"""
    try:
        # Import and register auth blueprint
        from .auth import bp as auth_bp
        app.register_blueprint(auth_bp, url_prefix='/auth')
        
        # Import and register main blueprint
        from .main import bp as main_bp
        app.register_blueprint(main_bp)
        
        logger.info("✅ Blueprints registered successfully")
        
    except Exception as e:
        logger.error(f"❌ Failed to register blueprints: {e}")
        raise


def configure_error_handlers(app):
    """Configure custom error handlers"""
    
    @app.errorhandler(400)
    def bad_request(error):
        """Handle bad request errors"""
        return jsonify({
            "error": "Bad request",
            "message": "The request could not be understood by the server"
        }), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        """Handle unauthorized errors"""
        return jsonify({
            "error": "Unauthorized",
            "message": "Authentication is required to access this resource"
        }), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        """Handle forbidden errors"""
        return jsonify({
            "error": "Forbidden", 
            "message": "You don't have permission to access this resource"
        }), 403
    
    @app.errorhandler(404)
    def not_found(error):
        """Handle not found errors"""
        if request.path.startswith('/api/') or request.is_json:
            return jsonify({
                "error": "Not found",
                "message": "The requested resource was not found"
            }), 404
        
        # Render HTML page for non-API requests
        try:
            return render_template('404.html'), 404
        except:
            return jsonify({"error": "Page not found"}), 404
    
    @app.errorhandler(429)
    def ratelimit_handler(error):
        """Handle rate limit exceeded errors"""
        return jsonify({
            "error": "Rate limit exceeded",
            "message": "Too many requests. Please try again later.",
            "retry_after": getattr(error, 'retry_after', None)
        }), 429
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle internal server errors"""
        logger.error(f"Internal server error: {error}")
        
        return jsonify({
            "error": "Internal server error",
            "message": "An unexpected error occurred"
        }), 500
    
    @app.errorhandler(503)
    def service_unavailable(error):
        """Handle service unavailable errors"""
        return jsonify({
            "error": "Service unavailable",
            "message": "The service is temporarily unavailable"
        }), 503
    
    logger.info("✅ Error handlers configured")


def configure_middleware(app):
    """Configure application middleware"""
    
    @app.before_request
    def log_request_info():
        """Log request information"""
        if not app.config.get('DEBUG'):
            return
        
        logger.debug(f"📝 {request.method} {request.path}")
        if request.is_json and request.json:
            logger.debug(f"📦 Request data: {request.json}")
    
    @app.before_request
    def handle_preflight():
        """Handle CORS preflight requests"""
        if request.method == "OPTIONS":
            response = make_response()
            
            # Get origin from request
            origin = request.headers.get('Origin')
            
            if origin:
                # Check if origin is allowed
                allowed_origins_str = app.config.get('ALLOWED_ORIGINS', '')
                allowed_origins = [o.strip() for o in allowed_origins_str.split(',') if o.strip()]
                
                if app.config.get('DEBUG') or origin in allowed_origins:
                    response.headers['Access-Control-Allow-Origin'] = origin
                    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization,X-Requested-With'
                    response.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS'
                    response.headers['Access-Control-Allow-Credentials'] = 'true'
                    response.headers['Access-Control-Max-Age'] = '86400'  # 24 hours
            
            return response
    
    @app.after_request
    def add_security_headers(response):
        """Add security headers to all responses"""
        
        # Security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Add HSTS in production
        if app.config.get('SESSION_COOKIE_SECURE'):
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        # Content Security Policy (basic)
        if not app.config.get('DEBUG'):
            csp = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://accounts.google.com; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                "font-src 'self' https://fonts.gstatic.com; "
                "img-src 'self' data: https:; "
                "connect-src 'self' https:; "
                "frame-src https://accounts.google.com;"
            )
            response.headers['Content-Security-Policy'] = csp
        
        return response
    
    @app.after_request
    def add_cors_headers(response):
        """Add CORS headers to responses"""
        origin = request.headers.get('Origin')
        
        if origin:
            allowed_origins_str = app.config.get('ALLOWED_ORIGINS', '')
            allowed_origins = [o.strip() for o in allowed_origins_str.split(',') if o.strip()]
            
            if app.config.get('DEBUG') or origin in allowed_origins:
                response.headers['Access-Control-Allow-Origin'] = origin
                response.headers['Access-Control-Allow-Credentials'] = 'true'
        
        return response
    
    logger.info("✅ Middleware configured")


def add_utility_routes(app, config_name):
    """Add utility routes for monitoring and health checks"""
    
    @app.route('/health')
    def health_check():
        """Application health check endpoint"""
        try:
            from .extensions import supabase_service
            
            health_status = {
                "status": "healthy",
                "timestamp": time.time(),
                "config": config_name,
                "version": "2.0.0",
                "services": {
                    "database": supabase_service.is_connected(),
                    "cache": True  # Always available with in-memory fallback
                }
            }
            
            # Check if any critical services are down
            if not all(health_status["services"].values()):
                health_status["status"] = "degraded"
            
            status_code = 200 if health_status["status"] == "healthy" else 503
            
            return jsonify(health_status), status_code
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return jsonify({
                "status": "unhealthy",
                "timestamp": time.time(),
                "error": str(e)
            }), 503
    
    @app.route('/version')
    def version_info():
        """Application version information"""
        return jsonify({
            "name": "DSA Mentor",
            "version": "2.0.0",
            "config": config_name,
            "python_version": os.sys.version,
            "flask_version": getattr(__import__('flask'), '__version__', 'unknown')
        })
    
    @app.route('/')
    def index():
        """Main application page"""
        try:
            return render_template('index.html')
        except Exception as e:
            logger.error(f"Failed to render index template: {e}")
            return jsonify({
                "message": "DSA Mentor API is running",
                "version": "2.0.0",
                "endpoints": {
                    "health": "/health",
                    "version": "/version",
                    "auth": "/auth/login",
                    "chat": "/chat"
                }
            })
    
    logger.info("✅ Utility routes added")


# Export the create_app function
__all__ = ['create_app']