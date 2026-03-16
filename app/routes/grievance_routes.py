"""
grievance_routes.py
-------------------
Flask Blueprint for the Grievance Handling System.
Mount with:  app.register_blueprint(grievance_bp)

Routes
------
GET  /grievance                  → user grievance submission page
POST /api/grievance/submit       → submit new ticket (multipart)
GET  /api/grievance/types        → list active grievance types
GET  /api/grievance/my_tickets   → tickets for logged-in user
GET  /api/grievance/all_tickets  → admin: all tickets with filters
POST /api/grievance/update       → admin: change status / add remark
GET  /api/grievance/attachment/<ticket_id>  → download attachment
GET  /api/grievance/ticket/<ticket_no>      → single ticket detail
"""

"""grievance_routes.py — Grievance Handling System"""

from flask import Blueprint, render_template, request, jsonify, session, send_file, current_app
from datetime import datetime
import traceback
import io
from app.utils.database import with_db_connection, log_error_db

grievance_bp = Blueprint("grievance", __name__)


def require_login():
    if "username" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    return None

def require_admin():
    if "username" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    if session.get("role") != "admin":
        return jsonify({"error": "Admin only"}), 403
    return None


def generate_ticket_no(cursor, department=""):
    """
    Format: DEP-YYYY-MM-0001
    DEP = first 3 letters of department, uppercased
    e.g. if department = "Agriculture"  → AGR-2026-03-0001
         if department = "Statistics"   → STA-2026-03-0001
         if department = ""             → GEN-2026-03-0001  (generic fallback)
    Sequence resets each month per dept prefix.
    """
    dept_code = (department[:3].upper() if department else "GEN").ljust(3,"X")
    prefix    = f"{dept_code}{datetime.now().strftime('%Y%m')}"
    cursor.execute(
        "SELECT COUNT(*) AS cnt FROM tbl_grievance_ticket WHERE ticket_no LIKE %s",
        (f"{prefix}%",)
    )
    cnt = cursor.fetchone()["cnt"]
    return f"{prefix}{str(cnt + 1).zfill(4)}"


@grievance_bp.route("/grievance")
def grievance_page():
    if "username" not in session:
        from flask import redirect, url_for
        return redirect(url_for("auth.login_page"))
    return render_template("grievance.html")


@grievance_bp.route("/api/grievance/types")
@with_db_connection
def get_grievance_types(cursor, conn):
    err = require_login()
    if err: return err
    try:
        cursor.execute(
            "SELECT id, type_name, description "
            "FROM tbl_grievance_type WHERE is_active=1 ORDER BY id"
        )
        return jsonify(cursor.fetchall())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@grievance_bp.route("/api/grievance/submit", methods=["POST"])
