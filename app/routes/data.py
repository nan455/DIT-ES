"""Data viewing, editing, and upload routes."""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session, send_file
import datetime
import pandas as pd
import io
import traceback
import json
from werkzeug.utils import secure_filename
from app.utils.database import with_db_connection, log_error_db
from app.utils.validators import (
    is_audit_column,
    is_refno_column,
    resolve_year,
    fk_value_to_id,
)
from app.constants import LOOKUP_CONFIG
from app.utils.excel_helpers import load_metadata_for_table, generate_excel_template
from flask import current_app
from flask import abort
from reportlab.platypus import SimpleDocTemplate, Table
from flask import Blueprint, render_template, request

data_bp = Blueprint("data", __name__)

@data_bp.route("/report/view")
def report_view():
    table = request.args.get("table")

    if not table:
        return "Table not specified", 400

    return render_template(
        "report_view.html",
        table=table
    )


@data_bp.route("/user_dashboard")
def user_dashboard():
    """User dashboard page."""
    if "username" not in session:
        return redirect(url_for("auth.login_page"))
    return render_template("user_dashboard.html")


@data_bp.route("/view_excel_data")
@with_db_connection  # ✅ This line is REQUIRED
def view_excel_data(cursor, conn):  # ✅ Add cursor, conn parameters
    """View/edit table data page."""
    if "username" not in session:
        return redirect(url_for("auth.login_page"))

    table = request.args.get("table")
    mode = request.args.get("mode", "view")
    
    # Get report_name
    cursor.execute("SELECT report_name FROM txn_registry WHERE target_table_name = %s", (table,))
    result = cursor.fetchone()
    report_name = result["report_name"] if result else table
    
    return render_template("view_excel_data.html", table=table, mode=mode, report_name=report_name)


@data_bp.route("/download_register_template")
@with_db_connection
def download_register_template(cursor, conn):
    """Download Excel template for a transaction table."""
    table = request.args.get("table")
    if not table:
        return jsonify({"error": "Missing table parameter"}), 400

    try:
        output = generate_excel_template(cursor, table, LOOKUP_CONFIG, {})
        filename = f"{table}_template.xlsx"

        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        tb = traceback.format_exc()
        config_obj = current_app.config.get("CONFIG_OBJ")
        log_error_db(session.get("username"), request.path, str(e), tb, config_obj)
        print(" ERROR (template):", e)
        print(tb)
        return jsonify({"error": "Template generation failed"}), 500

#### JSON UPLOAD HANDLER ###
# def _process_upload_transaction_json(cursor, conn, table, file_obj):
#     """
#     Process uploaded transaction JSON file.
#     Uses SAME config and helpers as Excel upload.
#     """
#     if "username" not in session:
#         return {"error": "Unauthorized"}, 401

#     replace_existing = (
#         request.form.get("replace_existing", "false").lower() == "true"
#     )

#     # -------------------------------------------------
#     # Load DB columns
#     # -------------------------------------------------
#     try:
#         cursor.execute(f"SHOW COLUMNS FROM {table}")
#         cols_info = cursor.fetchall()
#         db_cols = [c["Field"] for c in cols_info]
#     except Exception as e:
#         tb = traceback.format_exc()
#         log_error_db(
#             session.get("username"),
#             request.path,
#             str(e),
#             tb,
#             current_app.config.get("CONFIG_OBJ")
#         )
#         return {"error": f"Target table error: {e}"}, 400

#     # -------------------------------------------------
#     # Read JSON
#     # -------------------------------------------------
#     try:
#         file_obj.seek(0)
#         raw = json.load(file_obj)
        
#         # Handle wrapped format: {"table_name": [rows]}
#         if isinstance(raw, dict):
#             if len(raw) == 1 and isinstance(list(raw.values())[0], list):
#                 raw = list(raw.values())[0]
#             else:
#                 raw = [raw]
        
#         if not isinstance(raw, list) or not raw:
#             return {"error": "JSON has no rows or invalid format"}, 400
            
#         df = pd.DataFrame(raw)
        
#     except Exception as e:
#         tb = traceback.format_exc()
#         log_error_db(
#             session.get("username"),
#             request.path,
#             str(e),
#             tb,
#             current_app.config.get("CONFIG_OBJ")
#         )
#         return {"error": f"Unable to read JSON: {e}"}, 400

#     if df.empty:
#         return {"error": "Uploaded file is empty"}, 400

#     df.fillna("", inplace=True)

#     # -------------------------------------------------
#     # Metadata mapping (SAME AS EXCEL)
#     # -------------------------------------------------
#     header_to_col = load_metadata_for_table(cursor, table)
#     for c in db_cols:
#         header_to_col.setdefault(c.lower(), c)
#         header_to_col.setdefault(c.replace("_", " ").lower(), c)

#     parsed_rows = []

#     # -------------------------------------------------
#     # Parse JSON rows (SAME AS EXCEL)
#     # -------------------------------------------------
#     for _, row in df.iterrows():
#         row_data = {}

#         for header in df.columns:
#             raw_val = row[header]
#             if str(raw_val).strip() == "":
#                 continue

#             key = header.strip().lower()
#             col = header_to_col.get(key) or header_to_col.get(key.replace(" ", "_"))

#             if not col or col not in db_cols:
#                 continue

#             if col == "id" or is_audit_column(col) or is_refno_column(col):
#                 continue

#             value = raw_val

#             if col == "year_id":
#                 value = resolve_year(cursor, value)
#             elif col.endswith("_id"):
#                 value = fk_value_to_id(cursor, col, value, LOOKUP_CONFIG)
#             elif isinstance(value, str):
#                 value = value.strip() or None

