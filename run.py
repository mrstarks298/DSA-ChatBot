from app import create_app
import os

app = create_app(os.environ.get("FLASK_CONFIG", "development"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 50017))
    app.run(host="0.0.0.0", port=port, debug=app.config.get("DEBUG", False))