# FIXED app/auth/routes.py - Authentication Error Handling and Security

import time
import secrets
from . import bp
from flask import request, session, redirect, jsonify, current_app, render_template_string, make_response
from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
from google.auth.transport import requests as google_auth_requests
import logging

logger = logging.getLogger("dsa-mentor")

def _google_flow():
    """Create Google OAuth flow with proper error handling"""
    try:
        client_id = current_app.config.get("GOOGLE_CLIENT_ID")
        client_secret = current_app.config.get("GOOGLE_CLIENT_SECRET")
        
        if not client_id or not client_secret:
            logger.error("Google OAuth credentials not configured")
            return None

        flow = Flow.from_client_config(
            {"web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/v2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }},
            scopes=[
                "https://www.googleapis.com/auth/userinfo.email",
                "https://www.googleapis.com/auth/userinfo.profile",
                "openid"
            ]
        )

        # FIXED: Dynamic redirect URI configuration
        redirect_uri = current_app.config.get("REDIRECT_URI")
        if not redirect_uri:
            # Fallback to auto-detect for development
            redirect_uri = request.url_root.rstrip('/') + '/oauth2callback'
        
        flow.redirect_uri = redirect_uri
        logger.info(f"OAuth flow configured with redirect URI: {redirect_uri}")
        return flow

    except Exception as e:
        logger.error(f"Google flow creation error: {e}")
        return None

def _is_session_valid():
    """Validate user session with improved error handling"""
    try:
        if 'google_id' not in session:
            return (False, "No session")
        
        if 'login_time' not in session:
            return (False, "No login timestamp")
        
        # Check session expiration
        session_age = time.time() - session.get('login_time', 0)
        max_age = current_app.config.get('PERMANENT_SESSION_LIFETIME', 3600)
        if hasattr(max_age, 'total_seconds'):
            max_age = max_age.total_seconds()
        
        if session_age > max_age:
            return (False, "Session expired")
        
        return (True, "Valid")
    
    except Exception as e:
        logger.error(f"Session validation error: {e}")
        return (False, "Session validation failed")

@bp.route('/login')
def login():
    """Initiate Google OAuth login flow"""
    try:
        flow = _google_flow()
        if not flow:
            return jsonify({"error": "Google authentication is not configured"}), 500

    except Exception as e:
        logger.error(f"Login initialization error: {e}")
        return jsonify({"error": "Authentication service unavailable"}), 500

    # Store the 'next' URL parameter for redirect after login
    next_url = request.args.get('next')
    if next_url:
        session['next_url'] = next_url

    # Clear any existing session data before starting new auth flow
    session.pop('google_id', None)
    session.pop('oauth_state', None)
    session.pop('oauth_start_time', None)

    # Generate and store OAuth state for security
    state = secrets.token_urlsafe(32)
    session['oauth_state'] = state
    session['oauth_start_time'] = time.time()

    auth_url, _ = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        state=state,
        prompt='select_account'
    )

    logger.info(f"Redirecting user to OAuth URL: {auth_url[:100]}...")
    return redirect(auth_url)

