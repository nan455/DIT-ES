"""
table_builder_routes.py  (v3)
- No forced id column - user defines every column including PK/FK.
- key_type stored in tbl_column_metadata so template can exclude PK columns.
"""

from flask import Blueprint, request, jsonify, session
from app.utils.database import with_db_connection
import re, traceback

table_builder_bp = Blueprint("table_builder", __name__)

ALLOWED_TYPES = {
    "VARCHAR(50)","VARCHAR(100)","VARCHAR(255)","VARCHAR(500)",
    "TEXT","LONGTEXT","INT","BIGINT","SMALLINT","TINYINT",
    "DECIMAL(10,2)","DECIMAL(15,2)","FLOAT","DOUBLE",
    "DATE","DATETIME","TIMESTAMP","YEAR","TINYINT(1)",
}

IDENTIFIER_RE = re.compile(r'^[a-z][a-z0-9_]{0,63}$')
SYSTEM_RESERVED = {
    "created_by","created_date","updated_by","updated_date",
    "status_","is_approved","is_active","upload_id"
}

def _vi(name, label="name"):
    if not name or not IDENTIFIER_RE.match(name):
        raise ValueError(f"Invalid {label} '{name}'. Lowercase, start with letter, underscores only.")

def _vt(dtype):
    if dtype not in ALLOWED_TYPES:
        raise ValueError(f"Data type '{dtype}' not allowed.")


@table_builder_bp.route("/api/table_builder/create", methods=["POST"])
@with_db_connection
def create_table(cursor, conn):
    if "username" not in session or session.get("role") != "admin":
        return jsonify({"error": "Admin only"}), 403

    data = request.get_json() or {}

    try:
        table_name  = (data.get("table_name") or "").strip().lower()
        report_name = (data.get("report_name") or "").strip()
        table_type  = data.get("table_type", "transaction")
        department  = (data.get("department") or "").strip()
        columns     = data.get("columns", [])
        is_txn      = table_type == "transaction"

        _vi(table_name, "table name")
        if not report_name: return jsonify({"error": "report_name required"}), 400
        if not columns:     return jsonify({"error": "At least one column required"}), 400

        cursor.execute("""SELECT COUNT(*) AS cnt FROM information_schema.TABLES
            WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s""", (table_name,))
        if cursor.fetchone()["cnt"] > 0:
            return jsonify({"error": f"Table '{table_name}' already exists"}), 409

        col_defs, fk_clauses, meta_rows, pk_cols = [], [], [], []
        seen = set()

        for i, col in enumerate(columns):
            n  = (col.get("name")    or "").strip().lower()
            lb = (col.get("label")   or "").strip()
            t  = (col.get("type")    or "VARCHAR(100)").strip()
            nu = col.get("nullable", "YES")
            df = (col.get("default") or "").strip()
            kt = (col.get("key_type") or "NONE").upper()
            fk = (col.get("fk_ref")  or "").strip()
            ai = col.get("auto_increment", False)

            _vi(n, f"column[{i}].name")
            _vt(t)
            if not lb:  return jsonify({"error": f"Display label missing for '{n}'"}), 400
            if n in SYSTEM_RESERVED: return jsonify({"error": f"'{n}' is reserved by the system."}), 400
            if n in seen: return jsonify({"error": f"Duplicate column: '{n}'"}), 400
            seen.add(n)

            null_sql = "" if nu == "YES" else " NOT NULL"
            def_sql  = f" DEFAULT '{df}'" if df and re.match(r'^[a-zA-Z0-9_\-\. ]+$', df) else ""

            if kt == "PRIMARY":
                extra = " AUTO_INCREMENT" if ai and t in ("INT","BIGINT") else ""
                col_defs.append(f"    `{n}` {t} NOT NULL{extra}{def_sql}")
                pk_cols.append(n)
            elif kt == "FOREIGN":
                if not fk: return jsonify({"error": f"FK reference missing for '{n}'"}), 400
                m = re.match(r'^([a-z][a-z0-9_]*)\(([a-z][a-z0-9_]*)\)$', fk)
                if not m:  return jsonify({"error": f"Invalid FK format for '{n}': use tablename(col)"}), 400
                col_defs.append(f"    `{n}` {t}{null_sql}{def_sql}")
                fk_clauses.append(
                    f"    CONSTRAINT `fk_{table_name}_{n}` "
                    f"FOREIGN KEY (`{n}`) REFERENCES `{m.group(1)}`(`{m.group(2)}`)"
                )
            else:
                col_defs.append(f"    `{n}` {t}{null_sql}{def_sql}")

            # Store key_type in metadata so template generation can exclude PK columns
            meta_rows.append({
                "table_name": table_name,
                "column_name": n,
                "display_label": lb,
                "ordinal": i + 1,
                "key_type": kt
            })

        # Build SQL — no forced id column
        all_defs = list(col_defs)
        if pk_cols:
            all_defs.append("    PRIMARY KEY (" + ", ".join(f"`{c}`" for c in pk_cols) + ")")
        if is_txn:
            all_defs.append("    `upload_id` INT DEFAULT NULL")
        all_defs += [
            "    `created_by`   VARCHAR(100)",
            "    `created_date` DATETIME DEFAULT CURRENT_TIMESTAMP",
            "    `updated_by`   VARCHAR(100)",
            "    `updated_date` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
            "    `status_`      TINYINT  DEFAULT NULL",
            "    `is_approved`  TINYINT DEFAULT NULL" if is_txn else "    `is_active` TINYINT(1) DEFAULT 1",
        ]
        all_defs += fk_clauses

        sql = f"CREATE TABLE IF NOT EXISTS `{table_name}` (\n" + ",\n".join(all_defs) + "\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
        cursor.execute(sql)

        if is_txn:
            try:
                cursor.execute(f"""ALTER TABLE `{table_name}`
                    ADD CONSTRAINT `fk_{table_name}_upload`
                    FOREIGN KEY (`upload_id`) REFERENCES `excel_uploads`(`id`) ON DELETE SET NULL""")
            except: pass

        meta_saved = 0
        for m in meta_rows:
            try:
                cursor.execute("""INSERT INTO tbl_column_metadata
                    (table_name, column_name, display_label, ordinal, key_type)
                    VALUES(%s,%s,%s,%s,%s)
                    ON DUPLICATE KEY UPDATE
                        display_label=VALUES(display_label),
                        ordinal=VALUES(ordinal),
                        key_type=VALUES(key_type)""",
                    (m["table_name"], m["column_name"], m["display_label"], m["ordinal"], m.get("key_type","NONE")))
                meta_saved += 1
            except Exception as meta_err:
                print(f"Meta save error: {meta_err}")

        registry_saved = False
        if is_txn and department:
            try:
                cursor.execute("""INSERT INTO txn_registry(department,report_name,target_table_name)
                    VALUES(%s,%s,%s) ON DUPLICATE KEY UPDATE report_name=VALUES(report_name)""",
                    (department, report_name, table_name))
                registry_saved = True
            except: pass

        conn.commit()
        return jsonify({
            "message": f"Table '{table_name}' created",
            "table_name": table_name,
            "meta_rows": meta_saved,
            "registry_saved": registry_saved
        })

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        conn.rollback()
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


