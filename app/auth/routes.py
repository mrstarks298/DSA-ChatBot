# app/auth/routes.py - Enhanced Authentication Routes with Production Optimizations
import time
import secrets
import logging
from flask import request, session, redirect, jsonify, current_app, make_response
from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
from google.auth.transport import requests as google_auth_requests

from . import bp

logger = logging.getLogger("dsa-mentor")


def _create_google_flow():
    """Create Google OAuth flow with comprehensive error handling"""
    try:
        client_id = current_app.config.get("GOOGLE_CLIENT_ID")
        client_secret = current_app.config.get("GOOGLE_CLIENT_SECRET")
        
        if not client_id or not client_secret:
            logger.error("Google OAuth credentials not configured")
            return None
        
        # Create OAuth flow configuration
        client_config = {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/v2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [current_app.config.get("REDIRECT_URI")]
            }
        }
        
        flow = Flow.from_client_config(
            client_config,
            scopes=[
                "https://www.googleapis.com/auth/userinfo.email",
                "https://www.googleapis.com/auth/userinfo.profile",
                "openid"
            ]
        )
        
        # Set redirect URI
        redirect_uri = current_app.config.get("REDIRECT_URI")
        if not redirect_uri:
            # Fallback for development
            redirect_uri = request.url_root.rstrip('/') + '/auth/oauth2callback'
        
        flow.redirect_uri = redirect_uri
        
        logger.debug(f"OAuth flow configured with redirect URI: {redirect_uri}")
        return flow
        
    except Exception as e:
        logger.error(f"Failed to create Google OAuth flow: {e}")
        return None


def _validate_session():
    """Validate user session with enhanced security checks"""
    try:
        # Check for required session data
        if 'google_id' not in session:
            return False, "No active session"
        
        if 'login_time' not in session:
            return False, "Invalid session data"
        
        # Check session expiration
        session_age = time.time() - session.get('login_time', 0)
        max_age = current_app.config.get('PERMANENT_SESSION_LIFETIME')
        
        if hasattr(max_age, 'total_seconds'):
            max_age = max_age.total_seconds()
        else:
            max_age = 7200  # 2 hours default
        
        if session_age > max_age:
            return False, "Session expired"
        
        # Additional security checks
        user_agent = session.get('user_agent')
        current_user_agent = request.headers.get('User-Agent', '')
        
        if user_agent and user_agent != current_user_agent:
            logger.warning(f"User agent mismatch for user {session.get('email')}")
            return False, "Session security violation"
        
        return True, "Valid session"
        
    except Exception as e:
        logger.error(f"Session validation error: {e}")
        return False, "Session validation failed"


@bp.route('/login')
def login():
    """Initiate Google OAuth login flow"""
    try:
        flow = _create_google_flow()
        if not flow:
            return jsonify({
                "error": "Authentication service unavailable",
                "message": "Google OAuth is not properly configured"
            }), 503
        
        # Store the 'next' URL for post-login redirect
        next_url = request.args.get('next')
        if next_url:
            session['next_url'] = next_url
        
        # Clear any existing session data
        session.pop('google_id', None)
        session.pop('oauth_state', None)
        session.pop('oauth_start_time', None)
        
        # Generate and store OAuth state for CSRF protection
        state = secrets.token_urlsafe(32)
        session['oauth_state'] = state
        session['oauth_start_time'] = time.time()
        
        # Store user agent for session validation
        session['user_agent'] = request.headers.get('User-Agent', '')
        
        # Generate authorization URL
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            state=state,
            prompt='select_account'  # Always show account selection
        )
        
        logger.info(f"🔐 Initiating OAuth flow for new user")
        return redirect(auth_url)
        
    except Exception as e:
        logger.error(f"Login initiation error: {e}")
        return jsonify({
            "error": "Authentication failed",
            "message": "Unable to start authentication process"
        }), 500


