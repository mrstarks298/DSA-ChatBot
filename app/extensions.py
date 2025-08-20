


# Initialize immediately instead of waiting for init_extensions

import logging
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()  # load .env variables

logger = logging.getLogger("dsa-mentor")

# Get Supabase credentials from environment variables
url = os.environ.get("SUPABASE_URL", "https://tsuwpbunvavtygtnsypm.supabase.co")
key = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRzdXdwYnVudmF2dHlndG5zeXBtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTQ4MTkyODIsImV4cCI6MjA3MDM5NTI4Mn0.oUl9B1cZWWu4uE4m5fKdkmlpXN3Gqe9Cj6Gsc4rJJ8g")

print(f"DEBUG: Initializing Supabase with URL: {url}")
print(f"DEBUG: Supabase key is set: {bool(key)}")

try:
    supabase: Client = create_client(url, key)
    print("DEBUG: Supabase client created successfully")
except Exception as e:
    print(f"ERROR: Failed to create Supabase client: {e}")
    supabase = None

def init_extensions(app):
    """Additional app-specific initialization"""
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO)
    logger.setLevel(logging.INFO)

    if app.config.get("OAUTHLIB_INSECURE_TRANSPORT"):
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    
    global supabase
    print(f"DEBUG: init_extensions called - supabase is None: {supabase is None}")
    
    if supabase is None:
        logger.error("CRITICAL: Supabase client is still None after initialization!")
    