#             row_data[col] = value

#         if row_data:
#             parsed_rows.append(row_data)

#     if not parsed_rows:
#         return {"error": "No valid rows found to insert"}, 400

#     # -------------------------------------------------
#     # DUPLICATE CHECK (SAME AS EXCEL)
#     # -------------------------------------------------
#     if not replace_existing:
#         try:
#             cursor.execute(f"SHOW INDEX FROM {table} WHERE Non_unique = 0")
#             indexes = cursor.fetchall()

#             unique_cols = [
#                 i["Column_name"]
#                 for i in indexes
#                 if i["Key_name"] != "PRIMARY"
#             ]

#             if unique_cols:
#                 sample = parsed_rows[0]
#                 where = []
#                 values = []

#                 for col in unique_cols:
#                     if col in sample:
#                         where.append(f"{col} = %s")
#                         values.append(sample[col])

#                 if where:
#                     sql = f"""
#                         SELECT 1
#                         FROM {table}
#                         WHERE {' AND '.join(where)}
#                         LIMIT 1
#                     """
#                     cursor.execute(sql, values)
#                     if cursor.fetchone():
#                         return {
#                             "error": "Data already exists. Replace existing data?"
#                         }, 409

#         except Exception as e:
#             tb = traceback.format_exc()
#             log_error_db(
#                 session.get("username"),
#                 request.path,
#                 str(e),
#                 tb,
#                 current_app.config.get("CONFIG_OBJ")
#             )
#             return {"error": "Duplicate validation failed"}, 500

#     # -------------------------------------------------
#     # INSERT + UPSERT (SAME AS EXCEL)
#     # -------------------------------------------------
#     try:
#         now = datetime.datetime.now()
        
#         # ✅ FIXED: Match Excel logic - delete by filename too
#         filename = secure_filename(file_obj.filename) if hasattr(file_obj, 'filename') else 'upload.json'
        
#         if replace_existing:
#     # Delete only the rows uploaded by THIS specific file previously
#             cursor.execute("""
#                 SELECT id FROM excel_uploads
#                 WHERE table_name = %s 
#                 AND department = %s 
#                 AND filename = %s
#                 """, (table, session.get("department"), filename))
    
#             old_upload_ids = [row['id'] for row in cursor.fetchall()]
    
#         if old_upload_ids:
#             # Delete old data rows linked to this file's previous uploads
#             placeholders = ','.join(['%s'] * len(old_upload_ids))
#             cursor.execute(f"""
#                 DELETE FROM {table}
#                 WHERE upload_id IN ({placeholders})
#                 """, old_upload_ids)
            
#             # Delete old upload records
#             cursor.execute(f"""
#                 DELETE FROM excel_uploads
#                 WHERE id IN ({placeholders})
#                 """, old_upload_ids)

#             # Insert upload log
#             cursor.execute(
#                 """
#                 INSERT INTO excel_uploads
#                 (filename, table_name, uploaded_by, department)
#                 VALUES (%s, %s, %s, %s)
#                 """,
#                 (
#                     secure_filename(file_obj.filename),
#                     table,
#                     session.get("username"),
#                     session.get("department"),
#                 ),
#             )
#             upload_id = cursor.lastrowid

#             # Check columns
#             all_cols = set()
#             for r in parsed_rows:
#                 all_cols.update(r.keys())

#             if "upload_id" in db_cols:
#                 all_cols.add("upload_id")
#             if "is_approved" in db_cols:
#                 all_cols.add("is_approved")
#             if "updated_by" in db_cols:
#                 all_cols.add("updated_by")
#             if "updated_date" in db_cols:
#                 all_cols.add("updated_date")
#             # ✅ FIXED: Only add status_ if it exists in the table
#             # if "status_" in db_cols:
#             #     all_cols.add("status_")

#             all_cols = sorted(all_cols)

#             insert_cols = ", ".join(f"{c}" for c in all_cols)
#             placeholders = ", ".join(["%s"] * len(all_cols))

#             update_cols = []
#             for c in all_cols:
#                 if c.endswith("_num") or c in (
#                     "updated_by", "updated_date", "upload_id", "is_approved"#, "status_"  # ✅ Added status_ here
#                 ):
#                     update_cols.append(f"{c} = VALUES({c})")

#             update_sql = ", ".join(update_cols)

#             sql = f"""
#                 INSERT INTO {table} ({insert_cols})
#                 VALUES ({placeholders})
#                 ON DUPLICATE KEY UPDATE
#                 {update_sql}
#             """

#             values = []
#             for r in parsed_rows:
#                 row = dict(r)
#                 row["upload_id"] = upload_id
#                 row["is_approved"] = None
#                 row["updated_by"] = session.get("username")
#                 row["updated_date"] = now
#                 # ✅ FIXED: Only set status_ if column exists
#                 #if "status_" in db_cols:
#                 row["status_"] = 1
                    
#                 values.append(tuple(row.get(c) for c in all_cols))

#             cursor.executemany(sql, values)
#             conn.commit()

#             return {
#                 "message": f"{len(values)} rows uploaded successfully",
#                 "upload_id": upload_id
#             }, 200

#     except Exception as e:
#         conn.rollback()
#         tb = traceback.format_exc()
#         log_error_db(
#             session.get("username"),
#             request.path,
#             str(e),
#             tb,
#             current_app.config.get("CONFIG_OBJ")
#         )
#         return {"error": str(e)}, 500 