@with_db_connection
def submit_grievance(cursor, conn):
    err = require_login()
    if err: return err

    username          = session["username"]
    department        = session.get("department", "")
    grievance_type_id = request.form.get("grievance_type_id")
    details           = request.form.get("details", "").strip()
    attachment        = request.files.get("attachment")

    if not grievance_type_id:
        return jsonify({"error": "Please select a grievance type"}), 400
    if not details:
        return jsonify({"error": "Details are required"}), 400

    try:
        ticket_no  = generate_ticket_no(cursor, department)
        has_attach = 1 if (attachment and attachment.filename) else 0

        cursor.execute("""
            INSERT INTO tbl_grievance_ticket
                (ticket_no, submitted_by, department,
                 grievance_type_id, details, has_attachment, status_id)
            VALUES (%s, %s, %s, %s, %s, %s, 1)
        """, (ticket_no, username, department,
              int(grievance_type_id), details, has_attach))

        ticket_id = cursor.lastrowid

        if has_attach:
            file_bytes = attachment.read()
            cursor.execute("""
                INSERT INTO tbl_grievance_attachment
                    (ticket_id, filename, mimetype, file_data, file_size_kb)
                VALUES (%s, %s, %s, %s, %s)
            """, (ticket_id, attachment.filename,
                  attachment.mimetype or "application/octet-stream",
                  file_bytes, len(file_bytes) // 1024))

        cursor.execute("""
            INSERT INTO tbl_grievance_log (ticket_id, action_by, action, remark)
            VALUES (%s, %s, 'Ticket Submitted', %s)
        """, (ticket_id, username, f"Ticket {ticket_no} submitted by {username}"))

        conn.commit()
        return jsonify({"message": "Grievance submitted successfully", "ticket_no": ticket_no})

    except Exception as e:
        tb = traceback.format_exc()
        print(tb)
        config_obj = current_app.config.get("CONFIG_OBJ")
        if config_obj:
            log_error_db(session.get("username"), request.path, str(e), tb, config_obj)
        return jsonify({"error": str(e)}), 500


@grievance_bp.route("/api/grievance/my_tickets")
@with_db_connection
def my_tickets(cursor, conn):
    err = require_login()
    if err: return err
    try:
        cursor.execute("""
            SELECT t.id, t.ticket_no, t.details, t.has_attachment,
                   t.admin_remark, t.closed_at, t.created_at, t.updated_at,
                   gt.type_name AS grievance_type,
                   gs.status_name AS status, gs.color_hex AS status_color
            FROM tbl_grievance_ticket t
            JOIN tbl_grievance_type   gt ON t.grievance_type_id = gt.id
            JOIN tbl_grievance_status gs ON t.status_id = gs.id
            WHERE t.submitted_by = %s
            ORDER BY t.created_at DESC
        """, (session["username"],))
        rows = cursor.fetchall()
        for r in rows:
            for k in ("created_at","updated_at","closed_at"):
                if r[k]: r[k] = str(r[k])
        return jsonify(rows)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@grievance_bp.route("/api/grievance/all_tickets")
@with_db_connection
def all_tickets(cursor, conn):
    err = require_admin()
    if err: return err
    status_filter = request.args.get("status", "")
    type_filter   = request.args.get("type_id", "")
    try:
        where  = "WHERE 1=1"
        params = []
        if status_filter:
            where += " AND gs.status_name = %s"
            params.append(status_filter)
        if type_filter:
            where += " AND t.grievance_type_id = %s"
            params.append(int(type_filter))

        cursor.execute(f"""
            SELECT t.id, t.ticket_no, t.submitted_by, t.department,
                   t.details, t.has_attachment, t.admin_remark,
                   t.assigned_to, t.closed_by, t.closed_at,
                   t.created_at, t.updated_at,
                   gt.type_name AS grievance_type,
                   gs.status_name AS status, gs.color_hex AS status_color
            FROM tbl_grievance_ticket t
            JOIN tbl_grievance_type   gt ON t.grievance_type_id = gt.id
            JOIN tbl_grievance_status gs ON t.status_id = gs.id
            {where}
            ORDER BY t.created_at DESC
        """, params)
        rows = cursor.fetchall()
        for r in rows:
            for k in ("created_at","updated_at","closed_at"):
                if r[k]: r[k] = str(r[k])
        return jsonify(rows)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@grievance_bp.route("/api/grievance/update", methods=["POST"])
@with_db_connection
def update_ticket(cursor, conn):
    err = require_admin()
    if err: return err
    data       = request.get_json()
    ticket_id  = data.get("ticket_id")
    new_status = data.get("status")
    remark     = data.get("admin_remark", "").strip()
    username   = session["username"]
    if not ticket_id or not new_status:
        return jsonify({"error": "ticket_id and status required"}), 400
    try:
        cursor.execute("SELECT id FROM tbl_grievance_status WHERE status_name=%s", (new_status,))
        status_row = cursor.fetchone()
        if not status_row:
            return jsonify({"error": f"Unknown status: {new_status}"}), 400
        status_id = status_row["id"]
        if new_status == "Closed":
            cursor.execute("""
                UPDATE tbl_grievance_ticket
                SET status_id=%s, admin_remark=%s, closed_by=%s, closed_at=NOW(), assigned_to=%s
                WHERE id=%s
            """, (status_id, remark, username, username, ticket_id))
        else:
            cursor.execute("""
                UPDATE tbl_grievance_ticket
                SET status_id=%s, admin_remark=%s, assigned_to=%s WHERE id=%s
            """, (status_id, remark, username, ticket_id))
        cursor.execute("""
            INSERT INTO tbl_grievance_log (ticket_id, action_by, action, remark)
            VALUES (%s, %s, %s, %s)
        """, (ticket_id, username, f"Status changed to {new_status}", remark))
        conn.commit()
        return jsonify({"message": f"Ticket updated to {new_status}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@grievance_bp.route("/api/grievance/attachment/<int:ticket_id>")
@with_db_connection
def download_attachment(cursor, conn, ticket_id):
    """
    Returns attachment as inline (for popup preview).
    Images / PDF are served with Content-Disposition: inline
    so the browser renders them directly inside the modal.
    Also returns JSON with base64 data when ?mode=base64
    """
    err = require_login()
    if err: return err
    try:
        cursor.execute(
            "SELECT filename, mimetype, file_data "
            "FROM tbl_grievance_attachment WHERE ticket_id=%s LIMIT 1",
            (ticket_id,)
        )
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "No attachment found"}), 404

        if request.args.get("mode") == "base64":
            import base64
            b64 = base64.b64encode(row["file_data"]).decode("utf-8")
            return jsonify({
                "filename": row["filename"],
                "mimetype": row["mimetype"],
                "data":     b64
            })

        # Default: inline (renders in browser popup / iframe)
        from flask import Response
        resp = Response(
            io.BytesIO(row["file_data"]).read(),
            mimetype=row["mimetype"]
        )
        resp.headers["Content-Disposition"] = f"inline; filename={row['filename']}"
        return resp
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@grievance_bp.route("/api/grievance/ticket/<ticket_no>")
@with_db_connection
def ticket_detail(cursor, conn, ticket_no):
    err = require_login()
    if err: return err
    try:
        cursor.execute("""
            SELECT t.*, gt.type_name, gs.status_name, gs.color_hex
            FROM tbl_grievance_ticket t
            JOIN tbl_grievance_type   gt ON t.grievance_type_id = gt.id
            JOIN tbl_grievance_status gs ON t.status_id = gs.id
            WHERE t.ticket_no = %s
        """, (ticket_no,))
        ticket = cursor.fetchone()
        if not ticket:
            return jsonify({"error": "Ticket not found"}), 404
        if session.get("role") != "admin":
            if ticket["submitted_by"] != session["username"]:
                return jsonify({"error": "Access denied"}), 403
        for k in ("created_at","updated_at","closed_at"):
            if ticket[k]: ticket[k] = str(ticket[k])
        cursor.execute("""
            SELECT action_by, action, remark, created_at
            FROM tbl_grievance_log WHERE ticket_id=%s ORDER BY created_at ASC
        """, (ticket["id"],))
        logs = cursor.fetchall()
        for l in logs:
            if l["created_at"]: l["created_at"] = str(l["created_at"])
        return jsonify({"ticket": ticket, "logs": logs})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@grievance_bp.route("/api/grievance/stats")
@with_db_connection
def grievance_stats(cursor, conn):
    err = require_admin()
    if err: return err
    try:
        cursor.execute("""
            SELECT gs.status_name, COUNT(*) AS cnt
            FROM tbl_grievance_ticket t
            JOIN tbl_grievance_status gs ON t.status_id = gs.id
            GROUP BY gs.status_name
        """)
        result = {r["status_name"]: r["cnt"] for r in cursor.fetchall()}
        result.setdefault("Submitted", 0)
        result.setdefault("Pending",   0)
        result.setdefault("Closed",    0)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500