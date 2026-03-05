"""API routes for data operations."""
from flask import Blueprint, request, jsonify, session, send_file
import datetime
import decimal
import json
import io
import pandas as pd
import traceback
from app.utils.database import with_db_connection, log_error_db
from app.utils.validators import (
    is_audit_column,
    is_refno_column,
    resolve_year,
    fk_value_to_id,
)
from app.constants import LOOKUP_CONFIG, COLUMN_LABEL
from app.utils.excel_helpers import (
    load_metadata_for_table,
    generate_excel_template,
)
from werkzeug.utils import secure_filename
from flask import current_app

api_bp = Blueprint("api", __name__)


class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for datetime and Decimal."""
    def default(self, obj):
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        return super().default(obj)


@api_bp.route("/api/profile")
@with_db_connection
def api_profile(cursor, conn):
    """Get current user profile."""
    cursor.execute(
        "SELECT id, username, department, role "
        "FROM users WHERE username=%s",
        (session.get("username"),),
    )
    return jsonify(cursor.fetchone())


@api_bp.route("/api/transaction_tables")
@with_db_connection
def api_transaction_tables(cursor, conn):
    """
    Returns list of registers from txn_registry for the
    logged-in user's department.
    """
    dept = session.get("department")
    if not dept:
        return jsonify([])

    try:
        cursor.execute("SHOW TABLES LIKE 'txn_registry'")
        if not cursor.fetchone():
            return jsonify([])

        cursor.execute(
            """
            SELECT report_id,
                   report_name AS label,
                   target_table_name AS table_name
            FROM txn_registry
            WHERE LOWER(department) = LOWER(%s)
            ORDER BY report_name
            """,
            (dept,),
        )
        rows = cursor.fetchall()
        return jsonify(rows)
    except Exception as e:
        tb = traceback.format_exc()
        config_obj = current_app.config.get("CONFIG_OBJ")
        log_error_db(session.get("username"), request.path, str(e), tb, config_obj)
        return jsonify([])


@api_bp.route("/api/table_columns")
@with_db_connection
def api_table_columns(cursor, conn):
    """Get columns for a table."""
    table = request.args.get("table")
    try:
        cursor.execute(f"SHOW COLUMNS FROM `{table}`")
        cols = [c["Field"] for c in cursor.fetchall()]
        return jsonify(cols)
    except Exception as e:
        tb = traceback.format_exc()
        config_obj = current_app.config.get("CONFIG_OBJ")
        log_error_db(session.get("username"), request.path, str(e), tb, config_obj)
        return jsonify({"error": str(e)}), 400


@api_bp.route("/api/primary_key")
@with_db_connection
def api_primary_key(cursor, conn):
    """
    Tell the front-end which column is the PRIMARY KEY.
    Needed because many tables use *_refno instead of 'id'.
    """
    table = request.args.get("table")
    if not table:
        return jsonify({"pk": None})

    try:
        cursor.execute(f"SHOW KEYS FROM `{table}` WHERE Key_name='PRIMARY'")
        pk_res = cursor.fetchone()
        pk_col = pk_res["Column_name"] if pk_res else None
        return jsonify({"pk": pk_col})
    except Exception as e:
        tb = traceback.format_exc()
        config_obj = current_app.config.get("CONFIG_OBJ")
        log_error_db(session.get("username"), request.path, str(e), tb, config_obj)
        return jsonify({"pk": None})


@api_bp.route("/api/excel_data")
@with_db_connection
def api_excel_data(cursor, conn):
    """Get data from a table."""
    table = request.args.get("table")
    only_rejected = request.args.get("only_rejected") == "true"
    upload_id = request.args.get("upload_id")

    try:
        params = []
        sql = f"SELECT * FROM `{table}` WHERE 1=1"

        # ✅ filter by upload_id if present
        if upload_id:

            sql += " AND (upload_id = %s OR upload_id IS NULL)"
            params.append(upload_id)

        # ✅ show only rejected rows for user fix
        if only_rejected:
            sql += " AND is_approved = 0"

        # ordering
        cursor.execute(f"SHOW COLUMNS FROM `{table}` LIKE 'id'")
        has_id = cursor.fetchone()
        if has_id:
            sql += " ORDER BY id DESC"

        sql += " LIMIT 1000"
        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()

        return current_app.response_class(
            response=json.dumps(rows, cls=CustomJSONEncoder),
            status=200,
            mimetype="application/json",
        )

    except Exception as e:
        tb = traceback.format_exc()
        config_obj = current_app.config.get("CONFIG_OBJ")
        log_error_db(session.get("username"), request.path, str(e), tb, config_obj)
        return jsonify({"error": str(e)}), 500


@api_bp.route("/api/lookup")
@with_db_connection
def api_lookup(cursor, conn):
    """Get lookup values for a foreign key column."""
    from app.utils.validators import infer_master_table_from_fk, detect_master_id_and_desc
    
    col = request.args.get("col")
    master_override = request.args.get("master")

    if not col:
        return jsonify([])

    try:
        if col in LOOKUP_CONFIG:
            table_ref, desc_col, id_col = LOOKUP_CONFIG[col]
            cursor.execute(
                f"SELECT {id_col} AS id, {desc_col} AS name "
                f"FROM `{table_ref}` ORDER BY name"
            )
            return jsonify(cursor.fetchall())

        master_table = master_override or infer_master_table_from_fk(col)
        if not master_table:
            return jsonify([])

        id_col, desc_col = detect_master_id_and_desc(cursor, master_table)
        if not id_col or not desc_col:
            return jsonify([])

        cursor.execute(
            f"SELECT `{id_col}` AS id, `{desc_col}` AS name "
            f"FROM `{master_table}` ORDER BY name"
        )
        rows = cursor.fetchall()
        return jsonify(rows)
    except Exception as e:
        tb = traceback.format_exc()
        config_obj = current_app.config.get("CONFIG_OBJ")
        log_error_db(session.get("username"), request.path, str(e), tb, config_obj)
        print("❌ lookup error:", e)
        return jsonify({"error": str(e)}), 500


@api_bp.route("/api/column_metadata")
@with_db_connection
def api_column_metadata(cursor, conn):
    """Get column metadata for a table."""
    table = request.args.get("table")
    try:
        cursor.execute("""
            SELECT column_name, display_label
            FROM tbl_column_metadata
            WHERE table_name = %s
        """, (table,))
        rows = cursor.fetchall()
        # unify keys
        result = {}
        for r in rows:
            col = r.get("column_name") or r.get("col_name") or r.get("column")
            label = r.get("display_label") or r.get("displayname") or r.get("label") or ""
            if col:
                result[col] = label
        return jsonify(result)
    except Exception as e:
        tb = traceback.format_exc()
        config_obj = current_app.config.get("CONFIG_OBJ")
        log_error_db(session.get("username"), request.path, str(e), tb, config_obj)
        return jsonify({})


def user_can_edit_table(cursor, table_name: str) -> bool:
    """
    Very simple permission check.
    """
    if "username" not in session:
        return False
    if session.get("role") == "admin":
        return True

    dept = session.get("department")

    try:
        cursor.execute(
            "SELECT 1 FROM txn_registry "
            "WHERE LOWER(department)=LOWER(%s) AND target_table_name=%s LIMIT 1",
            (dept, table_name),
        )
    #     if cursor.fetchone():
    #         return True
    # except Exception:
    #     pass

    # cursor.execute(
    #     "SELECT 1 FROM excel_uploads WHERE table_name=%s AND department=%s LIMIT 1",
    #     (table_name, dept),
    # )
        return cursor.fetchone() is not None
    except:
        return False


# @api_bp.route("/api/update_excel_cell", methods=["POST"])
# @with_db_connection
# def api_update_excel_cell(cursor, conn):
#     """Update a single cell in a table."""
#     data = request.get_json(force=True)
#     table = data.get("table")
#     col = data.get("column")
#     val = data.get("value")
#     row_id = data.get("id")

#     # Permission check
#     if not user_can_edit_table(cursor, table):
#         return jsonify({"error": "You do not have permission to edit this table."}), 403

#     try:
#         # Clean string
#         if isinstance(val, str):
#             val = val.strip() or None

#         # Load table columns
#         cursor.execute(f"SHOW COLUMNS FROM `{table}`")
#         cols_info = cursor.fetchall()
#         db_cols = [c["Field"] for c in cols_info]

#         if col not in db_cols:
#             return jsonify({"error": "Invalid column."}), 400

#         if col == "id" or is_audit_column(col):
#             return jsonify({"error": "This column cannot be edited."}), 400

#         # Special: year column → convert display → id
#         if col == "year_id":
#             try:
#                 val = resolve_year(cursor, val)
#             except Exception as e:
#                 return jsonify({"error": "Invalid year selected."}), 400

#         # Special: foreign key columns
#         elif col.endswith("_id"):
#             try:
#                 val = fk_value_to_id(cursor, col, val, LOOKUP_CONFIG)
#             except Exception as e:
#                 return jsonify({"error": "Invalid option selected."}), 400

#         # Detect primary key
#         cursor.execute(f"SHOW KEYS FROM `{table}` WHERE Key_name = 'PRIMARY'")
#         pk_res = cursor.fetchone()
#         pk_col = pk_res["Column_name"] if pk_res else "id"

#         # Build UPDATE
#         audit_sql = ""
#         audit_vals = []

#         if "updated_by" in db_cols:
#             audit_sql += ", updated_by=%s"
#             audit_vals.append(session.get("username", "system"))

#         if "updated_date" in db_cols:
#             audit_sql += ", updated_date=%s"
#             audit_vals.append(datetime.datetime.now())

#         sql = f"UPDATE `{table}` SET `{col}`=%s{audit_sql} WHERE `{pk_col}`=%s"

#         cursor.execute(sql, (val, *audit_vals, row_id))
#         conn.commit()

#         return jsonify({"message": "Saved", "value": val})

#     except ValueError:
#         conn.rollback()
#         return jsonify({"error": "Invalid value entered."}), 400

#     except Exception as e:
#         tb = traceback.format_exc()
#         config_obj = current_app.config.get("CONFIG_OBJ")
#         log_error_db(session.get("username"), request.path, str(e), tb, config_obj)
#         conn.rollback()
#         print("❌ update error:", e)
#         return jsonify({
#             "error": "Something went wrong. Please enter valid data."
#         }), 400


@api_bp.route("/api/add_excel_row", methods=["POST"])
@with_db_connection
def api_add_excel_row(cursor, conn):
    data = request.get_json(force=True)

    table = data.get("table")
    row_data = data.get("row_data", {})
    upload_id = data.get("upload_id")   # pass this from UI if available

    if not table or not row_data:
        return jsonify({"error": "Missing table/row_data"}), 400

    if not user_can_edit_table(cursor, table):
        return jsonify({"error": "Permission denied"}), 403

    try:
        cursor.execute(f"SHOW COLUMNS FROM `{table}`")
        cols_info = cursor.fetchall()
        db_cols = [c["Field"] for c in cols_info]

        now = datetime.datetime.now()
        role = session.get("role")

        # -------------------------------------------------
        # ✅ ROLE-BASED STATUS
        # -------------------------------------------------
        if role in ["approver", "admin"]:
            status_val = 1
            approved_val = 1
        else:
            status_val = 1
            approved_val = None

        # -------------------------------------------------
        # ✅ AUTO FIELDS
        # -------------------------------------------------
        if "status_" in db_cols:
            row_data["status_"] = status_val

        if "is_approved" in db_cols:
            row_data["is_approved"] = approved_val

        if "upload_id" in db_cols and upload_id:
            row_data["upload_id"] = upload_id

        if "created_by" in db_cols:
            row_data["created_by"] = session.get("username")

        if "created_date" in db_cols:
            row_data["created_date"] = now

        if "updated_by" in db_cols:
            row_data["updated_by"] = session.get("username")

        if "updated_date" in db_cols:
            row_data["updated_date"] = now

        # -------------------------------------------------
        # ✅ FILTER VALID COLS ONLY
        # -------------------------------------------------
        final_data = {k: v for k, v in row_data.items() if k in db_cols}

        cols = list(final_data.keys())
        values = list(final_data.values())

        col_sql = ", ".join(f"`{c}`" for c in cols)
        ph = ", ".join(["%s"] * len(cols))

        sql = f"INSERT INTO `{table}` ({col_sql}) VALUES ({ph})"
        cursor.execute(sql, values)

        conn.commit()

        return jsonify({
            "message": "Row added",
            "auto_status": status_val
        })

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    
@api_bp.route("/api/delete_excel_row", methods=["POST"])
@with_db_connection
def api_delete_excel_row(cursor, conn):
    """Delete a row from a table."""
    data = request.get_json(force=True)
    table = data.get("table")
    row_id = data.get("id")

    if not user_can_edit_table(cursor, table):
        return jsonify({"error": "Permission denied"}), 403

    try:
        # detect primary key
        cursor.execute(f"SHOW KEYS FROM `{table}` WHERE Key_name='PRIMARY'")
        pk_res = cursor.fetchone()
        pk_col = pk_res["Column_name"] if pk_res else "id"

        sql = f"DELETE FROM `{table}` WHERE `{pk_col}`=%s"
        cursor.execute(sql, (row_id,))
        conn.commit()

        return jsonify({"message": "Row deleted"})
    except Exception as e:
        tb = traceback.format_exc()
        config_obj = current_app.config.get("CONFIG_OBJ")
        log_error_db(session.get("username"), request.path, str(e), tb, config_obj)
        conn.rollback()
        return jsonify({"error": str(e)}), 500

@api_bp.route("/uploads")
@with_db_connection
def get_uploads(cursor, conn):
    """Get uploads for current user's department - FIXED VERSION WITH CONSISTENT STATUS."""
    try:
        department = session.get("department")
        role = session.get("role")
        username = session.get("username")
        
        # print(f"\n🔍 Loading uploads for: {username} ({role}) - Dept: {department}")
        
        # ✅ CRITICAL FIX: Always include status_ in SELECT and ensure proper typing
        if role == "admin":
            cursor.execute("""
                SELECT 
                    id, 
                    filename, 
                    table_name, 
                    uploaded_by, 
                    department, 
                    uploaded_on,
                    CAST(is_approved AS SIGNED) as is_approved
                FROM excel_uploads 
                ORDER BY uploaded_on DESC
            """)
        else:
            cursor.execute("""
                SELECT 
                    id, 
                    filename, 
                    table_name, 
                    uploaded_by, 
                    department, 
                    uploaded_on,
                    CAST(is_approved AS SIGNED) as is_approved
                FROM excel_uploads 
                WHERE department = %s 
                ORDER BY uploaded_on DESC
            """, (department,))
        
        uploads = cursor.fetchall()
        
        # print(f"📊 Found {len(uploads)} uploads")
        
        # ✅ CONSISTENT STATUS HANDLING FOR ALL DASHBOARDS
        for upload in uploads:
            status = upload.get("is_approved")

            if status is None or status == '' or status == 'NULL':
                normalized = None
            elif status in [1, True, '1']:
                normalized = 1
            elif status in [0, False, '0']:
                normalized = 0
            else:
                normalized = None

            # text
            if normalized is None:
                upload["status_text"] = "Pending"
                upload["status_class"] = "pending"
            elif normalized == 1:
                upload["status_text"] = "Approved"
                upload["status_class"] = "approved"
            else:
                upload["status_text"] = "Rejected"
                upload["status_class"] = "rejected"

            upload["is_approved"] = normalized

            # permission
            can_edit = False
            can_delete = False

            if normalized is None:
                if role in ["admin", "approver"]:
                    can_edit = True
                    can_delete = True
                elif role == "user":
                    can_edit = (upload.get("uploaded_by") == username)
                    can_delete = (upload.get("uploaded_by") == username)

            elif normalized == 1:
                can_edit = False
                can_delete = False

            elif normalized == 0:
                # rejected: allow user fix
                if role in ["admin", "approver"]:
                    can_edit = True
                    can_delete = False
                elif role == "user":
                    can_edit = (upload.get("uploaded_by") == username)
                    can_delete = False

            upload["can_edit"] = can_edit
            upload["can_delete"] = can_delete

        return jsonify(uploads)
        
    except Exception as e:
        tb = traceback.format_exc()
        print(f"❌ Error in get_uploads: {e}")
        print(tb)
        config_obj = current_app.config.get("CONFIG_OBJ")
        log_error_db(session.get("username"), request.path, str(e), tb, config_obj)
        return jsonify({"error": str(e)}), 500

