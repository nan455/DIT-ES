"""Approver routes - FULL FINAL VERSION (strict checkbox validation)."""
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
import traceback
import datetime
from app.utils.database import with_db_connection, log_error_db
from flask import current_app

approver_bp = Blueprint("approver", __name__)


def requires_approver(f):
    """Decorator to check if user is an approver/admin."""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("auth.login_page"))

        if session.get("role") not in ["approver", "admin"]:
            return jsonify({"error": "Unauthorized - Approver access required"}), 403

        return f(*args, **kwargs)
    return decorated_function


@approver_bp.route("/approver_dashboard")
def approver_dashboard():
    if "username" not in session:
        return redirect(url_for("auth.login_page"))
    return render_template("approver_dashboard.html")


@approver_bp.route("/api/debug_session")
def debug_session():
    return jsonify({
        "session_data": dict(session),
        "has_username": "username" in session,
        "username": session.get("username"),
        "role": session.get("role"),
        "department": session.get("department"),
        "user_id": session.get("user_id"),
        "session_keys": list(session.keys())
    })


# ─────────────────────────────────────────────────────────────
# APPROVER: pending uploads queue
# ─────────────────────────────────────────────────────────────
@approver_bp.route("/api/pending_uploads")
@with_db_connection
def get_pending_uploads(cursor, conn):
    try:
        if "username" not in session:
            return jsonify({"error": "Not authenticated"}), 401

        role       = session.get("role")
        department = session.get("department")

        if role not in ["approver", "admin"]:
            return jsonify({"error": "Unauthorized"}), 403

        # ✅ FIX: rejection_reason, updated_by, updated_date included
        if role == "admin":
            cursor.execute("""
                SELECT id, filename, table_name,
                       uploaded_by, department, uploaded_on,
                       CAST(status_ AS SIGNED) AS status_,
                       rejection_reason, updated_by, updated_date
                FROM excel_uploads
                ORDER BY uploaded_on DESC
            """)
        else:
            cursor.execute("""
                SELECT id, filename, table_name,
                       uploaded_by, department, uploaded_on,
                       CAST(status_ AS SIGNED) AS status_,
                       rejection_reason, updated_by, updated_date
                FROM excel_uploads
                WHERE department = %s
                ORDER BY uploaded_on DESC
            """, (department,))

        uploads = cursor.fetchall()

        for upload in uploads:
            upload_id  = upload["id"]
            table_name = upload["table_name"]
            status     = upload.get("status_")

            # Normalize status
            if status in [1, True, "1"]:
                normalized = 1
            elif status in [0, False, "0"]:
                normalized = 0
            else:
                normalized = None

            upload["status_"] = normalized

            # Ensure rejection_reason is None if empty
            if not upload.get("rejection_reason"):
                upload["rejection_reason"] = None

            # Row-level summary
            try:
                cursor.execute(f"""
                    SELECT
                        COUNT(*) AS total_rows,
                        SUM(CASE WHEN is_approved = 1 THEN 1 ELSE 0 END) AS approved_rows,
                        SUM(CASE WHEN is_approved = 0 THEN 1 ELSE 0 END) AS rejected_rows
                    FROM `{table_name}`
                    WHERE upload_id = %s
                """, (upload_id,))
                summary = cursor.fetchone()
            except Exception:
                summary = None

            total         = summary["total_rows"]    if summary else 0
            approved_rows = summary["approved_rows"] or 0 if summary else 0
            rejected_rows = summary["rejected_rows"] or 0 if summary else 0

            upload["all_rows_approved"] = (total > 0 and approved_rows == total)
            upload["has_rejected_rows"] = (rejected_rows > 0)

            # Button logic
            if normalized is None:
                upload["can_edit"]    = True
                upload["can_reject"]  = not upload["all_rows_approved"]
                upload["can_approve"] = not upload["has_rejected_rows"]
                upload["can_delete"]  = True
            else:
                upload["can_edit"]    = False
                upload["can_approve"] = False
                upload["can_reject"]  = False
                upload["can_delete"]  = False

        return jsonify(uploads)

    except Exception as e:
        tb = traceback.format_exc()
        print("❌ Error:", e)
        print(tb)
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────
# USER DASHBOARD: /uploads  (called by user_dashboard.html)
# ✅ FIX: now returns rejection_reason so popup works
# ─────────────────────────────────────────────────────────────
@approver_bp.route("/uploads")
@with_db_connection
def get_uploads_for_user(cursor, conn):
    """
    Returns uploads for the current user's department.
    Used by the user dashboard Upload History tab.
    Includes rejection_reason so the 'View Remark' popup works.
    """
    try:
        if "username" not in session:
            return jsonify({"error": "Not authenticated"}), 401

        # Allow department override via query param (for backward compat)
        department = request.args.get("department") or session.get("department")

        cursor.execute("""
            SELECT id, filename, table_name,
                   uploaded_by, department, uploaded_on,
                   CAST(status_ AS SIGNED) AS status_,
                   rejection_reason,
                   updated_by,
                   updated_date
            FROM excel_uploads
            WHERE department = %s
            ORDER BY uploaded_on DESC
        """, (department,))

        uploads = cursor.fetchall()

        for upload in uploads:
            status = upload.get("status_")

            if status in [1, True, "1"]:
                upload["status_"] = 1
            elif status in [0, False, "0"]:
                upload["status_"] = 0
            else:
                upload["status_"] = None

            # Normalize rejection_reason
            if not upload.get("rejection_reason"):
                upload["rejection_reason"] = None

            # Default button flags — adjust these based on your real logic
            upload.setdefault("can_edit",   upload["status_"] is None)
            upload.setdefault("can_delete", upload["status_"] is None)

        return jsonify(uploads)

    except Exception as e:
        tb = traceback.format_exc()
        config_obj = current_app.config.get("CONFIG_OBJ")
        if config_obj:
            log_error_db(session.get("username"), request.path, str(e), tb, config_obj)
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────
# CHECK: rejected rows
# ─────────────────────────────────────────────────────────────
@approver_bp.route("/api/check_rejected_rows")
@with_db_connection
def check_rejected_rows(cursor, conn):
    upload_id = request.args.get("upload_id")
    if not upload_id:
        return jsonify({"error": "Missing upload_id"}), 400

    try:
        cursor.execute("SELECT table_name FROM excel_uploads WHERE id = %s", (upload_id,))
        up = cursor.fetchone()
        if not up:
            return jsonify({"error": "Upload not found"}), 404

        table = up["table_name"]

        cursor.execute(f"""
            SELECT COUNT(*) AS rejected_count
            FROM `{table}`
            WHERE upload_id = %s AND is_approved = 0
        """, (upload_id,))
        row = cursor.fetchone()

        rejected_count = int(row["rejected_count"] or 0)
        return jsonify({"rejected_count": rejected_count, "has_rejected": rejected_count > 0})

    except Exception as e:
        tb = traceback.format_exc()
        config_obj = current_app.config.get("CONFIG_OBJ")
        if config_obj:
            log_error_db(session.get("username"), request.path, str(e), tb, config_obj)
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────
# CHECK: all rows reviewed
# ─────────────────────────────────────────────────────────────
@approver_bp.route("/api/check_all_rows_reviewed")
@with_db_connection
def check_all_rows_reviewed(cursor, conn):
    upload_id = request.args.get("upload_id")
    if not upload_id:
        return jsonify({"error": "Missing upload_id"}), 400

    try:
        cursor.execute("SELECT table_name FROM excel_uploads WHERE id=%s", (upload_id,))
        up = cursor.fetchone()
        if not up:
            return jsonify({"error": "Upload not found"}), 404

        table = up["table_name"]

        cursor.execute(f"""
            SELECT COUNT(*) AS pending_count
            FROM `{table}`
            WHERE is_approved IS NULL
        """)
        pending_count = int(cursor.fetchone()["pending_count"])

        return jsonify({"pending_count": pending_count, "has_pending": pending_count > 0})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────