def _process_upload_transaction_json(cursor, conn, table, file_obj):
    """
    Process uploaded transaction JSON file.
    Uses SAME config and helpers as Excel upload.
    """

    if "username" not in session:
        return {"error": "Unauthorized"}, 401

    replace_existing = (
        request.form.get("replace_existing", "false").lower() == "true"
    )

    # -------------------------------------------------
    # Load DB columns
    # -------------------------------------------------
    try:
        cursor.execute(f"SHOW COLUMNS FROM {table}")
        cols_info = cursor.fetchall()
        db_cols = [c["Field"] for c in cols_info]
    except Exception as e:
        tb = traceback.format_exc()
        log_error_db(
            session.get("username"),
            request.path,
            str(e),
            tb,
            current_app.config.get("CONFIG_OBJ")
        )
        return {"error": f"Target table error: {e}"}, 400

    # -------------------------------------------------
    # Read JSON
    # -------------------------------------------------
    try:
        file_obj.seek(0)
        raw = json.load(file_obj)
        
        # Handle wrapped format: {"table_name": [rows]}
        if isinstance(raw, dict):
            if len(raw) == 1 and isinstance(list(raw.values())[0], list):
                raw = list(raw.values())[0]
            else:
                raw = [raw]
        
        if not isinstance(raw, list) or not raw:
            return {"error": "JSON has no rows or invalid format"}, 400
            
        df = pd.DataFrame(raw)
        
    except Exception as e:
        tb = traceback.format_exc()
        log_error_db(
            session.get("username"),
            request.path,
            str(e),
            tb,
            current_app.config.get("CONFIG_OBJ")
        )
        return {"error": f"Unable to read JSON: {e}"}, 400

    if df.empty:
        return {"error": "Uploaded file is empty"}, 400

    df.fillna("", inplace=True)

    # -------------------------------------------------
    # Metadata mapping (SAME AS EXCEL)
    # -------------------------------------------------
    header_to_col = load_metadata_for_table(cursor, table)
    for c in db_cols:
        header_to_col.setdefault(c.lower(), c)
        header_to_col.setdefault(c.replace("_", " ").lower(), c)

    parsed_rows = []

    # -------------------------------------------------
    # Parse JSON rows (SAME AS EXCEL)
    # -------------------------------------------------
    for _, row in df.iterrows():
        row_data = {}

        for header in df.columns:
            raw_val = row[header]
            if str(raw_val).strip() == "":
                continue

            key = header.strip().lower()
            col = header_to_col.get(key) or header_to_col.get(key.replace(" ", "_"))

            if not col or col not in db_cols:
                continue

            if col == "id" or is_audit_column(col) or is_refno_column(col):
                continue

            value = raw_val

            if col == "year_id":
                value = resolve_year(cursor, value)
            elif col.endswith("_id"):
                value = fk_value_to_id(cursor, col, value, LOOKUP_CONFIG)
            elif isinstance(value, str):
                value = value.strip() or None

            row_data[col] = value

        if row_data:
            parsed_rows.append(row_data)

    if not parsed_rows:
        return {"error": "No valid rows found to insert"}, 400

    # -------------------------------------------------
    # DUPLICATE CHECK (SAME AS EXCEL)
    # -------------------------------------------------
    if not replace_existing:
        try:
            cursor.execute(f"SHOW INDEX FROM {table} WHERE Non_unique = 0")
            indexes = cursor.fetchall()

            unique_cols = [
                i["Column_name"]
                for i in indexes
                if i["Key_name"] != "PRIMARY"
            ]

            if unique_cols:
                sample = parsed_rows[0]
                where = []
                values = []

                for col in unique_cols:
                    if col in sample:
                        where.append(f"{col} = %s")
                        values.append(sample[col])

                if where:
                    sql = f"""
                        SELECT 1
                        FROM {table}
                        WHERE {' AND '.join(where)}
                        LIMIT 1
                    """
                    cursor.execute(sql, values)
                    if cursor.fetchone():
                        return {
                            "error": "Data already exists. Replace existing data?"
                        }, 409

        except Exception as e:
            tb = traceback.format_exc()
            log_error_db(
                session.get("username"),
                request.path,
                str(e),
                tb,
                current_app.config.get("CONFIG_OBJ")
            )
            return {"error": "Duplicate validation failed"}, 500

    # -------------------------------------------------
    # INSERT + UPSERT (SAME AS EXCEL)
    # -------------------------------------------------
    try:
        now = datetime.datetime.now()
        
        # ✅ FIXED: Match Excel logic - delete by filename too
        filename = secure_filename(file_obj.filename) if hasattr(file_obj, 'filename') else 'upload.json'
        
        if replace_existing:
        # Delete only the rows uploaded by THIS specific file previously
            cursor.execute("""
               SELECT id FROM excel_uploads
               WHERE table_name = %s 
               AND department = %s 
               AND filename = %s
               """, (table, session.get("department"), filename))
    
            old_upload_ids = [row['id'] for row in cursor.fetchall()]
    
            if old_upload_ids:
            # Delete old data rows linked to this file's previous uploads
               placeholders = ','.join(['%s'] * len(old_upload_ids))
               cursor.execute(f"""
               DELETE FROM `{table}`
               WHERE upload_id IN ({placeholders})
               """, old_upload_ids)
        
               # Delete old upload records
               cursor.execute(f"""
               DELETE FROM excel_uploads
               WHERE id IN ({placeholders})
               """, old_upload_ids)

        # Insert upload log
        cursor.execute(
            """
            INSERT INTO excel_uploads
            (filename, table_name, uploaded_by, department)
            VALUES (%s, %s, %s, %s)
            """,
            (
                secure_filename(file_obj.filename),
                table,
                session.get("username"),
                session.get("department"),
            ),
        )
        upload_id = cursor.lastrowid

        # Check columns
        all_cols = set()
        for r in parsed_rows:
            all_cols.update(r.keys())

        if "upload_id" in db_cols:
            all_cols.add("upload_id")
        if "is_approved" in db_cols:
            all_cols.add("is_approved")
        if "updated_by" in db_cols:
            all_cols.add("updated_by")
        if "updated_date" in db_cols:
            all_cols.add("updated_date")
        # ✅ FIXED: Only add status_ if it exists in the table
        # if "status_" in db_cols:
        #     all_cols.add("status_")

        all_cols = sorted(all_cols)

        insert_cols = ", ".join(f"{c}" for c in all_cols)
        placeholders = ", ".join(["%s"] * len(all_cols))

        update_cols = []
        for c in all_cols:
            if c.endswith("_num") or c in (
                "updated_by", "updated_date", "upload_id", "is_approved"#, "status_"  # ✅ Added status_ here
            ):
                update_cols.append(f"{c} = VALUES({c})")

        update_sql = ", ".join(update_cols)

        sql = f"""
            INSERT INTO {table} ({insert_cols})
            VALUES ({placeholders})
            ON DUPLICATE KEY UPDATE
            {update_sql}
        """

        values = []
        for r in parsed_rows:
            row = dict(r)
            row["upload_id"] = upload_id
            row["is_approved"] = None
            row["updated_by"] = session.get("username")
            row["updated_date"] = now
            # ✅ FIXED: Only set status_ if column exists
            #if "status_" in db_cols:
            row["status_"] = 1
                
            values.append(tuple(row.get(c) for c in all_cols))

        cursor.executemany(sql, values)
        conn.commit()

        return {
            "message": f"{len(values)} rows uploaded successfully",
            "upload_id": upload_id
        }, 200

    except Exception as e:
        conn.rollback()
        tb = traceback.format_exc()
        log_error_db(
            session.get("username"),
            request.path,
            str(e),
            tb,
            current_app.config.get("CONFIG_OBJ")
        )
        return {"error": str(e)}, 500