def user_can_edit_upload(cursor, upload_id: str, username: str, role: str) -> tuple:
    """
    Permission check based on excel_uploads.is_approved

    Rules:
    - Pending (is_approved IS NULL): editable (admin/approver + user-own)
    - Approved (is_approved = 1): LOCKED
    - Rejected (is_approved = 0): user can edit to fix and re-request reapproval
    """

    try:
        cursor.execute("""
            SELECT 
                id,
                uploaded_by,
                department,
                table_name,
                CAST(is_approved AS SIGNED) AS is_approved
            FROM excel_uploads
            WHERE id = %s
        """, (upload_id,))
        
        upload = cursor.fetchone()

        if not upload:
            return False, "Upload not found"

        appr = upload.get("is_approved")  # NULL / 1 / 0

        # ✅ APPROVED -> locked
        if appr == 1:
            return False, "Cannot edit approved uploads (locked)"

        # ✅ PENDING -> editable for admin/approver, user only if owner
        if appr is None:
            if role == "admin":
                return True, "Admin can edit pending uploads"
            if role == "approver":
                return True, "Approver can edit pending uploads"
            if role == "user":
                if upload.get("uploaded_by") == username:
                    return True, "User owns pending upload"
                return False, "Can only edit your own uploads"
            return False, "No permission"

        # ✅ REJECTED -> editable for user to fix (recommended)
        if appr == 0:
            if role == "admin":
                return True, "Admin can edit rejected uploads"
            if role == "approver":
                return True, "Approver can edit rejected uploads"
            if role == "user":
                if upload.get("uploaded_by") == username:
                    return True, "User can edit rejected upload (fix + reapproval)"
                return False, "Can only edit your own rejected uploads"
            return False, "No permission"

        return False, "Unknown approval state"

    except Exception as e:
        print(f"❌ Error checking edit permission: {e}")
        return False, str(e)



