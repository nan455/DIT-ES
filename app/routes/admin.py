"""Admin routes for user management, templates, and permissions."""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session, send_file
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
import json
import os
import traceback
from app.utils.database import with_db_connection, log_error_db
from flask import current_app

admin_bp = Blueprint("admin", __name__)


def require_admin(f):
    """Decorator to require admin role."""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("role") != "admin":
            return redirect(url_for("auth.login_page"))
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route("/admin_dashboard")
def admin_dashboard():
    """Admin dashboard page."""
    if "username" not in session:
        return redirect(url_for("auth.login_page"))
    return render_template("admin_dashboard.html")


@admin_bp.route("/users", methods=["GET"])
@with_db_connection
def admin_get_users(cursor, conn):
    """Get all users (admin only)."""
    cursor.execute(
        "SELECT id, username, department, role, created_by "
        "FROM users ORDER BY id DESC"
    )
    return jsonify(cursor.fetchall())


@admin_bp.route("/users", methods=["POST"])
@with_db_connection
def admin_add_user(cursor, conn):
    """Add a new user (admin only)."""
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    department = data.get("department")
    role = data.get("role", "user")

    if not username or not password or not department:
        return jsonify({"error": "Missing fields"}), 400

    hashed = generate_password_hash(password)

    cursor.execute(
        """
        INSERT INTO users (username, password, department, role, created_by)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (username, hashed, department, role, session.get("username")),
    )
    conn.commit()

    return jsonify({"message": "User added"})


@admin_bp.route("/users/<int:uid>", methods=["PUT"])
@with_db_connection
def admin_edit_user(cursor, conn, uid):
    """Edit an existing user (admin only)."""
    data = request.get_json()

    sets = []
    vals = []

    if "username" in data:
        sets.append("username=%s")
        vals.append(data["username"])

    if "password" in data and data["password"]:
        hashed = generate_password_hash(data["password"])
        sets.append("password=%s")
        vals.append(hashed)

    if "department" in data:
        sets.append("department=%s")
        vals.append(data["department"])

    if "role" in data:
        sets.append("role=%s")
        vals.append(data["role"])

    if not sets:
        return jsonify({"error": "Nothing to update"}), 400

    vals.append(uid)
    sql = f"UPDATE users SET {', '.join(sets)} WHERE id=%s"
    cursor.execute(sql, tuple(vals))
    conn.commit()

    return jsonify({"message": "User updated"})


@admin_bp.route("/users/<int:uid>", methods=["DELETE"])
@with_db_connection
def admin_delete_user(cursor, conn, uid):
    """Delete a user (admin only)."""
    cursor.execute("DELETE FROM users WHERE id=%s", (uid,))
    conn.commit()
    return jsonify({"message": "User deleted"})


@admin_bp.route("/templates", methods=["GET"])
@with_db_connection
def get_templates(cursor, conn):
    """Get all Excel templates."""
    cursor.execute(
        "SELECT id, name, department, uploaded_by "
        "FROM excel_templates ORDER BY id DESC"
    )
    return jsonify(cursor.fetchall())


@admin_bp.route("/templates/upload", methods=["POST"])
@with_db_connection
def upload_template(cursor, conn):
    """Upload a new Excel template."""
    file = request.files.get("file")
    department = request.form.get("department", "GLOBAL")

    if not file:
        return jsonify({"error": "No file"}), 400

    filename = secure_filename(file.filename)
    config_obj = current_app.config.get("CONFIG_OBJ")
    save_path = os.path.join(config_obj.TEMPLATE_FOLDER, filename)
    file.save(save_path)

    cursor.execute(
        """
        INSERT INTO excel_templates (name, department, uploaded_by)
        VALUES (%s, %s, %s)
        """,
        (filename, department, session.get("username")),
    )
    conn.commit()

    return jsonify({"message": "Template uploaded"})


@admin_bp.route("/templates/delete/<int:tid>", methods=["DELETE"])
@with_db_connection
def delete_template(cursor, conn, tid):
    """Delete a template."""
    cursor.execute("DELETE FROM excel_templates WHERE id=%s", (tid,))
    conn.commit()
    return jsonify({"message": "Template deleted"})


@admin_bp.route("/download_template")
@with_db_connection
def download_template(cursor, conn):
    """Download a template file."""
    tid = request.args.get("id")
    cursor.execute("SELECT name FROM excel_templates WHERE id=%s", (tid,))
    row = cursor.fetchone()
    if not row:
        return jsonify({"error": "Not found"}), 404

    config_obj = current_app.config.get("CONFIG_OBJ")
    filepath = os.path.join(config_obj.TEMPLATE_FOLDER, row["name"])
    return send_file(filepath, as_attachment=True)


@admin_bp.route("/api/departments")
@with_db_connection
def api_departments(cursor, conn):
    """Get list of departments."""
    cursor.execute("SELECT dept_desc AS department FROM tbl_dept_master WHERE status_ IS NULL OR status_ = 1 ORDER BY dept_desc")
    rows = cursor.fetchall()
    return jsonify([r["department"] for r in rows])


@admin_bp.route("/permissions/<int:uid>")
@with_db_connection
def get_permissions(cursor, conn, uid):
    """Get user permissions."""
    cursor.execute("SELECT permissions_json FROM users WHERE id=%s", (uid,))
    row = cursor.fetchone()
    return jsonify(json.loads(row["permissions_json"] or "{}"))


@admin_bp.route("/permissions/update", methods=["POST"])
@with_db_connection
def update_permissions(cursor, conn):
    """Update user permissions."""
    data = request.get_json()
    uid = data["user_id"]
    perms = json.dumps(data["permissions"])

    cursor.execute(
        "UPDATE users SET permissions_json=%s WHERE id=%s",
        (perms, uid),
    )
    conn.commit()

    return jsonify({"message": "Permissions updated"})


@admin_bp.route("/admin/error_logs")
@require_admin
def admin_error_logs_page():
    """Admin error logs page."""
    return render_template("admin_error_logs.html")


@admin_bp.route("/api/error_logs")
@with_db_connection
def api_error_logs(cursor, conn):
    """Get error logs (admin only)."""
    if session.get("role") != "admin":
        return jsonify([]), 403

    limit = int(request.args.get("limit", 200))
    cursor.execute("""
        SELECT id, username, endpoint, error_message, created_at
        FROM error_logs
        ORDER BY id DESC
        LIMIT %s
    """, (limit,))
    logs = cursor.fetchall()
    return jsonify(logs)


@admin_bp.route("/api/error_logs/<int:log_id>")
@with_db_connection
def api_error_logs_detail(cursor, conn, log_id):
    """Get detailed error log (admin only)."""
    if session.get("role") != "admin":
        return jsonify({"error": "Forbidden"}), 403

    cursor.execute("""
        SELECT id, username, endpoint, error_message, traceback, created_at
        FROM error_logs WHERE id=%s
    """, (log_id,))
    row = cursor.fetchone()
    if not row:
        return jsonify({"error": "Not found"}), 404

    return jsonify(row)


@admin_bp.route("/api/error_logs/delete/<int:log_id>", methods=["DELETE"])
@with_db_connection
def api_error_logs_delete(cursor, conn, log_id):
    """Delete an error log (admin only)."""
    if session.get("role") != "admin":
        return jsonify({"error": "Forbidden"}), 403

    cursor.execute("DELETE FROM error_logs WHERE id=%s", (log_id,))
    conn.commit()
    return jsonify({"message": "Deleted"})


@admin_bp.route("/api/error_logs/clear", methods=["DELETE"])
@with_db_connection
def api_error_logs_clear(cursor, conn):
    """Clear all error logs (admin only)."""
    if session.get("role") != "admin":
        return jsonify({"error": "Forbidden"}), 403

    cursor.execute("TRUNCATE TABLE error_logs")
    conn.commit()
    return jsonify({"message": "All logs cleared"})