#EXCEL UPLOAD HANDLER####
def _process_upload_transaction(cursor, conn, table, file_obj):
    """
    Process uploaded transaction Excel file.
    """

    import pandas as pd
    import datetime
    import traceback
    from flask import session, request
    from werkzeug.utils import secure_filename

    # -------------------------------------------------
    # AUTH
    # -------------------------------------------------
    if "username" not in session:
        return {"error": "Unauthorized"}, 401

    replace_existing = (
        request.form.get("replace_existing", "false").lower() == "true"
    )

    # -------------------------------------------------
    # LOAD TABLE COLUMNS
    # -------------------------------------------------
    try:
        cursor.execute(f"SHOW COLUMNS FROM {table}")
        cols_info = cursor.fetchall()
        db_cols = [c["Field"] for c in cols_info]
    except Exception as e:
        return {"error": f"Target table error: {e}"}, 400

    # -------------------------------------------------
    # READ EXCEL
    # -------------------------------------------------
    try:
        df = pd.read_excel(file_obj)
    except Exception as e:
        return {"error": f"Unable to read Excel: {e}"}, 400

    if df.empty:
        return {"error": "Uploaded file is empty"}, 400

    df.fillna("", inplace=True)

    # -------------------------------------------------
    # METADATA MAP
    # -------------------------------------------------
    header_to_col = load_metadata_for_table(cursor, table)

    for c in db_cols:
        header_to_col.setdefault(c.lower(), c)
        header_to_col.setdefault(c.replace("_", " ").lower(), c)

    parsed_rows = []

    # -------------------------------------------------
    # PARSE EXCEL
    # -------------------------------------------------
    for _, row in df.iterrows():
        row_data = {}

        for header in df.columns:
            val = row[header]

            if str(val).strip() == "":
                continue

            key = header.strip().lower()
            col = header_to_col.get(key) or header_to_col.get(key.replace(" ", "_"))

            if not col or col not in db_cols:
                continue

            if col == "id" or is_audit_column(col) or is_refno_column(col):
                continue

            if col == "year_id":
                val = resolve_year(cursor, val)
            elif col.endswith("_id"):
                val = fk_value_to_id(cursor, col, val, LOOKUP_CONFIG)
            elif isinstance(val, str):
                val = val.strip() or None

            row_data[col] = val

        if row_data:
            parsed_rows.append(row_data)

    if not parsed_rows:
        return {"error": "No valid rows found to insert"}, 400

    # -------------------------------------------------
    # FIND UNIQUE KEYS
    # -------------------------------------------------
    cursor.execute(f"SHOW INDEX FROM {table} WHERE Non_unique=0")
    indexes = cursor.fetchall()

    unique_cols = [
        i["Column_name"]
        for i in indexes
        if i["Key_name"] != "PRIMARY"
    ]

    # -------------------------------------------------
    # DUPLICATE CHECK
    # -------------------------------------------------
    if unique_cols and not replace_existing:

        sample = parsed_rows[0]
        where = []
        vals = []

        for c in unique_cols:
            if c in sample:
                where.append(f"{c}=%s")
                vals.append(sample[c])

        if where:
            cursor.execute(
                f"""
                SELECT 1 FROM {table}
                WHERE {' AND '.join(where)}
                LIMIT 1
                """,
                vals
            )

            if cursor.fetchone():
                return {
                    "error": "Data already exists. Replace existing data?"
                }, 409

    # -------------------------------------------------
    # INSERT / REPLACE
    # -------------------------------------------------
    try:
        now = datetime.datetime.now()
        old_upload_ids = []

        # ---------- DELETE MATCHING OLD DATA ----------
        if replace_existing and unique_cols:

            sample = parsed_rows[0]
            where = []
            vals = []

            for c in unique_cols:
                if c in sample:
                    where.append(f"{c}=%s")
                    vals.append(sample[c])

            if where:

                cursor.execute(
                    f"""
                    SELECT DISTINCT upload_id
                    FROM {table}
                    WHERE {' AND '.join(where)}
                    """,
                    vals
                )

                rows = cursor.fetchall()
                old_upload_ids = [
                    r["upload_id"] for r in rows if r["upload_id"]
                ]

                cursor.execute(
                    f"""
                    DELETE FROM {table}
                    WHERE {' AND '.join(where)}
                    """,
                    vals
                )

        # ---------- DELETE ONLY RELATED UPLOAD LOGS ----------
        if old_upload_ids:
            placeholders = ",".join(["%s"] * len(old_upload_ids))
            cursor.execute(
                f"""
                DELETE FROM excel_uploads
                WHERE id IN ({placeholders})
                """,
                old_upload_ids
            )

        # ---------- CREATE NEW UPLOAD LOG ----------
        cursor.execute(
            """
            INSERT INTO excel_uploads
            (filename, table_name, uploaded_by, department)
            VALUES (%s,%s,%s,%s)
            """,
            (
                secure_filename(file_obj.filename),
                table,
                session.get("username"),
                session.get("department"),
            )
        )

        upload_id = cursor.lastrowid

        # ---------- PREPARE INSERT ----------
        all_cols = set()
        for r in parsed_rows:
            all_cols.update(r.keys())

        if "upload_id" in db_cols:
            all_cols.add("upload_id")
        if "is_approved" in db_cols:
            all_cols.add("is_approved")
        if "status_" in db_cols:
            all_cols.add("status_")
        if "updated_by" in db_cols:
            all_cols.add("updated_by")
        if "updated_date" in db_cols:
            all_cols.add("updated_date")

        all_cols = sorted(all_cols)

        insert_cols = ", ".join(f"{c}" for c in all_cols)
        placeholders = ", ".join(["%s"] * len(all_cols))

        update_cols = []
        for c in all_cols:
            if c.endswith("_num") or c in (
                "upload_id",
                "updated_by",
                "updated_date",
                "is_approved",
                "status_",   # important
            ):
                update_cols.append(f"{c}=VALUES({c})")

        update_sql = ", ".join(update_cols)

        sql = f"""
            INSERT INTO {table} ({insert_cols})
            VALUES ({placeholders})
            ON DUPLICATE KEY UPDATE
            {update_sql}
        """

        values = []

        for r in parsed_rows:
            row = dict(r)
            row["upload_id"] = upload_id
            row["is_approved"] = None
            row["updated_by"] = session.get("username")
            row["updated_date"] = now

            if "status_" in db_cols:
                row["status_"] = 1  # ✅ prevent default 1

            values.append(tuple(row.get(c) for c in all_cols))

        cursor.executemany(sql, values)
        conn.commit()

        return {
            "message": f"{len(values)} rows uploaded successfully",
            "upload_id": upload_id
        }, 200

    except Exception as e:
        conn.rollback()
        return {"error": str(e)}, 500

