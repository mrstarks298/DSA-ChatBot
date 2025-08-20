


# Initialize immediately instead of waiting for init_extensions

import logging
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()  # load .env variables

logger = logging.getLogger("dsa-mentor")

# Get Supabase credentials from environment variables
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

if not url or not key:
    logger.error("SUPABASE_URL and SUPABASE_KEY environment variables are required")
    supabase = None
else:
    logger.info(f"Initializing Supabase with URL: {url[:20]}...")
    logger.info("Supabase key is configured")

    try:
        supabase: Client = create_client(url, key)
        logger.info("Supabase client created successfully")
    except Exception as e:
        logger.error(f"Failed to create Supabase client: {e}")
        supabase = None

def init_extensions(app):
    """Additional app-specific initialization"""
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO)
    logger.setLevel(logging.INFO)

    if app.config.get("OAUTHLIB_INSECURE_TRANSPORT"):
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    
    global supabase
    logger.info(f"init_extensions called - supabase initialized: {supabase is not None}")
    
    if supabase is None:
        logger.error("CRITICAL: Supabase client is still None after initialization!")
    