@api_bp.route("/api/can_edit_upload", methods=["POST"])
@with_db_connection
def api_can_edit_upload(cursor, conn):
    """Check if current user can edit an upload."""
    try:
        if "username" not in session:
            return jsonify({"can_edit": False, "reason": "Not authenticated"}), 401
        
        data = request.get_json()
        upload_id = data.get("upload_id")
        
        if not upload_id:
            return jsonify({"can_edit": False, "reason": "Missing upload_id"}), 400
        
        can_edit, reason = user_can_edit_upload(
            cursor,
            upload_id,
            session.get("username"),
            session.get("role")
        )
        
        return jsonify({
            "can_edit": can_edit,
            "reason": reason
        })
        
    except Exception as e:
        return jsonify({"can_edit": False, "reason": str(e)}), 500
    
@api_bp.route("/api/update_excel_cell", methods=["POST"])
@with_db_connection
def api_update_excel_cell(cursor, conn):
    """
    Update single cell (inline editing)
    """
    data = request.get_json(force=True)
    table = data.get("table")
    row_id = data.get("id")
    column = data.get("column")
    value = data.get("value")

    if not table or not row_id or not column:
        return jsonify({"error": "Missing table/id/column"}), 400

    if not user_can_edit_table(cursor, table):
        return jsonify({"error": "Permission denied"}), 403

    try:
        # detect primary key
        cursor.execute(f"SHOW KEYS FROM {table} WHERE Key_name='PRIMARY'")
        pk_res = cursor.fetchone()
        pk_col = pk_res["Column_name"] if pk_res else "id"

        # validate column exists
        cursor.execute(f"SHOW COLUMNS FROM {table}")
        cols_info = cursor.fetchall()
        col_names = [c["Field"] for c in cols_info]

        if column not in col_names:
            return jsonify({"error": "Invalid column"}), 400

        if column == pk_col or is_audit_column(column):
            return jsonify({"error": "Cannot edit this column"}), 400

        # ✅ USER restrictions
        if session.get("role") == "user":
            # user cannot edit approval/status columns
            if column == "is_approved":
                return jsonify({"error": "You cannot change approval status"}), 403

            # user can edit only rejected rows
            # cursor.execute(f"SELECT is_approved FROM {table} WHERE {pk_col}=%s",(row_id,))
            # rr = cursor.fetchone()
            # if not rr:
            #     return jsonify({"error": "Row not found"}), 404

            # if rr.get("is_approved") != 0:
            #     return jsonify({"error": "Only rejected rows can be edited"}), 403


        # FK support
        if column == "year_id":
            value = resolve_year(cursor, value)
        elif column.endswith("_id"):
            value = fk_value_to_id(cursor, column, value, LOOKUP_CONFIG)

