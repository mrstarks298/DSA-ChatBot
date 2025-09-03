# CRITICAL FIX: app/auth/routes.py - Fixed Session Management

import time
import secrets
import logging
from flask import request, session, redirect, jsonify, current_app, make_response, url_for
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
            redirect_uri = request.url_root.rstrip('/') + '/auth/oauth2callback'
        
        flow.redirect_uri = redirect_uri
        logger.debug(f"OAuth flow configured with redirect URI: {redirect_uri}")
        return flow

    except Exception as e:
        logger.error(f"Failed to create Google OAuth flow: {e}")
        return None

def _validate_session():
    """Relaxed session validation for OAuth compatibility"""
    try:
        # Check for required session data
        if 'google_id' not in session:
            logger.debug("No google_id in session")
            return False, "No active session"

        if 'login_time' not in session:
            logger.debug("No login_time in session")  
            return False, "Invalid session data"

        # Check session expiration
        session_age = time.time() - session.get('login_time', 0)
        max_age = current_app.config.get('PERMANENT_SESSION_LIFETIME')
        
        if hasattr(max_age, 'total_seconds'):
            max_age = max_age.total_seconds()
        else:
            max_age = 43200  # 12 hours default

        if session_age > max_age:
            logger.debug(f"Session expired: {session_age} > {max_age}")
            return False, "Session expired"

        logger.debug(f"Session valid for user: {session.get('email')}")
        return True, "Valid session"

    except Exception as e:
        logger.error(f"Session validation error: {e}")
        return False, "Session validation failed"

@bp.route('/login')
def login():
    """Initiate Google OAuth login flow with better error handling"""
    try:
        flow = _create_google_flow()
        if not flow:
            return jsonify({
                "error": "Authentication service unavailable",
                "message": "Google OAuth is not properly configured"
            }), 503

        # Store the 'next' URL for post-login redirect
        next_url = request.args.get('next', '/')
        session['next_url'] = next_url

        # Clear any existing session data
        session.clear()

        # Generate and store OAuth state for CSRF protection
        state = secrets.token_urlsafe(32)
        session['oauth_state'] = state
        session['oauth_start_time'] = time.time()

        # Generate authorization URL
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            state=state,
            prompt='select_account'  # Always show account selection
        )

        logger.info(f"🔐 Initiating OAuth flow")
        return redirect(auth_url)

    except Exception as e:
        logger.error(f"Login initiation error: {e}")
        return jsonify({
            "error": "Authentication failed",
            "message": "Unable to start authentication process"
        }), 500

@bp.route('/oauth2callback')
def oauth2callback():
    """✅ CRITICAL FIX: Handle OAuth2 callback with PROPER session creation"""
    try:
        # Validate OAuth state parameter
        state = request.args.get('state')
        session_state = session.get('oauth_state')
        
        if not state or not session_state or state != session_state:
            logger.warning("OAuth state mismatch - possible CSRF attack")
            return redirect(url_for('main.index') + '?error=invalid_state')

        # Check OAuth flow timeout (15 minutes max)
        oauth_start_time = session.get('oauth_start_time', 0)
        if time.time() - oauth_start_time > 900:  # 15 minutes
            logger.warning("OAuth flow expired")
            return redirect(url_for('main.index') + '?error=timeout')

        # Handle OAuth errors
        error = request.args.get('error')
        if error:
            logger.warning(f"OAuth error: {error}")
            error_description = request.args.get('error_description', 'Unknown error')
            return redirect(url_for('main.index') + f'?error={error}')

        # Create OAuth flow
        flow = _create_google_flow()
        if not flow:
            return redirect(url_for('main.index') + '?error=service_unavailable')

        # Exchange authorization code for tokens
        authorization_code = request.args.get('code')
        if not authorization_code:
            return redirect(url_for('main.index') + '?error=no_code')

        try:
            flow.fetch_token(authorization_response=request.url)
        except Exception as e:
            logger.error(f"Token exchange failed: {e}")
            return redirect(url_for('main.index') + '?error=token_exchange_failed')

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
            return redirect(url_for('main.index') + '?error=token_verification_failed')

        # Extract user information
        user_id = id_info.get('sub')
        email = id_info.get('email')
        name = id_info.get('name')
        picture = id_info.get('picture')

        if not user_id or not email:
            logger.error("Incomplete user information from Google")
            return redirect(url_for('main.index') + '?error=incomplete_user_info')

        # ✅ CRITICAL FIX: Create persistent session
        session.permanent = True  # Mark session as permanent
        session.modified = True   # Force session save
        
        # Store user information
        session['google_id'] = user_id
        session['email'] = email
        session['name'] = name
        session['picture'] = picture
        session['login_time'] = time.time()

        # Clear OAuth temporary data
        session.pop('oauth_state', None)
        session.pop('oauth_start_time', None)

        logger.info(f"✅ Session created for user: {email}")
        logger.info(f"✅ Session ID: {session.get('google_id')}")

        # Redirect to original destination or home
        next_url = session.pop('next_url', '/')
        
        # Validate redirect URL to prevent open redirects
        if next_url.startswith('http') and not next_url.startswith(request.host_url):
            next_url = '/'

        logger.info(f"✅ Redirecting authenticated user to: {next_url}")
        
        # Create response with success parameter
        response = make_response(redirect(next_url + ('&' if '?' in next_url else '?') + 'login=success'))
        return response

    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        return redirect(url_for('main.index') + '?error=callback_failed')

@bp.route('/logout', methods=['POST'])
def logout():
    """Logout user and clear session"""
    try:
        user_email = session.get('email', 'Unknown')
        
        # Clear session data
        session.clear()
        
        logger.info(f"🔐 User logged out: {user_email}")
        
        return jsonify({
            "message": "Logged out successfully",
            "redirect": "/"
        })

    except Exception as e:
        logger.error(f"Logout error: {e}")
        return jsonify({
            "error": "Logout failed",
            "message": "An error occurred during logout"
        }), 500