@bp.route('/oauth2callback')
def oauth2callback():
    """Handle OAuth2 callback with enhanced security and error handling"""
    try:
        # Validate OAuth state parameter
        state = request.args.get('state')
        session_state = session.get('oauth_state')
        
        if not state or not session_state or state != session_state:
            logger.warning("OAuth state mismatch - possible CSRF attack")
            return jsonify({
                "error": "Authentication failed",
                "message": "Invalid authentication state"
            }), 400
        
        # Check OAuth flow timeout (15 minutes max)
        oauth_start_time = session.get('oauth_start_time', 0)
        if time.time() - oauth_start_time > 900:  # 15 minutes
            logger.warning("OAuth flow expired")
            return jsonify({
                "error": "Authentication timeout",
                "message": "Authentication process took too long"
            }), 400
        
        # Handle OAuth errors
        error = request.args.get('error')
        if error:
            logger.warning(f"OAuth error: {error}")
            error_description = request.args.get('error_description', 'Unknown error')
            return jsonify({
                "error": "Authentication failed",
                "message": f"OAuth error: {error_description}"
            }), 400
        
        # Create OAuth flow
        flow = _create_google_flow()
        if not flow:
            return jsonify({
                "error": "Authentication service unavailable"
            }), 503
        
        # Exchange authorization code for tokens
        authorization_code = request.args.get('code')
        if not authorization_code:
            return jsonify({
                "error": "Authentication failed",
                "message": "No authorization code received"
            }), 400
        
        try:
            flow.fetch_token(authorization_response=request.url)
        except Exception as e:
            logger.error(f"Token exchange failed: {e}")
            return jsonify({
                "error": "Authentication failed", 
                "message": "Failed to exchange authorization code"
            }), 400
        
        # Get user info from Google
        credentials = flow.credentials
        request_session = google_auth_requests.Request()
        
        try:
            id_info = id_token.verify_oauth2_token(
                credentials.id_token,
                request_session,
                current_app.config.get("GOOGLE_CLIENT_ID")
            )
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            return jsonify({
                "error": "Authentication failed",
                "message": "Failed to verify user identity"
            }), 400
        
        # Extract user information
        user_id = id_info.get('sub')
        email = id_info.get('email')
        name = id_info.get('name')
        picture = id_info.get('picture')
        
        if not user_id or not email:
            logger.error("Incomplete user information from Google")
            return jsonify({
                "error": "Authentication failed",
                "message": "Incomplete user information"
            }), 400
        
        # Create secure session
        session.permanent = True
        session['google_id'] = user_id
        session['email'] = email
        session['name'] = name
        session['picture'] = picture
        session['login_time'] = time.time()
        
        # Clear OAuth temporary data
        session.pop('oauth_state', None)
        session.pop('oauth_start_time', None)
        
        logger.info(f"✅ User authenticated successfully: {email}")
        
        # Redirect to original destination or home
        next_url = session.pop('next_url', '/')
        
        # Validate redirect URL to prevent open redirects
        if next_url.startswith('http') and not next_url.startswith(request.host_url):
            next_url = '/'
        
        return redirect(next_url)
        
    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        return jsonify({
            "error": "Authentication failed",
            "message": "An unexpected error occurred during authentication"
        }), 500


@bp.route('/logout', methods=['POST'])
def logout():
    """Logout user and clear session"""
    try:
        user_email = session.get('email', 'Unknown')
        
        # Clear session data
        session.clear()
        
        logger.info(f"🔐 User logged out: {user_email}")
        
        return jsonify({
            "message": "Logged out successfully"
        })
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        return jsonify({
            "error": "Logout failed",
            "message": "An error occurred during logout"
        }), 500


@bp.route('/auth-status')
def auth_status():
    """Get current authentication status"""
    try:
        is_valid, message = _validate_session()
        
        if is_valid:
            return jsonify({
                "is_authenticated": True,
                "user_id": session.get('google_id'),
                "email": session.get('email'),
                "name": session.get('name'),
                "picture": session.get('picture'),
                "login_time": session.get('login_time')
            })
        else:
            # Clear invalid session
            session.clear()
            
            return jsonify({
                "is_authenticated": False,
                "message": message
            })
            
    except Exception as e:
        logger.error(f"Auth status check error: {e}")
        return jsonify({
            "is_authenticated": False,
            "error": "Unable to verify authentication status"
        }), 500


@bp.route('/user-info')
def user_info():
    """Get detailed user information (requires authentication)"""
    try:
        is_valid, message = _validate_session()
        
        if not is_valid:
            return jsonify({
                "error": "Authentication required",
                "message": message
            }), 401
        
        return jsonify({
            "user_id": session.get('google_id'),
            "email": session.get('email'), 
            "name": session.get('name'),
            "picture": session.get('picture'),
            "login_time": session.get('login_time'),
            "session_age": time.time() - session.get('login_time', 0)
        })
        
    except Exception as e:
        logger.error(f"User info error: {e}")
        return jsonify({
            "error": "Unable to retrieve user information"
        }), 500


# Rate limiting decorator for sensitive endpoints
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from ..extensions import limiter

# Apply rate limiting to authentication endpoints
login.decorators.append(limiter.limit("10 per minute"))
oauth2callback.decorators.append(limiter.limit("10 per minute"))
logout.decorators.append(limiter.limit("20 per minute"))