# =========================
        # ✅ update cell
        # =========================
        sql = f"""
            UPDATE {table}
            SET {column}=%s,
                updated_by=%s,
                updated_date=NOW()
            WHERE {pk_col}=%s
        """
        cursor.execute(sql, (value, session.get("username"), row_id))
        conn.commit()

        return jsonify({"message": "Cell updated"})

    except Exception as e:
        tb = traceback.format_exc()
        config_obj = current_app.config.get("CONFIG_OBJ")
        if config_obj:
            log_error_db(
                session.get("username"),
                request.path,
                str(e),
                tb,
                config_obj
            )
        conn.rollback()
        return jsonify({"error": str(e)}), 500

@api_bp.route("/api/set_row_status", methods=["POST"])
@with_db_connection
def api_set_row_status(cursor, conn):
    """
    Approver sets row approval ONLY using is_approved:

    is_approved = NULL  -> Pending
    is_approved = 1     -> Approved
    is_approved = 0     -> Rejected

    NOTE: status_ will NOT be updated anymore.
    """
    data = request.get_json(force=True)
    table = data.get("table")
    row_id = data.get("id")
    is_approved_val = data.get("status")  # frontend sends 1 / 0 / null

    if session.get("role") not in ["admin", "approver"]:
        return jsonify({"error": "Permission denied"}), 403

    if not table or not row_id:
        return jsonify({"error": "Missing table/id"}), 400

    try:
        # detect pk
        cursor.execute(f"SHOW KEYS FROM `{table}` WHERE Key_name='PRIMARY'")
        pk_res = cursor.fetchone()
        pk_col = pk_res["Column_name"] if pk_res else "id"

        # normalize incoming
        if is_approved_val in [None, "", "null", "NULL"]:
            is_approved_val = None
        elif str(is_approved_val) == "1":
            is_approved_val = 1
        else:
            is_approved_val = 0

        sql = f"""
            UPDATE `{table}`
            SET is_approved=%s,
                updated_by=%s,
                updated_date=NOW()
            WHERE `{pk_col}`=%s
        """
        cursor.execute(sql, (is_approved_val, session.get("username"), row_id))
        conn.commit()

        return jsonify({"message": "Row approval updated", "is_approved": is_approved_val})

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500

