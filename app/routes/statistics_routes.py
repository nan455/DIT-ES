"""
statistics_routes.py
====================
Two new API routes to power the enhanced Statistics tab:

  GET /api/statistics/departments?from=YYYY-MM&to=YYYY-MM
      → Existing dept summary (submitted / pending / not_submitted)
        NOW supports optional date range filter via `from` and `to` params.

  GET /api/statistics/register_breakdown?from=YYYY-MM&to=YYYY-MM
      → NEW: per-register stats (submitted / approved / rejected / pending counts)
        across all departments, with optional date range filter.

ADD TO YOUR __init__.py:
    from app.routes.statistics_routes import statistics_bp
    app.register_blueprint(statistics_bp)

OR if your existing statistics route is in data_routes.py / admin_routes.py,
paste the two route functions there and remove the blueprint wrapper.
"""

from flask import Blueprint, request, jsonify, session
import traceback
from app.utils.database import with_db_connection

statistics_bp = Blueprint("statistics_ext", __name__)


# ─────────────────────────────────────────────────────────
#  HELPER: build date-range WHERE clause
#  `from`  = "2026-01"  →  uploaded_on >= '2026-01-01'
#  `to`    = "2026-03"  →  uploaded_on <  '2026-04-01'
# ─────────────────────────────────────────────────────────
def _date_where(from_ym: str, to_ym: str, col: str = "t.updated_date"):
    """Returns (where_clause, params_list)"""
    parts, params = [], []
    if from_ym:
        # e.g. "2026-01" → "2026-01-01"
        parts.append(f"{col} >= %s")
        params.append(from_ym + "-01")
    if to_ym:
        # e.g. "2026-03" → next month "2026-04-01"
        y, m = map(int, to_ym.split("-"))
        if m == 12:
            next_ym = f"{y+1}-01-01"
        else:
            next_ym = f"{y}-{str(m+1).zfill(2)}-01"
        parts.append(f"{col} < %s")
        params.append(next_ym)
    return (" AND ".join(parts), params)