@bp.route('/auth-status')
def auth_status():
    """✅ IMPROVED: Get current authentication status"""
    try:
        logger.debug(f"Auth status check - session keys: {list(session.keys())}")
        
        is_valid, message = _validate_session()

        if is_valid:
            user_data = {
                "is_authenticated": True,
                "user_id": session.get('google_id'),
                "email": session.get('email'),
                "name": session.get('name'),
                "picture": session.get('picture'),
                "login_time": session.get('login_time'),
                "session_age": time.time() - session.get('login_time', 0)
            }

            logger.debug(f"✅ Auth status: User authenticated as {user_data['email']}")
            return jsonify(user_data)
        else:
            logger.debug(f"❌ Auth status: {message}")
            return jsonify({
                "is_authenticated": False,
                "message": message
            }), 401

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

@bp.route('/session-debug')
def session_debug():
    """Enhanced debug route to check session state"""
    try:
        session_data = {
            "has_session": bool(session),
            "session_keys": list(session.keys()),
            "google_id": session.get('google_id', 'None'),
            "email": session.get('email', 'None'),
            "name": session.get('name', 'None'),
            "login_time": session.get('login_time', 'None'),
            "session_age": time.time() - session.get('login_time', 0) if 'login_time' in session else 'N/A',
            "session_permanent": session.permanent,
            "session_new": session.new,
            "session_modified": session.modified
        }

        validation_result = _validate_session()
        
        config_info = {
            "cookie_name": current_app.config.get('SESSION_COOKIE_NAME'),
            "cookie_secure": current_app.config.get('SESSION_COOKIE_SECURE'),
            "cookie_httponly": current_app.config.get('SESSION_COOKIE_HTTPONLY'),
            "cookie_samesite": current_app.config.get('SESSION_COOKIE_SAMESITE'),
            "session_lifetime_hours": current_app.config.get('PERMANENT_SESSION_LIFETIME').total_seconds() / 3600,
            "session_protection": current_app.config.get('SESSION_PROTECTION'),
            "flask_env": current_app.config.get('FLASK_ENV')
        }

        cookie_info = {
            "has_session_cookie": current_app.config.get('SESSION_COOKIE_NAME') in request.cookies,
            "all_cookies": list(request.cookies.keys()),
            "user_agent": request.headers.get('User-Agent', 'None')[:100]
        }

        return jsonify({
            "timestamp": time.time(),
            "session_data": session_data,
            "validation_result": validation_result,
            "config_info": config_info,
            "cookie_info": cookie_info,
            "flask_version": getattr(__import__('flask'), '__version__', 'unknown')
        })

    except Exception as e:
        logger.error(f"Session debug error: {e}")
        return jsonify({"error": str(e)}), 500

# ✅ NEW: Session recovery endpoint
@bp.route('/session-recovery', methods=['POST'])
def session_recovery():
    """Attempt to recover lost session"""
    try:
        # Get session info from request
        recovery_data = request.get_json() or {}
        
        # Log recovery attempt
        logger.info(f"🔧 Session recovery attempt from: {request.remote_addr}")
        logger.info(f"Recovery data: {recovery_data.keys()}")
        
        # Check if session exists and is valid
        is_valid, message = _validate_session()
        
        if is_valid:
            return jsonify({
                "success": True,
                "message": "Session is already valid",
                "user": {
                    "email": session.get('email'),
                    "name": session.get('name'),
                    "is_authenticated": True
                }
            })
        else:
            return jsonify({
                "success": False,
                "message": "Session recovery failed",
                "reason": message,
                "action": "redirect_to_login"
            }), 401

    except Exception as e:
        logger.error(f"Session recovery error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# ✅ NEW: Health check for auth system
@bp.route('/health')
def auth_health():
    """Authentication system health check"""
    try:
        health_status = {
            "status": "healthy",
            "timestamp": time.time(),
            "services": {
                "google_oauth": bool(current_app.config.get("GOOGLE_CLIENT_ID") and 
                                   current_app.config.get("GOOGLE_CLIENT_SECRET")),
                "session_config": bool(current_app.config.get("SECRET_KEY")),
                "cors_config": bool(current_app.config.get("ALLOWED_ORIGINS"))
            },
            "config": {
                "session_cookie_samesite": current_app.config.get("SESSION_COOKIE_SAMESITE"),
                "session_cookie_secure": current_app.config.get("SESSION_COOKIE_SECURE"),
                "redirect_uri": current_app.config.get("REDIRECT_URI")
            }
        }

        # Check if any critical services are down
        if not all(health_status["services"].values()):
            health_status["status"] = "degraded"

        status_code = 200 if health_status["status"] == "healthy" else 503
        return jsonify(health_status), status_code

    except Exception as e:
        logger.error(f"Auth health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": time.time()
        }), 503

# Rate limiting (optional)
try:
    from ..extensions import limiter
    
    # Apply rate limiting using proper decorator syntax
    login = limiter.limit("10 per minute")(login)
    oauth2callback = limiter.limit("10 per minute")(oauth2callback)
    logout = limiter.limit("20 per minute")(logout)
    auth_status = limiter.limit("60 per minute")(auth_status)
    user_info = limiter.limit("30 per minute")(user_info)
    session_debug = limiter.limit("30 per minute")(session_debug)
    session_recovery = limiter.limit("10 per minute")(session_recovery)
    auth_health = limiter.limit("30 per minute")(auth_health)

except ImportError:
    logger.warning("Rate limiter not available - skipping rate limiting setup")
    pass
