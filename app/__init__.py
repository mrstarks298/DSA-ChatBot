from dotenv import load_dotenv
load_dotenv()


from flask import Flask
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
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
        response.headers.add("Access-Control-Allow-Methods", "GET,PUT,POST,DELETE,OPTIONS")
        return response

    return app