# def get_column_labels(table):
#     rows = db.fetch("""
#         SELECT column_name, display_label
#         FROM tbl_column_metadata
#         WHERE table_name = %s
#     """, (table,))
#     return {r['column_name']: r['display_label'] for r in rows}
      
def get_report_columns(cursor, table):
    cursor.execute("""
        SELECT column_name, display_label
        FROM tbl_column_metadata
        WHERE table_name = %s
          AND show_in_report = 1
        ORDER BY display_order
    """, (table,))
    rows = cursor.fetchall()
    return rows

#### JSON & EXCEL UPLOAD HANDLER ####
@data_bp.route("/upload_transaction", methods=["POST"])
@with_db_connection
def upload_transaction(cursor, conn):
    table = request.form.get("table_name")
    file = request.files.get("file")

    if not table:
        return jsonify({"error": "Missing table_name"}), 400
    if not file:
        return jsonify({"error": "No file uploaded"}), 400

    filename = file.filename.lower()

    # Excel handler (already exists)
    if filename.endswith((".xlsx")):
        res, code = _process_upload_transaction(cursor, conn, table, file)

    # JSON handler (new)
    elif filename.endswith(".json"):
        res, code = _process_upload_transaction_json(cursor, conn, table, file)

    else:
        return jsonify({"error": "Only Excel or JSON files allowed"}), 400

    return jsonify(res), code


@data_bp.route("/upload_accident_register", methods=["POST"])
@with_db_connection
def upload_accident_register(cursor, conn):
    """Upload accident register data from Excel."""
    table = request.form.get("table_name")
    file = request.files.get("file")

    if not table:
        return jsonify({"error": "Missing table_name"}), 400
    if not file:
        return jsonify({"error": "No file uploaded"}), 400

    res, code = _process_upload_transaction(cursor, conn, table, file)
    return jsonify(res), code