@table_builder_bp.route("/api/table_builder/list_tables")
@with_db_connection
def list_tables(cursor, conn):
    if "username" not in session or session.get("role") != "admin":
        return jsonify({"error":"Admin only"}), 403
    cursor.execute("SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE() ORDER BY TABLE_NAME")
    return jsonify([r["TABLE_NAME"] for r in cursor.fetchall()])


@table_builder_bp.route("/api/table_builder/registry")
@with_db_connection
def get_registry(cursor, conn):
    if "username" not in session or session.get("role") != "admin":
        return jsonify({"error":"Admin only"}), 403
    cursor.execute("SELECT report_id,department,report_name,target_table_name,created_at FROM txn_registry ORDER BY department,report_name")
    rows = cursor.fetchall()
    for r in rows:
        if r.get("created_at"): r["created_at"] = str(r["created_at"])
    return jsonify(rows)


@table_builder_bp.route("/api/table_builder/registry/add", methods=["POST"])
@with_db_connection
def registry_add(cursor, conn):
    if "username" not in session or session.get("role") != "admin":
        return jsonify({"error":"Admin only"}), 403
    d = request.get_json() or {}
    dept  = (d.get("department") or "").strip()
    tbl   = (d.get("target_table_name") or "").strip()
    rname = (d.get("report_name") or "").strip()
    if not dept or not tbl or not rname:
        return jsonify({"error":"All fields required"}), 400
    try:
        cursor.execute(
            "INSERT INTO txn_registry(department,report_name,target_table_name) VALUES(%s,%s,%s)",
            (dept, rname, tbl))
        conn.commit()
        return jsonify({"message":"Added","report_id":cursor.lastrowid})
    except Exception as e:
        conn.rollback()
        return jsonify({"error":str(e)}), 500


@table_builder_bp.route("/api/table_builder/registry/update", methods=["POST"])
@with_db_connection
def registry_update(cursor, conn):
    if "username" not in session or session.get("role") != "admin":
        return jsonify({"error":"Admin only"}), 403
    d = request.get_json() or {}
    rid   = d.get("report_id")
    rname = (d.get("report_name") or "").strip()
    if not rid or not rname:
        return jsonify({"error":"report_id and report_name required"}), 400
    try:
        cursor.execute("UPDATE txn_registry SET report_name=%s WHERE report_id=%s", (rname, rid))
        conn.commit()
        return jsonify({"message":"Updated"})
    except Exception as e:
        conn.rollback()
        return jsonify({"error":str(e)}), 500


@table_builder_bp.route("/api/table_builder/registry/delete", methods=["POST"])
@with_db_connection
def registry_delete(cursor, conn):
    if "username" not in session or session.get("role") != "admin":
        return jsonify({"error":"Admin only"}), 403
    d = request.get_json() or {}
    rid = d.get("report_id")
    if not rid:
        return jsonify({"error":"report_id required"}), 400
    try:
        cursor.execute("DELETE FROM txn_registry WHERE report_id=%s", (rid,))
        conn.commit()
        return jsonify({"message":"Deleted"})
    except Exception as e:
        conn.rollback()
        return jsonify({"error":str(e)}), 500