@api_bp.route("/api/request_reapproval", methods=["POST"])
@with_db_connection
def api_request_reapproval(cursor, conn):
    """
    User requests reapproval after fixing rejected rows.
    - Changes rejected rows (status_=0) -> pending (NULL)
    - Sets excel_uploads.status_ = NULL
    """
    if "username" not in session:
        return jsonify({"error": "Not logged in"}), 401

    data = request.get_json(force=True)
    upload_id = data.get("upload_id")
    table = data.get("table")

    if not upload_id or not table:
        return jsonify({"error": "Missing upload_id/table"}), 400

    try:
        # ✅ verify upload ownership (user can request only their upload)
        cursor.execute("""
            SELECT id, uploaded_by,status_
            FROM excel_uploads
            WHERE id=%s
        """, (upload_id,))
        up = cursor.fetchone()

        if not up:
            return jsonify({"error": "Upload not found"}), 404

       # if session.get("role") == "user" and up["uploaded_by"] != session["username"]:
        #    return jsonify({"error": "Not your upload"}), 403

        if up["status_"] != 0:
            # content changed by nanda
            return jsonify({"error": "Only rejected uploads can request reapproval"}), 400

        # ✅ reset rejected rows → pending
        cursor.execute(f"""
            UPDATE `{table}`
            SET is_approved=NULL,
                updated_by=%s,
                updated_date=NOW()
            WHERE upload_id=%s AND is_approved=0
        """, (session["username"], upload_id))

        # ✅ reset upload → pending
        cursor.execute("""
            UPDATE excel_uploads
            SET status_=NULL,
                updated_by=%s,
                updated_date=NOW()
            WHERE id=%s
        """, (session["username"], upload_id))

        conn.commit()
        return jsonify({"message": "Reapproval requested"})

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    


