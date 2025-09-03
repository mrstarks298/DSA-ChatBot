# app/__init__.py - Enhanced Flask Application Factory

import os
import time
import logging
from flask import Flask, request, jsonify, make_response, render_template, session
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
        config_class = get_config(config_name)
        app.config.from_object(config_class)

        # ✅ CRITICAL: Configure session settings directly
        app.config['SESSION_COOKIE_HTTPONLY'] = True
        app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
        app.config['SESSION_COOKIE_SECURE'] = os.environ.get("FLASK_ENV") == "production"
        app.config['SESSION_PROTECTION'] = None  # Disable for OAuth compatibility
        
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
    """Register application blueprints with error handling"""
    try:
        # Import and register auth blueprint
        from .auth import bp as auth_bp
        app.register_blueprint(auth_bp, url_prefix='/auth')
        logger.info("✅ Auth blueprint registered")

        # Import and register main blueprint
        from .main import bp as main_bp
        app.register_blueprint(main_bp)
        logger.info("✅ Main blueprint registered")

        logger.info("✅ All blueprints registered successfully")

    except Exception as e:
        logger.error(f"❌ Failed to register blueprints: {e}")
        raise

def configure_error_handlers(app):
    """Configure enhanced error handlers"""
    
    @app.errorhandler(400)
    def bad_request(error):
        if request.path.startswith('/api/') or request.is_json:
            return jsonify({
                "error": "Bad request",
                "message": "The request could not be understood by the server",
                "code": 400
            }), 400
        return render_template('error.html', error_code=400, error_message="Bad Request"), 400

    @app.errorhandler(401)
    def unauthorized(error):
        if request.path.startswith('/api/') or request.is_json:
            return jsonify({
                "error": "Unauthorized",
                "message": "Authentication is required to access this resource",
                "code": 401
            }), 401
        return render_template('error.html', error_code=401, error_message="Unauthorized"), 401

    @app.errorhandler(403)
    def forbidden(error):
        if request.path.startswith('/api/') or request.is_json:
            return jsonify({
                "error": "Forbidden",
                "message": "You don't have permission to access this resource",
                "code": 403
            }), 403
        return render_template('error.html', error_code=403, error_message="Forbidden"), 403

    @app.errorhandler(404)
    def not_found(error):
        if request.path.startswith('/api/') or request.is_json:
            return jsonify({
                "error": "Not found",
                "message": "The requested resource was not found",
                "code": 404
            }), 404
        
        try:
            return render_template('404.html'), 404
        except:
            return jsonify({"error": "Page not found"}), 404

    @app.errorhandler(429)
    def ratelimit_handler(error):
        return jsonify({
            "error": "Rate limit exceeded",
            "message": "Too many requests. Please try again later.",
            "retry_after": getattr(error, 'retry_after', None),
            "code": 429
        }), 429

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {error}")
        if request.path.startswith('/api/') or request.is_json:
            return jsonify({
                "error": "Internal server error",
                "message": "An unexpected error occurred",
                "code": 500
            }), 500
        return render_template('error.html', error_code=500, error_message="Internal Server Error"), 500

    @app.errorhandler(503)
    def service_unavailable(error):
        return jsonify({
            "error": "Service unavailable",
            "message": "The service is temporarily unavailable",
            "code": 503
        }), 503

    logger.info("✅ Enhanced error handlers configured")

