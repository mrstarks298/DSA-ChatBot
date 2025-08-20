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
        # Only allow requests from your own domain in production
        origin = request.headers.get('Origin')
        if origin and (app.config.get('DEBUG') or origin.startswith('https://dsa-chatbot-3rll.onrender.com')):
            response.headers.add("Access-Control-Allow-Origin", origin)
        response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
        response.headers.add("Access-Control-Allow-Methods", "GET,PUT,POST,DELETE,OPTIONS")
        response.headers.add("Access-Control-Allow-Credentials", "true")
        return response

    return app