@api_bp.route("/api/check_upload_review_status")
@with_db_connection
def api_check_upload_review_status(cursor, conn):
    """
    Approver validation:
    - If any row is_approved IS NULL => pending exists => block approve/reject
    - If any row is_approved = 0 => rejected exists => block approve (allow reject)
    Works for ALL transaction tables.
    """
    upload_id = request.args.get("upload_id")

    if not upload_id:
        return jsonify({"error": "Missing upload_id"}), 400

    try:
        # find transaction table
        cursor.execute("SELECT table_name FROM excel_uploads WHERE id=%s", (upload_id,))
        up = cursor.fetchone()
        if not up:
            return jsonify({"error": "Upload not found"}), 404

        table = up["table_name"]

        # ✅ check pending rows (NULL)
        cursor.execute(f"""
            SELECT COUNT(*) AS pending_count
            FROM `{table}`
            WHERE upload_id=%s AND is_approved IS NULL
        """, (upload_id,))
        pending_count = int(cursor.fetchone()["pending_count"])

        # ✅ check rejected rows
        cursor.execute(f"""
            SELECT COUNT(*) AS rejected_count
            FROM `{table}`
            WHERE upload_id=%s AND is_approved = 0
        """, (upload_id,))
        rejected_count = int(cursor.fetchone()["rejected_count"])

        return jsonify({
            "pending_count": pending_count,
            "rejected_count": rejected_count,
            "has_pending": pending_count > 0,
            "has_rejected": rejected_count > 0
        })

    except Exception as e:
        tb = traceback.format_exc()
        config_obj = current_app.config.get("CONFIG_OBJ")
        log_error_db(session.get("username"), request.path, str(e), tb, config_obj)
        return jsonify({"error": str(e)}), 500

