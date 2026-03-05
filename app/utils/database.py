"""Database connection and helper utilities."""
import mysql.connector
import traceback
from functools import wraps
from flask import jsonify, request, session
from app.config import Config


def get_db_connection(config_obj=None):
    """Create and return a database connection."""
    if config_obj is None:
        config_obj = Config()
    return mysql.connector.connect(**config_obj.db_config)


def ensure_connection_alive(conn, config_obj=None):
    """Ensure database connection is alive, reconnect if needed."""
    try:
        if conn is None or not getattr(conn, "is_connected", lambda: False)():
            return get_db_connection(config_obj)
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        cur.close()
        return conn
    except Exception:
        return get_db_connection(config_obj)


def log_error_db(username, endpoint, err_msg, tb_text, config_obj=None):
    """
    Attempt to write the error to the error_logs table using a fresh connection.
    This is best-effort — if it fails we print to console.
    """
    try:
        conn = get_db_connection(config_obj)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS error_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(150),
                endpoint VARCHAR(255),
                error_message TEXT,
                traceback LONGTEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute(
            "INSERT INTO error_logs (username, endpoint, error_message, traceback) VALUES (%s, %s, %s, %s)",
            (username, endpoint, err_msg, tb_text)
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        # best-effort: print if we cannot write to DB
        print("⚠️ log_error_db failed:", e)
        print("Original error:", err_msg)
        print(tb_text)


def with_db_connection(func):
    """Decorator to provide database connection to route handlers."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        conn = None
        cursor = None
        try:
            from flask import current_app
            config_obj = current_app.config.get("CONFIG_OBJ")
            conn = ensure_connection_alive(get_db_connection(config_obj), config_obj)
            cursor = conn.cursor(dictionary=True, buffered=True)
            return func(cursor, conn, *args, **kwargs)
        except Exception as e:
            tb = traceback.format_exc()
            print("🔥 DB Error (route):", e)
            print(tb)
            # attempt to log to DB (username & endpoint best-effort)
            username = session.get("username") if isinstance(session, dict) or session else None
            endpoint = request.path if request else None
            try:
                from flask import current_app
                config_obj = current_app.config.get("CONFIG_OBJ")
                log_error_db(username, endpoint, str(e), tb, config_obj)
            except Exception:
                # swallow
                pass
            return jsonify({"error": "Internal server error"}), 500
        finally:
            try:
                if cursor:
                    cursor.close()
            except Exception:
                pass
            try:
                if conn:
                    conn.close()
            except Exception:
                pass
    return wrapper

