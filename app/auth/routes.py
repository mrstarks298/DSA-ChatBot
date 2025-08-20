import time, secrets
from . import bp
from flask import request, session, redirect, jsonify, current_app, render_template_string
from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
from google.auth.transport import requests as google_auth_requests
import logging
logger = logging.getLogger("dsa-mentor")

def _google_flow():
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
        # FIXED: Ensure redirect URI matches your Flask app and Google Console
        redirect_uri = current_app.config.get("REDIRECT_URI")
        if not redirect_uri:
            # Fallback to auto-detect for development
            redirect_uri = request.url_root.rstrip('/') + '/oauth2callback'
        flow.redirect_uri = redirect_uri
        return flow
    except Exception as e:
        logger.error(f"Google flow creation error: {e}")
        return None

def _is_session_valid():
    try:
        if 'google_id' not in session:
            return (False, "No session")
        if 'login_time' not in session:
            return (False, "No login timestamp")
        if time.time() - session.get('login_time', 0) > 3600:
            return (False, "Session expired")
        return (True, "Valid")
    except Exception as e:
        logger.error(f"Session validation error: {e}")
        return (False, "Session validation failed")

@bp.route('/login')
def login():
    try:
        # FIX: Use correct function name with underscore
        flow = _google_flow()  # Changed from google_flow() to _google_flow()
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
    
    state = secrets.token_urlsafe(32)
    session['oauth_state'] = state
    session['oauth_start_time'] = time.time()
    
    auth_url, _ = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        state=state,
        prompt='select_account'
    )
    return redirect(auth_url)

@bp.route('/oauth2callback')
def oauth2callback():
    try:
        flow = _google_flow()
        if not flow:
            return render_template_string("""
            <script>
            alert('Authentication is not available.');
            localStorage.removeItem('user_data');
            window.location.href = '/';
            </script>
            """)
    except Exception as e:
        logger.error(f"OAuth callback initialization error: {e}")
        return render_template_string("""
        <script>
        alert('Authentication initialization failed.');
        localStorage.removeItem('user_data');
        window.location.href = '/';
        </script>
        """)
    
    try:
        # Better error handling and debugging
        state_from_session = session.get('oauth_state')
        state_from_request = request.args.get('state')
        
        if not state_from_session:
            raise ValueError("No OAuth state in session - please try logging in again")
        if not state_from_request:
            raise ValueError("No state parameter in callback - authentication failed")
        if state_from_session != state_from_request:
            raise ValueError("Invalid authentication state - possible CSRF attack")
        
        if time.time() - session.get('oauth_start_time', 0) > 300:
            raise ValueError("Authentication flow expired - please try again")
        
        # Better error handling for token fetch
        try:
            flow.fetch_token(authorization_response=request.url)
        except Exception as e:
            raise ValueError(f"Failed to fetch token: {str(e)}")
        
        creds = flow.credentials
        if not creds._id_token:
            raise ValueError("No ID token received from Google")
        
        idinfo = id_token.verify_oauth2_token(
            id_token=creds._id_token,
            request=google_auth_requests.Request(),
            audience=current_app.config["GOOGLE_CLIENT_ID"]
        )
        
        if not idinfo.get('sub') or not idinfo.get('email'):
            raise ValueError("Missing required user information from Google")

        # Clear temporary session data first
        session.pop('oauth_state', None)
        session.pop('oauth_start_time', None)
        
        # Get the next URL before updating session
        next_url = session.pop('next_url', '/')
        
        # Set session configuration
        session.permanent = True
        current_app.permanent_session_lifetime = 3600  # 1 hour
        
        session.update({
            'google_id': idinfo.get('sub'),
            'name': idinfo.get('name', 'User'),
            'email': idinfo.get('email'),
            'picture': idinfo.get('picture', ''),
            'login_time': time.time(),
            'token_expires': time.time() + 3600
        })

        logger.info(f"User {idinfo.get('email')} logged in successfully")

        # FIXED: Redirect to the next URL (shared chat) after login
        return render_template_string("""
        <script>
          // Clear any existing data
          localStorage.removeItem('user_data');
          sessionStorage.removeItem('auth_change');
          
          // Set user data
          const userData = {
            authenticated: true, 
            name: "{{name}}", 
            email: "{{email}}", 
            picture: "{{picture}}",
            loginTime: {{login}}
          };
          localStorage.setItem('user_data', JSON.stringify(userData));
          
          // Force page reload to update authentication state
          setTimeout(() => {
            window.location.href = "{{next_url}}";
          }, 100);
        </script>
        """, 
        name=idinfo.get('name', '').replace('"', '\\"'),
        email=idinfo.get('email', '').replace('"', '\\"'),
        picture=idinfo.get('picture', '').replace('"', '\\"'),
        login=int(time.time()),
        next_url=next_url)
        
    except Exception as e:
        logger.error(f"OAuth callback error: {str(e)}")
        # Clean up session on error
        session.pop('oauth_state', None)
        session.pop('oauth_start_time', None)
        session.pop('google_id', None)
        
        return render_template_string("""
        <script>
          localStorage.removeItem('user_data');
          console.error('Authentication error: {{error}}');
          alert('Authentication failed: {{error}}. Please try again.');
          setTimeout(() => {
            window.location.href = '/';
          }, 100);
        </script>
        """, error=str(e).replace("'", "\\'").replace('"', '\\"'))