@data_bp.route("/download_excel")
@with_db_connection
def download_excel(cursor, conn):
    """Download table data as Excel with FK names instead of IDs."""

    table = request.args.get("table")
    filename = request.args.get("filename", f"{table}.xlsx")

    hide_cols = request.args.get("hide_cols", "")
    hide_cols = [c.strip() for c in hide_cols.split(",") if c.strip()]

    try:
        # -----------------------------------
        # build SELECT with FK joins
        # -----------------------------------
        select_parts = [f"t.*"]
        joins = []

        for fk_col, cfg in LOOKUP_CONFIG.items():

            master_table, name_col, id_col = cfg

            # check FK column exists in this table
            cursor.execute(f"SHOW COLUMNS FROM {table} LIKE %s", (fk_col,))
            if not cursor.fetchone():
                continue

            alias = f"m_{fk_col}"

            joins.append(
                f"LEFT JOIN {master_table} {alias} "
                f"ON t.{fk_col} = {alias}.{id_col}"
            )

            select_parts.append(
                f"{alias}.{name_col} AS {fk_col}_name"
            )

        sql = f"""
            SELECT {", ".join(select_parts)}
            FROM {table} t
            {' '.join(joins)}
        """

        cursor.execute(sql)
        rows = cursor.fetchall()
        df = pd.DataFrame(rows)

        # -----------------------------------
        # replace fk_id with fk_name
        # -----------------------------------
        for fk_col in LOOKUP_CONFIG.keys():
            name_col = fk_col + "_name"

            if name_col in df.columns:
                df[fk_col] = df[name_col]
                df.drop(columns=[name_col], inplace=True)

        # -----------------------------------
        # hide audit columns
        # -----------------------------------
        if not df.empty and hide_cols:
            df.drop(columns=[c for c in hide_cols if c in df.columns], inplace=True)

        # -----------------------------------
        # export excel
        # -----------------------------------
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False)

        output.seek(0)

        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    except Exception as e:
        tb = traceback.format_exc()
        print(tb)

        config_obj = current_app.config.get("CONFIG_OBJ")
        if config_obj:
            log_error_db(session.get("username"), request.path, str(e), tb, config_obj)

        return jsonify({"error": str(e)}), 500


@data_bp.route("/uploads", methods=["GET"])
@with_db_connection
def uploads_list(cursor, conn):
    """Get list of uploads WITH STATUS - FIXED VERSION."""
    import json
    import decimal
    import datetime
    
    class CustomJSONEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, (datetime.datetime, datetime.date)):
                return obj.isoformat()
            if isinstance(obj, decimal.Decimal):
                return float(obj)
            return super().default(obj)
    
    try:
        department = session.get("department")
        role = session.get("role")
        username = session.get("username")
        
        # print(f"\n🔍 [data.py] Loading uploads for: {username} ({role}) - Dept: {department}")
        
        #  CRITICAL FIX: Include status_ with CAST for consistent type
        if role == "admin":
            cursor.execute("""
                SELECT 
                    id, 
                    filename, 
                    table_name, 
                    updated_by, 
                    department, 
                    updated_date,
                    CAST(status_ AS SIGNED) as status_,
                           rejection_reason
                FROM excel_uploads 
                ORDER BY updated_date DESC
            """)
        else:
            dept = request.args.get("department") or department
            cursor.execute("""
                SELECT 
                    id, 
                    filename, 
                    table_name, 
                    updated_by, 
                    department, 
                    updated_date,
                    CAST(status_ AS SIGNED) as status_,
                           rejection_reason
                FROM excel_uploads 
                WHERE department=%s 
                ORDER BY updated_date DESC
            """, (dept,))
        
        rows = cursor.fetchall()
        
        # print(f"📊 Found {len(rows)} uploads")
        
        #  CONSISTENT STATUS NORMALIZATION
        for upload in rows:
            status = upload.get('status_')
            upload_id = upload.get('id')
            
            # print(f"   Upload #{upload_id}: status_ = {status} (type: {type(status)})")
            
            # Normalize status value
            if status is None or status == '' or status == 'NULL':
                normalized_status = None  # Pending
            elif status in [1, True, '1']:
                normalized_status = 1  # Approved
            elif status in [0, False, '0']:
                normalized_status = 0  # Rejected
            else:
                normalized_status = None
            
            # Add status text for display
            if normalized_status is None:
                upload['status_text'] = 'Pending'
                upload['status_class'] = 'pending'
            elif normalized_status == 1:
                upload['status_text'] = 'Approved'
                upload['status_class'] = 'approved'
            elif normalized_status == 0:
                upload['status_text'] = 'Rejected'
                upload['status_class'] = 'rejected'
            else:
                upload['status_text'] = 'Unknown'
                upload['status_class'] = 'unknown'
            
            # Ensure status_ is normalized
            upload['status_'] = normalized_status
            
            #  NEW STRICT PERMISSION LOGIC
            # RULE: Only PENDING uploads can be edited/deleted
            # RULE: Approved and Rejected uploads are VIEW-ONLY (locked)
            
            can_edit = False
            can_delete = False
            
            if normalized_status is None:
                #  PENDING - Can edit and delete based on role
                if role == "admin":
                    can_edit = True
                    can_delete = True
                elif role == "approver":
                    can_edit = True
                    can_delete = True
                elif role == "user":
                    # User can only edit/delete their own uploads
                    can_edit = True
                    can_delete = True
                    
            elif normalized_status == 1:
                #  APPROVED - LOCKED (view-only for everyone)
                # can_edit = False
                # can_delete = False
                
                #  BACKUP: Uncomment to allow admin to edit/delete approved
                if role == "admin":
                    can_edit = True
                    can_delete = True
                
            elif normalized_status == 0:
                #  REJECTED - LOCKED (view-only for everyone)
                # can_edit = False
                # can_delete = False
                
                #  BACKUP: Uncomment to allow admin to edit/delete rejected
                if role == "admin":
                    can_edit = True
                    can_delete = True
            
            upload['can_edit'] = can_edit
            upload['can_delete'] = can_delete
            # print(f"      → Status: {upload['status_text']}, Can Edit: {can_edit}, Can Delete: {can_delete}")

        
        return current_app.response_class(
            response=json.dumps(rows, cls=CustomJSONEncoder),
            status=200,
            mimetype="application/json",
        )
        
    except Exception as e:
        tb = traceback.format_exc()
        print(f" Error in uploads_list: {e}")
        print(tb)
        config_obj = current_app.config.get("CONFIG_OBJ")
        log_error_db(session.get("username"), request.path, str(e), tb, config_obj)
        return jsonify({"error": str(e)}), 500


