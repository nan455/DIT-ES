"""Application configuration settings."""
import os


class Config:
    """Base configuration class."""
    SECRET_KEY = os.environ.get("SECRET_KEY") or "supersecretkey"
    
    # Database configuration
    DB_HOST = os.environ.get("DB_HOST") or "127.0.0.1"
    DB_USER = os.environ.get("DB_USER") or "root"
    DB_PASSWORD = os.environ.get("DB_PASSWORD") or "nanda"
    DB_NAME = os.environ.get("DB_NAME") or "ESP_STG_DB"
    DB_PORT = 3306
    #DB_PORT = int(os.environ.get("DB_PORT") or 3308)
    
    # Folder paths
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER") or "uploads"
    TEMPLATE_FOLDER = os.environ.get("TEMPLATE_FOLDER") or "templates_excel"
    
    # CORS enabled
    CORS_ENABLED = True
    
    # Session settings
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour in seconds
    SESSION_COOKIE_DOMAIN=None
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_SAMESITE = 'Lax'  # or 'Strict' for more security
    #APPLICATION_ROOT = None  # Set to '/Code' if app is served under /Code
    SESSION_COOKIE_PATH = '/'  # Will be set based on APPLICATION_ROOT

    @property
    def db_config(self):
        """Return database configuration dictionary."""
        return {
            "host": self.DB_HOST,
            "user": self.DB_USER,
            "password": self.DB_PASSWORD,
            "database": self.DB_NAME,
            "autocommit": True,
        }


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    # For development,serve from root
    APPLICATION_ROOT = None
    SESSION_COOKIE_PATH = None


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    APPLICATION_ROOT = '/Code'
    SESSION_COOKIE_PATH = '/Code'


# Configuration mapping
config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}