# ─────────────────────────────────────────────────────────
#  EXISTING: Department summary — now with date filter
#  GET /api/statistics/departments?from=YYYY-MM&to=YYYY-MM
#
#  Replace or add this route to your existing statistics handler.
#  The response shape is IDENTICAL to before so nothing else breaks.
# ─────────────────────────────────────────────────────────
@statistics_bp.route("/api/statistics/departments")
@with_db_connection
def department_statistics(cursor, conn):
    if "username" not in session or session.get("role") != "admin":
        return jsonify({"error": "Admin only"}), 403

    from_ym = request.args.get("from", "").strip()   # e.g. "2026-01"
    to_ym   = request.args.get("to",   "").strip()   # e.g. "2026-03"

    try:
        date_clause, date_params = _date_where(from_ym, to_ym)

        # ── All departments from user table ──
        cursor.execute("SELECT DISTINCT department FROM users WHERE department IS NOT NULL AND department != ''")
        all_depts = set(r["department"] for r in cursor.fetchall())

        # ── Uploads with approval status (filtered by date if given) ──
        date_sql = f"AND {date_clause}" if date_clause else ""
        cursor.execute(f"""
            SELECT
                t.department,
                MAX(t.updated_date)  AS last_upload,
                t.updated_by,
                COUNT(*)             AS files_count,
                MAX(t.status_)       AS status_
            FROM excel_uploads t
            WHERE t.department IS NOT NULL {date_sql}
            GROUP BY t.department, t.updated_by
        """, date_params)
        upload_rows = cursor.fetchall()

        upload_map = {}
        for r in upload_rows:
            dept = r["department"]
            if dept not in upload_map:
                upload_map[dept] = {
                    "department":  dept,
                    "last_upload": str(r["last_upload"]) if r["last_upload"] else "-",
                    "updated_by":  r["updated_by"] or "-",
                    "files_count": r["files_count"],
                    "status_":     r["status_"]
                }

        submitted, pending, not_submitted = [], [], []

        for dept in all_depts:
            if dept in upload_map:
                row    = upload_map[dept]
                status = row["status_"]
                if status == 1 or status is True or str(status) == "1":
                    submitted.append(row)
                else:
                    pending.append(row)
            else:
                not_submitted.append(dept)

        return jsonify({
            "submitted":     submitted,
            "pending":       pending,
            "not_submitted": not_submitted
        })

    except Exception as e:
        tb = traceback.format_exc()
        print(tb)
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────
#  NEW: Register-wise breakdown
#  GET /api/statistics/register_breakdown?from=YYYY-MM&to=YYYY-MM
#
#  Returns one row per transaction table showing:
#    table_name, label, total_depts, submitted_count,
#    approved_count, rejected_count, pending_count, completion_pct
# ─────────────────────────────────────────────────────────
@statistics_bp.route("/api/statistics/register_breakdown")
@with_db_connection
def register_breakdown(cursor, conn):
    if "username" not in session or session.get("role") != "admin":
        return jsonify({"error": "Admin only"}), 403

    from_ym = request.args.get("from", "").strip()
    to_ym   = request.args.get("to",   "").strip()

    try:
        # ── Total departments (denominator) ──
        cursor.execute("""
            SELECT COUNT(DISTINCT department) AS cnt
            FROM users
            WHERE department IS NOT NULL AND department != ''
        """)
        total_depts = cursor.fetchone()["cnt"] or 1

        # ── All transaction tables: discovered from excel_uploads ──
        # This works regardless of what master table your app uses,
        # because every uploaded register appears in excel_uploads.
        cursor.execute("""
            SELECT DISTINCT table_name
            FROM excel_uploads
            ORDER BY table_name
        """)
        upload_tables = [r["table_name"] for r in cursor.fetchall()]

        # Try to get human-readable labels from tbl_column_metadata
        label_map = {}
        try:
            cursor.execute("""
                SELECT table_name,
                       COALESCE(MAX(display_label), table_name) AS label
                FROM tbl_column_metadata
                GROUP BY table_name
            """)
            for r in cursor.fetchall():
                label_map[r["table_name"]] = r["label"]
        except Exception:
            pass  # no metadata table — fall back to table_name as label

        registers = [
            {"table_name": t, "label": label_map.get(t, t)}
            for t in upload_tables
        ]

        if not registers:
            return jsonify([])  # no uploads at all yet

        date_clause, date_params = _date_where(from_ym, to_ym)
        date_sql = f"AND {date_clause}" if date_clause else ""

        result = []
        for reg in registers:
            tbl   = reg["table_name"]
            label = reg.get("label") or tbl

            # Count uploads for this table, grouped by approval status
            cursor.execute(f"""
                SELECT
                    COUNT(DISTINCT department)                                      AS submitted_count,
                    SUM(CASE WHEN status_ = 1 OR status_ = TRUE THEN 1 ELSE 0 END) AS approved_count,
                    SUM(CASE WHEN status_ = 0 OR status_ = FALSE THEN 1 ELSE 0 END) AS rejected_count
                FROM excel_uploads
                WHERE table_name = %s {date_sql}
            """, [tbl] + date_params)
            row = cursor.fetchone()

            submitted_count = int(row["submitted_count"] or 0)
            approved_count  = int(row["approved_count"]  or 0)
            rejected_count  = int(row["rejected_count"]  or 0)
            pending_count   = submitted_count - approved_count - rejected_count
            if pending_count < 0: pending_count = 0

            completion_pct  = round((approved_count / total_depts) * 100, 1) if total_depts else 0

            result.append({
                "table_name":      tbl,
                "label":           label,
                "total_depts":     total_depts,
                "submitted_count": submitted_count,
                "approved_count":  approved_count,
                "rejected_count":  rejected_count,
                "pending_count":   pending_count,
                "completion_pct":  completion_pct
            })

        # Sort: lowest completion first (highlights problem areas)
        result.sort(key=lambda x: x["completion_pct"])

        return jsonify(result)

    except Exception as e:
        tb = traceback.format_exc()
        print(tb)
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────
#  NEW: Department-specific register breakdown
#  GET /api/statistics/dept_register_breakdown
#      ?department=Animal+Husbandry+and+Animal+Welfare
#      &from=YYYY-MM  (optional)
#      &to=YYYY-MM    (optional)
#
#  For each register in txn_registry for that department,
#  returns the upload status: approved / rejected / pending / not_uploaded
# ─────────────────────────────────────────────────────────
@statistics_bp.route("/api/statistics/dept_register_breakdown")
@with_db_connection
def dept_register_breakdown(cursor, conn):
    if "username" not in session or session.get("role") != "admin":
        return jsonify({"error": "Admin only"}), 403

    department = request.args.get("department", "").strip()
    from_ym    = request.args.get("from", "").strip()
    to_ym      = request.args.get("to",   "").strip()

    if not department:
        return jsonify({"error": "department parameter required"}), 400

    try:
        # ── Step 1: Get all registers assigned to this department ──
        cursor.execute("""
            SELECT report_id, department, report_name, target_table_name
            FROM txn_registry
            WHERE department = %s
            ORDER BY report_name
        """, (department,))
        registers = cursor.fetchall()

        if not registers:
            return jsonify({"registers": [], "department": department})

        # ── Step 2: Date filter clause ──
        date_clause, date_params = _date_where(from_ym, to_ym, col="updated_date")

        # ── Step 3: For each register, find latest upload from this dept ──
        result = []
        for reg in registers:
            tbl = reg["target_table_name"]

            where_extra = f"AND {date_clause}" if date_clause else ""

            # Step A: count total uploads for this dept+table
            cursor.execute(f"""
                SELECT COUNT(*) AS upload_count
                FROM excel_uploads
                WHERE department = %s
                  AND table_name  = %s
                  {where_extra}
            """, [department, tbl] + date_params)
            count_row  = cursor.fetchone()
            up_count   = int(count_row["upload_count"] or 0) if count_row else 0

            # Step B: get the latest upload row (no aggregate → no GROUP BY needed)
            cursor.execute(f"""
                SELECT id, status_, updated_date AS last_uploaded, updated_by AS uploaded_by
                FROM excel_uploads
                WHERE department = %s
                  AND table_name  = %s
                  {where_extra}
                ORDER BY updated_date DESC
                LIMIT 1
            """, [department, tbl] + date_params)
            upload = cursor.fetchone()

            # Determine status
            if not upload or up_count == 0:
                status     = "not_uploaded"
                last_up    = None
                uploaded_by= None
                up_count   = 0
            else:
                s = upload["status_"]
                if   s == 1 or s is True  or str(s) == "1": status = "approved"
                elif s == 0 or s is False or str(s) == "0": status = "rejected"
                else:                                         status = "pending"
                last_up     = str(upload["last_uploaded"]) if upload["last_uploaded"] else None
                uploaded_by = upload["uploaded_by"]

            result.append({
                "report_id":         reg["report_id"],
                "report_name":       reg["report_name"],
                "target_table_name": tbl,
                "upload_count":      up_count,
                "status":            status,
                "last_uploaded":     last_up,
                "uploaded_by":       uploaded_by
            })

        return jsonify({
            "department": department,
            "registers":  result
        })

    except Exception as e:
        tb = traceback.format_exc()
        print(tb)
        return jsonify({"error": str(e)}), 500