# APPROVE UPLOAD
# ─────────────────────────────────────────────────────────────
@approver_bp.route("/api/approve_upload", methods=["POST"])
@with_db_connection
def approve_upload(cursor, conn):
    try:
        if "username" not in session:
            return jsonify({"error": "Not authenticated"}), 401

        if session.get("role") not in ["approver", "admin"]:
            return jsonify({"error": "Unauthorized"}), 403

        data      = request.get_json(force=True)
        upload_id = data.get("upload_id")

        if not upload_id:
            return jsonify({"error": "Upload ID is required"}), 400

        cursor.execute("SELECT table_name FROM excel_uploads WHERE id=%s", (upload_id,))
        up = cursor.fetchone()
        if not up:
            return jsonify({"error": "Upload not found"}), 404

        table = up["table_name"]

        cursor.execute(f"""
            SELECT COUNT(*) AS pending_count
            FROM `{table}`
            WHERE upload_id=%s AND is_approved IS NULL
        """, (upload_id,))
        pending_count = int(cursor.fetchone()["pending_count"] or 0)
        if pending_count > 0:
            return jsonify({"error": f"Cannot approve upload. Pending rows: {pending_count}"}), 400

        cursor.execute(f"""
            SELECT COUNT(*) AS rejected_count
            FROM `{table}`
            WHERE upload_id=%s AND is_approved = 0
        """, (upload_id,))
        rejected_count = int(cursor.fetchone()["rejected_count"] or 0)
        if rejected_count > 0:
            return jsonify({
                "error": f"Cannot approve upload. {rejected_count} row(s) are rejected. Reject upload instead."
            }), 400

        cursor.execute("""
            UPDATE excel_uploads
            SET status_      = 1,
                updated_by   = %s,
                updated_date = NOW()
            WHERE id = %s
        """, (session.get("username"), upload_id))

        conn.commit()
        return jsonify({"message": "Upload approved successfully", "upload_id": upload_id})

    except Exception as e:
        tb = traceback.format_exc()
        config_obj = current_app.config.get("CONFIG_OBJ")
        if config_obj:
            log_error_db(session.get("username"), request.path, str(e), tb, config_obj)
        conn.rollback()
        return jsonify({"error": str(e)}), 500



