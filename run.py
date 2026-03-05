"""
Application entry point.
"""

from app import create_app

def main():
    app = create_app()

    # -------------------------------------------------
    # ✅ Login config
    # -------------------------------------------------
    app.config.update(
        SESSION_COOKIE_PATH="/",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=False,  ##have to set true when we go for https##
    )

    # -------------------------------------------------
    
    # -------------------------------------------------
    # app.config['APPLICATION_ROOT'] = '/Code'
    # app.config['SESSION_COOKIE_PATH'] = '/Code'

    # -------------------------------------------------
    # 🚀 RUN SERVER
    # -------------------------------------------------
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )

if __name__ == "__main__":
    main()