# FIXED: Add both API and regular logout endpoints for JS compatibility
@bp.route('/api/logout', methods=['POST'])
def api_logout():
    try:
        email = session.get('email', 'unknown')
        session.clear()
        logger.info(f"User {email} logged out via API")
        return jsonify({
            'success': True, 
            'message': 'Logged out successfully', 
            'action': 'clear_storage'
        })
    except Exception as e:
        logger.exception("API logout error")
        return jsonify({'success': False, 'error': 'Logout failed'}), 500

@bp.route('/logout', methods=['GET', 'POST'])  # FIXED: Accept both GET and POST
def logout():
    try:
        email = session.get('email', 'unknown')
        session.clear()
        logger.info(f"User {email} logged out")
        return render_template_string("""
        <script>
        localStorage.clear(); 
        sessionStorage.clear(); 
        setTimeout(() => {
          window.location.href = '/';
        }, 100);
        </script>
        """)
    except Exception as e:
        logger.error(f"Logout error: {e}")
        return render_template_string("""
        <script>
        localStorage.clear(); 
        sessionStorage.clear(); 
        window.location.href = '/';
        </script>
        """)

@bp.route('/api/check-auth')
def check_auth():
    try:
        ok, reason = _is_session_valid()
        if not ok:
            logger.debug(f"Auth check failed: {reason}")
            session.clear()
            return jsonify({
                'authenticated': False, 
                'action': 'clear_storage',
                'reason': reason
            })
        return jsonify({
            'authenticated': True, 
            'user': {
                'name': session.get('name'),
                'email': session.get('email'),
                'picture': session.get('picture'),
                'loginTime': session.get('login_time')
            }, 
            'sessionValid': True
        })
    except Exception as e:
        logger.exception("Auth check error")
        session.clear()
        return jsonify({
            'authenticated': False, 
            'action': 'clear_storage',
            'error': str(e)
        }), 500

@bp.route('/auth-status')  # FIXED: Keep this for JS compatibility
def auth_status():
    try:
        ok, reason = _is_session_valid()
        response_data = {
            'is_authenticated': ok, 
            'user_id': session.get('google_id') if ok else None
        }
        if not ok:
            response_data['reason'] = reason
        return jsonify(response_data)
    except Exception as e:
        logger.error(f"Auth status error: {e}")
        return jsonify({
            'is_authenticated': False,
            'error': 'Authentication check failed'
        }), 500