def configure_middleware(app):
    """Configure enhanced application middleware"""
    
    @app.before_request
    def log_request_info():
        """Enhanced request logging"""
        if app.config.get('DEBUG'):
            logger.debug(f"📝 {request.method} {request.path}")
            logger.debug(f"🍪 Cookies: {list(request.cookies.keys())}")
            
            if request.is_json and request.json:
                logger.debug(f"📦 Request data: {request.json}")

    @app.before_request
    def ensure_session_config():
        """Ensure session configuration is applied"""
        if hasattr(session, 'permanent') and not session.permanent and 'google_id' in session:
            session.permanent = True
            session.modified = True

    @app.before_request
    def handle_preflight():
        """Enhanced CORS preflight handling"""
        if request.method == "OPTIONS":
            response = make_response()
            origin = request.headers.get('Origin')
            
            if origin:
                allowed_origins = app.config.get('ALLOWED_ORIGINS', [])
                if isinstance(allowed_origins, str):
                    allowed_origins = allowed_origins.split(',')
                
                allowed_origins = [o.strip() for o in allowed_origins if o.strip()]
                
                if app.config.get('DEBUG') or origin in allowed_origins:
                    response.headers['Access-Control-Allow-Origin'] = origin
                    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization,X-Requested-With'
                    response.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS'
                    response.headers['Access-Control-Allow-Credentials'] = 'true'
                    response.headers['Access-Control-Max-Age'] = '86400'
                    
            return response

    @app.after_request
    def add_security_headers(response):
        """Enhanced security headers"""
        # Basic security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        # Add HSTS in production
        if app.config.get('SESSION_COOKIE_SECURE'):
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

        # Enhanced Content Security Policy
        if not app.config.get('DEBUG'):
            csp = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://accounts.google.com https://apis.google.com; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                "font-src 'self' https://fonts.gstatic.com; "
                "img-src 'self' data: https: blob:; "
                "connect-src 'self' https: wss:; "
                "frame-src https://accounts.google.com https://www.youtube.com; "
                "object-src 'none'; "
                "base-uri 'self';"
            )
            response.headers['Content-Security-Policy'] = csp

        return response

    @app.after_request  
    def add_cors_headers(response):
        """Enhanced CORS headers with session support"""
        origin = request.headers.get('Origin')
        
        if origin:
            allowed_origins = app.config.get('ALLOWED_ORIGINS', [])
            if isinstance(allowed_origins, str):
                allowed_origins = allowed_origins.split(',')
            
            allowed_origins = [o.strip() for o in allowed_origins if o.strip()]
            
            if app.config.get('DEBUG') or origin in allowed_origins:
                response.headers['Access-Control-Allow-Origin'] = origin
                response.headers['Access-Control-Allow-Credentials'] = 'true'
                response.headers['Vary'] = 'Origin'

        return response

    logger.info("✅ Enhanced middleware configured")

def add_utility_routes(app, config_name):
    """Add enhanced utility routes"""
    
    @app.route('/health')
    def health_check():
        """Enhanced application health check"""
        try:
            from .extensions import supabase_service

            health_status = {
                "status": "healthy",
                "timestamp": time.time(),
                "config": config_name,
                "version": "2.1.0",
                "services": {
                    "database": supabase_service.is_connected(),
                    "cache": True,
                    "auth": bool(app.config.get('GOOGLE_CLIENT_ID') and app.config.get('GOOGLE_CLIENT_SECRET')),
                    "session": bool(app.config.get('SECRET_KEY'))
                },
                "session_info": {
                    "cookie_name": app.config.get('SESSION_COOKIE_NAME'),
                    "cookie_samesite": app.config.get('SESSION_COOKIE_SAMESITE'),
                    "cookie_secure": app.config.get('SESSION_COOKIE_SECURE'),
                    "lifetime_hours": app.config.get('PERMANENT_SESSION_LIFETIME').total_seconds() / 3600
                }
            }

            # Check if any critical services are down
            critical_services = ['database', 'auth', 'session']
            if not all(health_status["services"][service] for service in critical_services):
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
        """Enhanced version information"""
        return jsonify({
            "name": "DSA Mentor",
            "version": "2.1.0",
            "config": config_name,
            "python_version": os.sys.version,
            "flask_version": getattr(__import__('flask'), '__version__', 'unknown'),
            "features": {
                "oauth_enabled": bool(app.config.get('GOOGLE_CLIENT_ID')),
                "streaming_enabled": app.config.get('STREAMING_ENABLED', True),
                "cors_enabled": bool(app.config.get('ALLOWED_ORIGINS'))
            }
        })

    @app.route('/')
    def index():
        """Enhanced main application page"""
        try:
            # Check if user is authenticated
            is_authenticated = 'google_id' in session and session.get('email')
            
            # Prepare user data for frontend
            user_data = {
                "is_authenticated": is_authenticated,
                "email": session.get('email'),
                "name": session.get('name'),
                "picture": session.get('picture'),
                "user_id": session.get('google_id')
            } if is_authenticated else {"is_authenticated": False}

            # Check for login success parameter
            login_success = request.args.get('login') == 'success'
            login_error = request.args.get('error')

            return render_template('index.html', 
                                 user=user_data, 
                                 login_success=login_success,
                                 login_error=login_error,
                                 config={
                                     'streaming_enabled': app.config.get('STREAMING_ENABLED', True),
                                     'max_query_length': app.config.get('MAX_QUERY_LENGTH', 2000)
                                 })

        except Exception as e:
            logger.error(f"Failed to render index template: {e}")
            return jsonify({
                "message": "DSA Mentor API is running",
                "version": "2.1.0",
                "status": "healthy",
                "endpoints": {
                    "health": "/health",
                    "version": "/version", 
                    "auth": "/auth/login",
                    "chat": "/chat",
                    "auth_status": "/auth/auth-status"
                }
            })

    logger.info("✅ Enhanced utility routes added")

# Export the create_app function
__all__ = ['create_app']
