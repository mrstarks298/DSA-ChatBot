# Updated app/auth/routes.py - Enhanced Authentication with Frontend Integration

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
        
        # Dynamic redirect URI configuration
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
    """Handle OAuth2 callback with enhanced error handling"""
    try:
        flow = _google_flow()
        if not flow:
            return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <title>Authentication Error</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
               background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
               margin: 0; padding: 20px; min-height: 100vh; display: flex; align-items: center; justify-content: center; }
        .error-container { background: white; padding: 40px; border-radius: 12px; box-shadow: 0 8px 32px rgba(0,0,0,0.1); 
                          text-align: center; max-width: 500px; }
        .error-icon { font-size: 48px; margin-bottom: 16px; }
        .error-title { font-size: 24px; color: #1f2937; margin-bottom: 16px; }
        .error-message { color: #6b7280; margin-bottom: 32px; line-height: 1.5; }
        .retry-btn { background: #1B7EFE; color: white; border: none; padding: 12px 24px; border-radius: 8px; 
                    font-size: 16px; cursor: pointer; text-decoration: none; display: inline-block; }
        .retry-btn:hover { background: #0056D2; }
    </style>
</head>
<body>
    <div class="error-container">
        <div class="error-icon">🔒</div>
        <h1 class="error-title">Authentication Configuration Error</h1>
        <p class="error-message">
            The authentication system is not properly configured. This could indicate a server issue.
        </p>
        <a href="/" class="retry-btn">← Return to Home</a>
    </div>
</body>
</html>
            """), 500
        
        # Validate OAuth state
        received_state = request.args.get('state')
        stored_state = session.pop('oauth_state', None)
        
        if not received_state or received_state != stored_state:
            logger.error("OAuth state validation failed")
            return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <title>Security Error</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
               background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
               margin: 0; padding: 20px; min-height: 100vh; display: flex; align-items: center; justify-content: center; }
        .error-container { background: white; padding: 40px; border-radius: 12px; box-shadow: 0 8px 32px rgba(0,0,0,0.1); 
                          text-align: center; max-width: 500px; }
        .error-icon { font-size: 48px; margin-bottom: 16px; }
        .error-title { font-size: 24px; color: #dc2626; margin-bottom: 16px; }
        .error-message { color: #6b7280; margin-bottom: 32px; line-height: 1.5; }
        .retry-btn { background: #1B7EFE; color: white; border: none; padding: 12px 24px; border-radius: 8px; 
                    font-size: 16px; cursor: pointer; text-decoration: none; display: inline-block; }
        .retry-btn:hover { background: #0056D2; }
    </style>
</head>
<body>
    <div class="error-container">
        <div class="error-icon">⚠️</div>
        <h1 class="error-title">Security Verification Failed</h1>
        <p class="error-message">
            Authentication state validation failed. This could indicate a security issue.
            <br><br>
            Please try logging in again.
        </p>
        <a href="/login" class="retry-btn">← Try Again</a>
    </div>
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
<head>
    <title>Session Timeout</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
               background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
               margin: 0; padding: 20px; min-height: 100vh; display: flex; align-items: center; justify-content: center; }
        .error-container { background: white; padding: 40px; border-radius: 12px; box-shadow: 0 8px 32px rgba(0,0,0,0.1); 
                          text-align: center; max-width: 500px; }
        .error-icon { font-size: 48px; margin-bottom: 16px; }
        .error-title { font-size: 24px; color: #f59e0b; margin-bottom: 16px; }
        .error-message { color: #6b7280; margin-bottom: 32px; line-height: 1.5; }
        .retry-btn { background: #1B7EFE; color: white; border: none; padding: 12px 24px; border-radius: 8px; 
                    font-size: 16px; cursor: pointer; text-decoration: none; display: inline-block; }
        .retry-btn:hover { background: #0056D2; }
    </style>
</head>
<body>
    <div class="error-container">
        <div class="error-icon">⏱️</div>
        <h1 class="error-title">Session Expired</h1>
        <p class="error-message">
            The authentication session has expired. Please try again.
        </p>
        <a href="/login" class="retry-btn">← Login Again</a>
    </div>
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
<head>
    <title>Authentication Error</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
               background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
               margin: 0; padding: 20px; min-height: 100vh; display: flex; align-items: center; justify-content: center; }
        .error-container { background: white; padding: 40px; border-radius: 12px; box-shadow: 0 8px 32px rgba(0,0,0,0.1); 
                          text-align: center; max-width: 500px; }
        .error-icon { font-size: 48px; margin-bottom: 16px; }
        .error-title { font-size: 24px; color: #dc2626; margin-bottom: 16px; }
        .error-message { color: #6b7280; margin-bottom: 32px; line-height: 1.5; }
        .retry-btn { background: #1B7EFE; color: white; border: none; padding: 12px 24px; border-radius: 8px; 
                    font-size: 16px; cursor: pointer; text-decoration: none; display: inline-block; }
        .retry-btn:hover { background: #0056D2; }
    </style>
</head>
<body>
    <div class="error-container">
        <div class="error-icon">❌</div>
        <h1 class="error-title">Authentication Failed</h1>
        <p class="error-message">
            {{ error_description }}
            <br><br>
            Please try logging in again or contact support.
        </p>
        <a href="/login" class="retry-btn">← Try Again</a>
    </div>
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
        
        # Success page with redirect for better UX
        return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <title>Login Successful</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="2;url={{ next_url }}">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
               background: linear-gradient(135deg, #10b981 0%, #059669 100%); 
               margin: 0; padding: 20px; min-height: 100vh; display: flex; align-items: center; justify-content: center; }
        .success-container { background: white; padding: 40px; border-radius: 12px; box-shadow: 0 8px 32px rgba(0,0,0,0.1); 
                           text-align: center; max-width: 500px; }
        .success-icon { font-size: 48px; margin-bottom: 16px; }
        .success-title { font-size: 24px; color: #059669; margin-bottom: 16px; }
        .success-message { color: #6b7280; margin-bottom: 32px; line-height: 1.5; }
        .continue-btn { background: #1B7EFE; color: white; border: none; padding: 12px 24px; border-radius: 8px; 
                       font-size: 16px; cursor: pointer; text-decoration: none; display: inline-block; }
        .continue-btn:hover { background: #0056D2; }
        .spinner { border: 2px solid #e5e7eb; border-top: 2px solid #1B7EFE; border-radius: 50%; 
                  width: 20px; height: 20px; animation: spin 1s linear infinite; margin: 0 auto; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div class="success-container">
        <div class="success-icon">✅</div>
        <h1 class="success-title">Welcome to DSA Mentor!</h1>
        <p class="success-message">
            You have successfully signed in as <strong>{{ user_name }}</strong>.
            <br><br>
            Redirecting you to the application...
        </p>
        <div class="spinner"></div>
        <br>
        <a href="{{ next_url }}" class="continue-btn">Continue</a>
    </div>
</body>
</html>
        """, next_url=next_url, user_name=id_info.get('name', 'User'))
        
    except Exception as e:
        logger.exception(f"OAuth callback error: {e}")
        return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <title>Unexpected Error</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
               background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%); 
               margin: 0; padding: 20px; min-height: 100vh; display: flex; align-items: center; justify-content: center; }
        .error-container { background: white; padding: 40px; border-radius: 12px; box-shadow: 0 8px 32px rgba(0,0,0,0.1); 
                          text-align: center; max-width: 500px; }
        .error-icon { font-size: 48px; margin-bottom: 16px; }
        .error-title { font-size: 24px; color: #dc2626; margin-bottom: 16px; }
        .error-message { color: #6b7280; margin-bottom: 32px; line-height: 1.5; }
        .error-details { background: #fef2f2; border: 1px solid #fecaca; border-radius: 6px; padding: 12px; 
                        font-size: 14px; color: #991b1b; margin-bottom: 24px; }
        .retry-btn { background: #1B7EFE; color: white; border: none; padding: 12px 24px; border-radius: 8px; 
                    font-size: 16px; cursor: pointer; text-decoration: none; display: inline-block; margin-right: 12px; }
        .retry-btn:hover { background: #0056D2; }
        .home-btn { background: #6b7280; color: white; border: none; padding: 12px 24px; border-radius: 8px; 
                   font-size: 16px; cursor: pointer; text-decoration: none; display: inline-block; }
        .home-btn:hover { background: #4b5563; }
    </style>
</head>
<body>
    <div class="error-container">
        <div class="error-icon">💥</div>
        <h1 class="error-title">Unexpected Error</h1>
        <p class="error-message">
            There was an unexpected error during authentication.
        </p>
        <div class="error-details">
            Error: {{ error_message }}
        </div>
        <p class="error-message">
            Please try again or contact support if the issue persists.
        </p>
        <a href="/login" class="retry-btn">🔄 Try Login Again</a>
        <a href="/" class="home-btn">🏠 Go Home</a>
    </div>
</body>
</html>
        """, error_message=str(e)), 500

@bp.route('/logout')
def logout():
    """Enhanced logout endpoint with better UX"""
    try:
        user_email = session.get('email', 'anonymous')
        
        # Clear all session data
        session.clear()
        
        logger.info(f"User logged out: {user_email}")
        
        # Redirect to home with logout success message
        return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <title>Logged Out</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="3;url=/">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
               background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
               margin: 0; padding: 20px; min-height: 100vh; display: flex; align-items: center; justify-content: center; }
        .logout-container { background: white; padding: 40px; border-radius: 12px; box-shadow: 0 8px 32px rgba(0,0,0,0.1); 
                           text-align: center; max-width: 500px; }
        .logout-icon { font-size: 48px; margin-bottom: 16px; }
        .logout-title { font-size: 24px; color: #1f2937; margin-bottom: 16px; }
        .logout-message { color: #6b7280; margin-bottom: 32px; line-height: 1.5; }
        .home-btn { background: #1B7EFE; color: white; border: none; padding: 12px 24px; border-radius: 8px; 
                   font-size: 16px; cursor: pointer; text-decoration: none; display: inline-block; }
        .home-btn:hover { background: #0056D2; }
    </style>
</head>
<body>
    <div class="logout-container">
        <div class="logout-icon">👋</div>
        <h1 class="logout-title">Successfully Logged Out</h1>
        <p class="logout-message">
            You have been safely logged out of DSA Mentor.
            <br><br>
            Thank you for learning with us!
            <br><br>
            Redirecting you to the home page...
        </p>
        <a href="/" class="home-btn">← Return to Home</a>
    </div>
</body>
</html>
        """)
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        return redirect('/')

# Session validation endpoint for frontend auth checks
@bp.route('/auth-status')
def auth_status():
    """Check current authentication status"""
    try:
        if 'google_id' in session:
            return jsonify({
                "is_authenticated": True,
                "user_id": session.get('google_id'),
                "name": session.get('name'),
                "email": session.get('email'),
                "picture": session.get('picture')
            })
        else:
            return jsonify({"is_authenticated": False})
    except Exception as e:
        logger.error(f"Auth status check error: {e}")
        return jsonify({"is_authenticated": False, "error": str(e)})


@bp.route('/validate-session')
def validate_session():
    """Validate current session - used by frontend for auth checks"""
    try:
        is_valid, reason = _is_session_valid()
        
        response_data = {
            'valid': is_valid,
            'reason': reason
        }
        
        if is_valid:
            response_data.update({
                'user_id': session.get('google_id'),
                'name': session.get('name'),
                'email': session.get('email'),
                'picture': session.get('picture'),
                'login_time': session.get('login_time')
            })
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Session validation error: {e}")
        return jsonify({
            'valid': False,
            'reason': 'Validation failed',
            'error': str(e)
        }), 500