# ─────────────────────────────────────────────────────────────
# GET upload-level rejection reason (used by view_excel_data)
# ─────────────────────────────────────────────────────────────
@approver_bp.route("/api/upload_rejection_reason")
@with_db_connection
def get_upload_rejection_reason(cursor, conn):
    """
    Returns the upload-level rejection_reason for a given upload_id.
    Called by view_excel_data.html to show in the row remarks modal.
    """
    if "username" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    upload_id = request.args.get("upload_id")
    if not upload_id:
        return jsonify({"error": "Missing upload_id"}), 400

    try:
        cursor.execute("""
            SELECT rejection_reason, updated_by, updated_date
            FROM excel_uploads
            WHERE id = %s
        """, (upload_id,))
        row = cursor.fetchone()
        if not row:
            return jsonify({"rejection_reason": None})

        return jsonify({
            "rejection_reason": row["rejection_reason"] or None,
            "rejected_by":      row["updated_by"],
            "rejected_date":    row["updated_date"].isoformat() if row["updated_date"] else None
        })

    except Exception as e:
        tb = traceback.format_exc()
        config_obj = current_app.config.get("CONFIG_OBJ")
        if config_obj:
            log_error_db(session.get("username"), request.path, str(e), tb, config_obj)
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────
# REJECT UPLOAD WITH REMARK
# ─────────────────────────────────────────────────────────────
@approver_bp.route("/uploads/<int:upload_id>/reject_uploads", methods=["POST"])
@with_db_connection
def reject_upload_with_remark(cursor, conn, upload_id):
    """
    Reject an upload with a mandatory remark.
    Frontend posts to /uploads/<id>/reject_uploads with JSON { "remark": "..." }
    """
    if "username" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    if session.get("role") not in ["approver", "admin"]:
        return jsonify({"error": "Permission denied"}), 403

    data   = request.get_json(force=True)
    remark = data.get("remark", "").strip()

    if not remark:
        return jsonify({"error": "Rejection remark is required"}), 400

    try:
        cursor.execute("SELECT table_name FROM excel_uploads WHERE id = %s", (upload_id,))
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "Upload not found"}), 404

        table = row["table_name"]

        # Block if any row still unreviewed
        cursor.execute(f"""
            SELECT COUNT(*) AS pending_count
            FROM `{table}`
            WHERE upload_id = %s AND is_approved IS NULL
        """, (upload_id,))
        pending_count = int(cursor.fetchone()["pending_count"] or 0)
        if pending_count > 0:
            return jsonify({
                "error": f"Cannot reject upload. {pending_count} row(s) are still pending review."
            }), 400

        # Update excel_uploads
        cursor.execute("""
            UPDATE excel_uploads
            SET status_          = 0,
                rejection_reason = %s,
                updated_by       = %s,
                updated_date     = NOW()
            WHERE id = %s
        """, (remark, session.get("username"), upload_id))

        # Mark all data rows as rejected
        cursor.execute(f"""
            UPDATE `{table}`
            SET status_     = 0,
                is_approved = 0
            WHERE upload_id = %s
        """, (upload_id,))

        conn.commit()
        return jsonify({"message": "Upload rejected successfully"})

    except Exception as e:
        tb = traceback.format_exc()
        conn.rollback()
        config_obj = current_app.config.get("CONFIG_OBJ")
        if config_obj:
            log_error_db(session.get("username"), request.path, str(e), tb, config_obj)
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────
#  Revert upload status back to NULL (pending)
#  Called when approver rejects/clears a row after bulk-accept
# ─────────────────────────────────────────────────────────────
@approver_bp.route("/api/revert_upload_pending", methods=["POST"])
@with_db_connection
def revert_upload_pending(cursor, conn):
    if "username" not in session or session.get("role") not in ("approver", "admin"):
        return jsonify({"error": "Unauthorized"}), 403

    data      = request.get_json()
    upload_id = data.get("upload_id")
    if not upload_id:
        return jsonify({"error": "upload_id required"}), 400

    try:
        cursor.execute(
            "UPDATE excel_uploads SET status_ = NULL WHERE id = %s",
            (upload_id,)
        )
        conn.commit()
        return jsonify({"message": "Upload reverted to pending"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500