@bp.route('/oauth2callback')
def oauth2callback():
    """Handle OAuth2 callback with FIXED error handling"""
    try:
        flow = _google_flow()
        if not flow:
            # FIXED: Proper error template with defined variables
            return render_template_string("""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Authentication Error</title>
                    <style>
                        body { 
                            font-family: Arial, sans-serif; 
                            text-align: center; 
                            padding: 50px; 
                            background: #f5f5f5; 
                        }
                        .error-container {
                            background: white;
                            padding: 40px;
                            border-radius: 10px;
                            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                            max-width: 500px;
                            margin: 0 auto;
                        }
                        .error-title { color: #e74c3c; margin-bottom: 20px; }
                        .error-message { color: #666; margin-bottom: 30px; }
                        .home-link { 
                            color: #1B7EFE; 
                            text-decoration: none; 
                            font-weight: bold;
                            padding: 10px 20px;
                            border: 2px solid #1B7EFE;
                            border-radius: 5px;
                            display: inline-block;
                        }
                        .home-link:hover { background: #1B7EFE; color: white; }
                    </style>
                </head>
                <body>
                    <div class="error-container">
                        <h1 class="error-title">🔒 Authentication Error</h1>
                        <p class="error-message">
                            Google authentication is not properly configured. 
                            Please contact support or try again later.
                        </p>
                        <a href="/" class="home-link">← Return to Home</a>
                    </div>
                </body>
                </html>
            """), 500

        # Validate OAuth state to prevent CSRF attacks
        returned_state = request.args.get('state')
        stored_state = session.pop('oauth_state', None)
        
        if not returned_state or returned_state != stored_state:
            logger.error("OAuth state mismatch - possible CSRF attack")
            return render_template_string("""
                <!DOCTYPE html>
                <html>
                <head><title>Security Error</title></head>
                <body style="font-family: Arial; text-align: center; padding: 50px;">
                    <h1 style="color: #e74c3c;">🛡️ Security Error</h1>
                    <p>Authentication state validation failed. This could indicate a security issue.</p>
                    <p>Please try logging in again.</p>
                    <a href="/login" style="color: #1B7EFE; text-decoration: none;">← Try Again</a>
                </body>
                </html>
            """), 400

        # Check OAuth session timeout (10 minutes)
        oauth_start_time = session.pop('oauth_start_time', None)
        if oauth_start_time and (time.time() - oauth_start_time) > 600:
            logger.error("OAuth session timeout")
            return render_template_string("""
                <!DOCTYPE html>
                <html>
                <head><title>Session Timeout</title></head>
                <body style="font-family: Arial; text-align: center; padding: 50px;">
                    <h1 style="color: #f39c12;">⏰ Session Timeout</h1>
                    <p>The authentication session has expired. Please try again.</p>
                    <a href="/login" style="color: #1B7EFE; text-decoration: none;">← Login Again</a>
                </body>
                </html>
            """), 408

        # Handle OAuth errors
        error = request.args.get('error')
        if error:
            logger.error(f"OAuth error: {error}")
            error_description = request.args.get('error_description', 'Authentication failed')
            
            return render_template_string("""
                <!DOCTYPE html>
                <html>
                <head><title>OAuth Error</title></head>
                <body style="font-family: Arial; text-align: center; padding: 50px;">
                    <h1 style="color: #e74c3c;">❌ OAuth Error</h1>
                    <p>{{ error_description }}</p>
                    <p>Please try logging in again or contact support.</p>
                    <a href="/login" style="color: #1B7EFE; text-decoration: none;">← Try Again</a>
                </body>
                </html>
            """, error_description=error_description), 400

        # Exchange authorization code for tokens
        flow.fetch_token(authorization_response=request.url)

        # Get user info from Google
        credentials = flow.credentials
        request_session = google_auth_requests.Request()
        
        id_info = id_token.verify_oauth2_token(
            credentials.id_token, 
            request_session, 
            current_app.config["GOOGLE_CLIENT_ID"]
        )

        # Store user information in session
        session.permanent = True
        session['google_id'] = id_info.get('sub')
        session['name'] = id_info.get('name')
        session['email'] = id_info.get('email')
        session['picture'] = id_info.get('picture')
        session['login_time'] = time.time()

        logger.info(f"User {id_info.get('email')} logged in successfully")

        # Redirect to next URL or home
        next_url = session.pop('next_url', '/')
        return redirect(next_url)

    except Exception as e:
        logger.exception(f"OAuth callback error: {e}")
        
        # FIXED: Comprehensive error handling with proper template
        return render_template_string("""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Authentication Failed</title>
                <style>
                    body { 
                        font-family: Arial, sans-serif; 
                        text-align: center; 
                        padding: 50px; 
                        background: #f8f9fa; 
                    }
                    .error-box {
                        background: white;
                        padding: 30px;
                        border-radius: 8px;
                        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                        max-width: 400px;
                        margin: 0 auto;
                    }
                </style>
            </head>
            <body>
                <div class="error-box">
                    <h1 style="color: #dc3545;">🚫 Authentication Failed</h1>
                    <p>There was an unexpected error during authentication.</p>
                    <p>Error: {{ error_message }}</p>
                    <p>Please try again or contact support if the issue persists.</p>
                    <a href="/login" style="color: #007bff; text-decoration: none;">
                        🔄 Try Login Again
                    </a>
                    <br><br>
                    <a href="/" style="color: #6c757d; text-decoration: none;">
                        🏠 Go Home
                    </a>
                </div>
            </body>
            </html>
        """, error_message=str(e)[:100]), 500

@bp.route('/logout')
def logout():
    """Log out user and clear session"""
    try:
        email = session.get('email', 'Unknown user')
        logger.info(f"User {email} logged out")
        
        # Clear all session data
        session.clear()
        
        return redirect('/')
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        # Even if logout fails, clear session and redirect
        session.clear()
        return redirect('/')

@bp.route('/auth/status')
def auth_status():
    """Check authentication status - useful for frontend"""
    try:
        is_valid, message = _is_session_valid()
        
        if is_valid:
            return jsonify({
                "authenticated": True,
                "user": {
                    "name": session.get('name'),
                    "email": session.get('email'),
                    "picture": session.get('picture')
                }
            })
        else:
            return jsonify({
                "authenticated": False,
                "message": message
            })
            
    except Exception as e:
        logger.error(f"Auth status check error: {e}")
        return jsonify({
            "authenticated": False,
            "message": "Status check failed"
        }), 500