@api_bp.route("/api/check_all_rows_reviewed")
@with_db_connection
def check_all_rows_reviewed(cursor, conn):
    upload_id = request.args.get("upload_id")
    if not upload_id:
        return jsonify({"error": "Missing upload_id"}), 400

    try:
        # get table for upload
        cursor.execute("SELECT table_name FROM excel_uploads WHERE id=%s", (upload_id,))
        up = cursor.fetchone()
        if not up:
            return jsonify({"error": "Upload not found"}), 404

        table = up["table_name"]

        # ✅ IMPORTANT: check is_approved (not status_)
        cursor.execute(f"""
            SELECT COUNT(*) AS pending_count
            FROM `{table}`
            WHERE is_approved IS NULL
        """)
        pending_count = int(cursor.fetchone()["pending_count"])

        return jsonify({
            "pending_count": pending_count,
            "has_pending": pending_count > 0
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route("/api/years")
@with_db_connection
def api_years(cursor, conn):
    """
    Return unique financial years for dropdown.
    If multiple rows exist with same year_desc,
    only one will be returned.
    """
    cursor.execute("""
        SELECT MAX(year_id) AS year_id, year_desc
        FROM tbl_year_master
        GROUP BY year_desc
        ORDER BY year_desc DESC
    """)
    return jsonify(cursor.fetchall())


@api_bp.route("/api/upload_row_summary")
@with_db_connection
def upload_row_summary(cursor, conn):
    upload_id = request.args.get("upload_id")

    if not upload_id:
        return jsonify({"error": "Missing upload_id"}), 400

    # find table
    cursor.execute("""
        SELECT table_name
        FROM excel_uploads
        WHERE id=%s
    """, (upload_id,))
    up = cursor.fetchone()

    if not up:
        return jsonify({"error": "Upload not found"}), 404

    table = up["table_name"]

    cursor.execute(f"""
        SELECT
            SUM(CASE WHEN is_approved IS NULL THEN 1 ELSE 0 END) AS pending_count,
            SUM(CASE WHEN is_approved = 0 THEN 1 ELSE 0 END) AS rejected_count,
            SUM(CASE WHEN is_approved = 1 THEN 1 ELSE 0 END) AS approved_count
        FROM `{table}`
        WHERE upload_id=%s
    """, (upload_id,))

    r = cursor.fetchone()

    return jsonify({
        "pending": int(r["pending_count"] or 0),
        "rejected": int(r["rejected_count"] or 0),
        "approved": int(r["approved_count"] or 0)
    })