@data_bp.route("/uploads/<int:upload_id>", methods=["DELETE"])
@with_db_connection
def uploads_delete(cursor, conn, upload_id):
    try:
        # 1️⃣ Fetch upload info
        cursor.execute(
            "SELECT table_name, department FROM excel_uploads WHERE id=%s",
            (upload_id,)
        )
        upload = cursor.fetchone()
			   
												   

        if not upload:
														 
            return jsonify({"error": "Upload not found"}), 404

        table_name = upload["table_name"]
				 
										  

        # 2️⃣ Permission check
        if session.get("role") != "admin":
            if upload["department"] != session.get("department"):
                return jsonify({"error": "Permission denied"}), 403

        # 3️⃣ Check if table existed BEFORE upload (JSON)
        cursor.execute("""
            SELECT COUNT(*) AS cnt
            FROM information_schema.tables
            WHERE table_schema = DATABASE()
              AND table_name = %s
              AND create_time < (
                  SELECT uploaded_on FROM excel_uploads WHERE id = %s
              )
        """, (table_name, upload_id))

        existed_before = cursor.fetchone()["cnt"] > 0

        # 4️⃣ Delete logic
        if existed_before:
            # JSON upload → delete values only
            cursor.execute(f"DELETE FROM `{table_name}`")
        else:
            # Excel upload → drop table
            cursor.execute(f"DROP TABLE IF EXISTS `{table_name}`")
            print(f" Table {table_name} dropped as it was created by the upload.")

        # 5️⃣ Remove upload record
        cursor.execute(
            "DELETE FROM excel_uploads WHERE id=%s",
            (upload_id,)
        )

        conn.commit()
        return jsonify({"message": "Upload deleted successfully"})
							
																							 
									 

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500

##REPORT GENERATION FILTERS##

@data_bp.route("/api/years")
@with_db_connection
def api_years(cursor, conn):
    cursor.execute("SELECT year_id, year_desc FROM tbl_year_master ORDER BY year_desc")
    return jsonify(cursor.fetchall())


@data_bp.route("/api/regions")
@with_db_connection
def api_regions(cursor, conn):
    cursor.execute("SELECT region_id, region_desc FROM tbl_region_master ORDER BY region_desc")
    return jsonify(cursor.fetchall())


@data_bp.route("/api/units")
@with_db_connection
def api_units(cursor, conn):
    cursor.execute("SELECT unit_id, unit_measure FROM tbl_unit_master ORDER BY unit_measure")
    return jsonify(cursor.fetchall())

"""
Row-level remark API routes  +  PK-safe helper.
Paste these into data_routes.py (data_bp blueprint).

ROOT CAUSE FIX:
  Tables like tbl_livestock_census use 'livestock_census_refno' as PK, not 'id'.
  All WHERE clauses now call _get_pk_column() to resolve the real PK first.
"""

# ─────────────────────────────────────────────────────────────
# HELPER: resolve real primary key column for any table
# ─────────────────────────────────────────────────────────────
def _get_pk_column(cursor, table):
    """Returns the PRIMARY KEY column name. Fallback: 'id'."""
    cursor.execute("""
        SELECT COLUMN_NAME
        FROM information_schema.KEY_COLUMN_USAGE
        WHERE TABLE_SCHEMA    = DATABASE()
          AND TABLE_NAME      = %s
          AND CONSTRAINT_NAME = 'PRIMARY'
        ORDER BY ORDINAL_POSITION
        LIMIT 1
    """, (table,))
    row = cursor.fetchone()
    return row["COLUMN_NAME"] if row else "id"


# ─────────────────────────────────────────────────────────────
# GET /api/primary_key?table=
# Frontend calls this on load to get the PK column name
# ─────────────────────────────────────────────────────────────
@data_bp.route("/api/primary_key")
@with_db_connection
def api_primary_key(cursor, conn):
    table = request.args.get("table")
    if not table:
        return jsonify({"pk": "id"})
    pk = _get_pk_column(cursor, table)
    return jsonify({"pk": pk})


