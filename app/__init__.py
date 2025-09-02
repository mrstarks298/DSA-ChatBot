# FIXED app/__init__.py - CORS Configuration and Security Improvements

from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request
from .config import get_config
from .extensions import init_extensions
from .main import bp as main_bp
from .auth import bp as auth_bp

def create_app(config_name="development"):
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(get_config(config_name))
    
    init_extensions(app)
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    
    @app.after_request
    def add_cors_headers(response):
        """FIXED: Environment-based CORS configuration"""
        origin = request.headers.get('Origin')
        
        if origin:
            # Get allowed origins from config (comma-separated string)
            allowed_origins_str = app.config.get('ALLOWED_ORIGINS', '')
            allowed_origins = [o.strip() for o in allowed_origins_str.split(',') if o.strip()]
            
            # Allow in debug mode or if origin is in allowed list
            if app.config.get('DEBUG') or origin in allowed_origins:
                response.headers.add("Access-Control-Allow-Origin", origin)
                response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
                response.headers.add("Access-Control-Allow-Methods", "GET,PUT,POST,DELETE,OPTIONS")
                response.headers.add("Access-Control-Allow-Credentials", "true")
        
        return response
    
    @app.before_request
    def handle_preflight():
        """Handle CORS preflight requests"""
        if request.method == "OPTIONS":
            response = make_response()
            origin = request.headers.get('Origin')
            
            if origin:
                allowed_origins_str = app.config.get('ALLOWED_ORIGINS', '')
                allowed_origins = [o.strip() for o in allowed_origins_str.split(',') if o.strip()]
                
                if app.config.get('DEBUG') or origin in allowed_origins:
                    response.headers.add("Access-Control-Allow-Origin", origin)
                    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
                    response.headers.add("Access-Control-Allow-Methods", "GET,PUT,POST,DELETE,OPTIONS")
                    response.headers.add("Access-Control-Allow-Credentials", "true")
            
            return response
    
    @app.errorhandler(404)
    def not_found(error):
        """Custom 404 handler"""
        return jsonify({"error": "Endpoint not found"}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """Custom 500 handler"""
        return jsonify({"error": "Internal server error"}), 500
    
    @app.route('/health')
    def health_check():
        """Health check endpoint for monitoring"""
        return jsonify({
            "status": "healthy",
            "timestamp": time.time(),
            "config": config_name
        })
    
    return app
