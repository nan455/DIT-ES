from flask import Flask, session, request, make_response
from datetime import timedelta
import os
import secrets
from app.routes.report import report_bp



def create_app(config_object=None):
    """Create Flask app with proper session configuration."""
    app = Flask(__name__)
    
    #  CRITICAL FIX 1: Unique secret key for each instance
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    
    #  CRITICAL FIX 2: Session configuration
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_PERMANENT'] = False
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
    # app.config['SESSION_COOKIE_NAME'] = 'esp_session_' + secrets.token_hex(4)  # Unique per restart
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
    app.config['SESSION_REFRESH_EACH_REQUEST'] = False
    
    #  Store config object
    if config_object:
        app.config['CONFIG_OBJ'] = config_object
    
    #  CRITICAL FIX 3: Add response headers to prevent caching
    @app.after_request
    def add_header(response):
        """Add headers to prevent caching of user-specific data."""
        # Don't cache API responses or HTML pages
        if not request.path.startswith('/static/'):
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
        return response
    
    #  CRITICAL FIX 4: Clear session on any authentication error
    @app.errorhandler(401)
    def unauthorized(error):
        """Clear session on unauthorized access."""
        session.clear()
        return make_response({"error": "Unauthorized"}, 401)
    
    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.data import data_bp
    from app.routes.admin import admin_bp
    from app.routes.api import api_bp
    from app.routes.approver import approver_bp
    from app.routes.grievance_routes import grievance_bp
    from app.routes.statistics_routes import statistics_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(data_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(approver_bp)
    app.register_blueprint(report_bp)
    app.register_blueprint(grievance_bp)
    app.register_blueprint(statistics_bp)

    #  Debug middleware (remove in production)
    @app.before_request
    def log_session_info():
        """Log session info for debugging."""
        if request.endpoint and not request.endpoint.startswith('static'):
            if 'username' in session:
                print(f"🔍 {request.method} {request.path} | User: {session.get('username')} | Dept: {session.get('department')}")
    
    return app