# ─────────────────────────────────────────────────────────────
# POST /api/set_row_status
# Body: { "table", "id", "status" (1/0/null), "upload_id" }
# ─────────────────────────────────────────────────────────────
@data_bp.route("/api/set_row_status", methods=["POST"])
@with_db_connection
def set_row_status(cursor, conn):
    if "username" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data      = request.get_json(force=True)
    table     = data.get("table")
    row_id    = data.get("id")
    status    = data.get("status")   # 1, 0, or None
    upload_id = data.get("upload_id")

    if not table or row_id is None:
        return jsonify({"error": "Missing table or id"}), 400

    try:
        pk_col = _get_pk_column(cursor, table)

        if status is None:
            cursor.execute(f"""
                UPDATE `{table}`
                SET is_approved  = NULL,
                    updated_by   = %s,
                    updated_date = NOW()
                WHERE `{pk_col}` = %s
            """, (session.get("username"), row_id))
        else:
            cursor.execute(f"""
                UPDATE `{table}`
                SET is_approved  = %s,
                    updated_by   = %s,
                    updated_date = NOW()
                WHERE `{pk_col}` = %s
            """, (int(status), session.get("username"), row_id))

        conn.commit()
        return jsonify({"message": "Row status updated"})

    except Exception as e:
        conn.rollback()
        tb = traceback.format_exc()
        config_obj = current_app.config.get("CONFIG_OBJ")
        if config_obj:
            log_error_db(session.get("username"), request.path, str(e), tb, config_obj)
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────
# POST /api/update_excel_cell
# Body: { "table", "id", "column", "value" }
# ─────────────────────────────────────────────────────────────
@data_bp.route("/api/update_excel_cell", methods=["POST"])
@with_db_connection
def update_excel_cell(cursor, conn):
    if "username" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data   = request.get_json(force=True)
    table  = data.get("table")
    row_id = data.get("id")
    col    = data.get("column")
    value  = data.get("value")

    if not table or row_id is None or not col:
        return jsonify({"error": "Missing table, id, or column"}), 400

    try:
        pk_col = _get_pk_column(cursor, table)

        cursor.execute(f"""
            UPDATE `{table}`
            SET `{col}`      = %s,
                updated_by   = %s,
                updated_date = NOW()
            WHERE `{pk_col}` = %s
        """, (value or None, session.get("username"), row_id))

        conn.commit()
        return jsonify({"message": "Cell updated"})

    except Exception as e:
        conn.rollback()
        tb = traceback.format_exc()
        config_obj = current_app.config.get("CONFIG_OBJ")
        if config_obj:
            log_error_db(session.get("username"), request.path, str(e), tb, config_obj)
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────
# POST /api/delete_excel_row
# Body: { "table", "id" }
# ─────────────────────────────────────────────────────────────
@data_bp.route("/api/delete_excel_row", methods=["POST"])
@with_db_connection
def delete_excel_row(cursor, conn):
    if "username" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data   = request.get_json(force=True)
    table  = data.get("table")
    row_id = data.get("id")

    if not table or row_id is None:
        return jsonify({"error": "Missing table or id"}), 400

    try:
        pk_col = _get_pk_column(cursor, table)

        cursor.execute(f"""
            DELETE FROM `{table}`
            WHERE `{pk_col}` = %s
        """, (row_id,))

        conn.commit()
        return jsonify({"message": "Row deleted"})

    except Exception as e:
        conn.rollback()
        tb = traceback.format_exc()
        config_obj = current_app.config.get("CONFIG_OBJ")
        if config_obj:
            log_error_db(session.get("username"), request.path, str(e), tb, config_obj)
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────
# GET /api/row_remarks?table=&upload_id=
# ─────────────────────────────────────────────────────────────
@data_bp.route("/api/row_remarks")
@with_db_connection
def get_row_remarks(cursor, conn):
    if "username" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    table     = request.args.get("table")
    upload_id = request.args.get("upload_id")

    if not table or not upload_id:
        return jsonify({"error": "Missing table or upload_id"}), 400

    try:
        pk_col = _get_pk_column(cursor, table)

        # Auto-create rejection_remark column if missing
        cursor.execute(f"SHOW COLUMNS FROM `{table}` LIKE 'rejection_remark'")
        if not cursor.fetchone():
            cursor.execute(f"""
                ALTER TABLE `{table}`
                ADD COLUMN rejection_remark TEXT NULL DEFAULT NULL
            """)
            conn.commit()

        cursor.execute(f"""
            SELECT `{pk_col}` AS id, rejection_remark
            FROM `{table}`
            WHERE upload_id = %s AND is_approved = 0
            ORDER BY `{pk_col}`
        """, (upload_id,))

        rows = cursor.fetchall()
        return jsonify({
            "rows": [{"id": r["id"], "remark": r["rejection_remark"] or ""} for r in rows]
        })

    except Exception as e:
        tb = traceback.format_exc()
        config_obj = current_app.config.get("CONFIG_OBJ")
        if config_obj:
            log_error_db(session.get("username"), request.path, str(e), tb, config_obj)
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────
# POST /api/save_row_remark
# Body: { "table", "row_id", "remark" }
# ─────────────────────────────────────────────────────────────
@data_bp.route("/api/save_row_remark", methods=["POST"])
@with_db_connection
def save_row_remark(cursor, conn):
    if "username" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    if session.get("role") not in ["approver", "admin"]:
        return jsonify({"error": "Permission denied"}), 403

    data   = request.get_json(force=True)
    table  = data.get("table")
    row_id = data.get("row_id")
    remark = (data.get("remark") or "").strip()

    if not table or not row_id:
        return jsonify({"error": "Missing table or row_id"}), 400

    try:
        pk_col = _get_pk_column(cursor, table)

        # Auto-create column if missing
        cursor.execute(f"SHOW COLUMNS FROM `{table}` LIKE 'rejection_remark'")
        if not cursor.fetchone():
            cursor.execute(f"""
                ALTER TABLE `{table}`
                ADD COLUMN rejection_remark TEXT NULL DEFAULT NULL
            """)

        cursor.execute(f"""
            UPDATE `{table}`
            SET rejection_remark = %s,
                updated_by       = %s,
                updated_date     = NOW()
            WHERE `{pk_col}` = %s
        """, (remark or None, session.get("username"), row_id))

        conn.commit()
        return jsonify({"message": "Remark saved"})

    except Exception as e:
        conn.rollback()
        tb = traceback.format_exc()
        config_obj = current_app.config.get("CONFIG_OBJ")
        if config_obj:
            log_error_db(session.get("username"), request.path, str(e), tb, config_obj)
        return jsonify({"error": str(e)}), 500