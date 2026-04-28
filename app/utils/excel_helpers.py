"""Excel processing and template generation utilities."""
import io
import pandas as pd
import traceback
from flask import session, request, current_app
from app.utils.database import log_error_db
from app.utils.validators import is_audit_column, is_refno_column
from werkzeug.utils import secure_filename
from app.utils.validators import (
    is_audit_column,
    is_refno_column,
    infer_master_table_from_fk,
    detect_master_id_and_desc,
    resolve_year,
    fk_value_to_id,
)


def load_metadata_for_table(cursor, table_name: str) -> dict:
    """
    Load user-friendly names from tbl_column_metadata.
    Returns mapping: normalized_display_name -> db_column_name
    """
    try:
        cursor.execute("""
            SELECT column_name, display_label
            FROM tbl_column_metadata
            WHERE table_name = %s
        """, (table_name,))
        rows = cursor.fetchall()

        mapping = {}
        for r in rows:
            db_col = r.get("column_name") or r.get("col_name") or r.get("column") or ""
            label  = r.get("display_label") or r.get("displayname") or r.get("label") or ""
            db_col = (db_col or "").strip()
            label  = (label  or "").strip()
            if not db_col or not label:
                continue
            mapping[label.lower()]                   = db_col
            mapping[label.replace(" ", "_").lower()] = db_col
        return mapping
    except Exception as e:
        tb = traceback.format_exc()
        config_obj = current_app.config.get("CONFIG_OBJ")
        log_error_db(session.get("username"), request.path, str(e), tb, config_obj)
        print("❌ ERROR: load_metadata_for_table:", e)
        return {}


EXCEL_REMOVE_COLUMNS = {
    "upload_id",
    "is_approved",
}


def _ensure_key_type_column(cursor) -> None:
    """
    1. Add key_type column to tbl_column_metadata if it doesn't exist.
    2. Backfill key_type = 'PRIMARY' for any column that is an actual
       PRIMARY KEY in its target table, detected via information_schema.
       This handles tables created before key_type tracking was added.
    """
    # ── Step 1: Add column if missing ──
    cursor.execute("""
        SELECT COUNT(*) AS cnt
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME   = 'tbl_column_metadata'
          AND COLUMN_NAME  = 'key_type'
    """)
    col_exists = cursor.fetchone()["cnt"] > 0

    if not col_exists:
        try:
            cursor.execute("""
                ALTER TABLE tbl_column_metadata
                    ADD COLUMN key_type VARCHAR(20) NOT NULL DEFAULT 'NONE'
            """)
            print("✅ Auto-migrated: added key_type to tbl_column_metadata")
        except Exception as e:
            err_str = str(e)
            if "1060" in err_str or "Duplicate column" in err_str:
                print("⚠️  key_type already added concurrently — continuing")
            else:
                raise

    # ── Step 2: Backfill — find every (table_name, column_name) pair in
    #    tbl_column_metadata whose key_type is still 'NONE' but the column
    #    is actually a PRIMARY KEY in MySQL's information_schema. ──
    #
    # This fixes tables built before key_type tracking existed,
    # e.g. the 'Test Id' column that was PK but stored as 'NONE'.
    try:
        cursor.execute("""
            UPDATE tbl_column_metadata AS m
            INNER JOIN information_schema.KEY_COLUMN_USAGE AS k
                ON  k.TABLE_SCHEMA    = DATABASE()
                AND k.TABLE_NAME      = m.table_name
                AND k.COLUMN_NAME     = m.column_name
                AND k.CONSTRAINT_NAME = 'PRIMARY'
            SET m.key_type = 'PRIMARY'
            WHERE (m.key_type IS NULL OR m.key_type = 'NONE')
        """)
        rows_updated = cursor.rowcount
        if rows_updated > 0:
            print(f"✅ Backfilled key_type='PRIMARY' for {rows_updated} metadata row(s)")
    except Exception as e:
        # Non-fatal — log and continue. Template may still include PK cols
        # for old tables, but won't crash.
        print(f"⚠️  key_type backfill warning: {e}")


def generate_excel_template(
    cursor,
    table: str,
    lookup_config: dict,
    column_label: dict
) -> io.BytesIO:
    """
    Generate an Excel template for a transaction table with dropdowns for FKs.
    PRIMARY KEY columns are excluded from the template so users never fill them in.
    Auto-migrates tbl_column_metadata to add + backfill key_type if missing.
    Returns a BytesIO object containing the Excel file.
    """
    try:
        # ── 0. Ensure key_type exists AND is backfilled from real PK info ──
        _ensure_key_type_column(cursor)

        # ── 1. Validate target table exists ──
        cursor.execute("SHOW TABLES LIKE %s", (table,))
        if not cursor.fetchone():
            raise ValueError(f"Table '{table}' not found")

        # ── 2. Get all columns from the target table ──
        cursor.execute(f"SHOW COLUMNS FROM `{table}`")
        cols_info = cursor.fetchall()
        db_cols = [c["Field"] for c in cols_info]

        # ── 3. Get the REAL primary key columns directly from MySQL ──
        # This is the ground truth — works even if metadata is stale.
        cursor.execute("""
            SELECT COLUMN_NAME
            FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA    = DATABASE()
              AND TABLE_NAME      = %s
              AND CONSTRAINT_NAME = 'PRIMARY'
        """, (table,))
        real_pk_columns = {r["COLUMN_NAME"] for r in cursor.fetchall()}

        # ── 4. Fetch metadata (display labels + key_type) ──
        cursor.execute("""
            SELECT column_name,
                   display_label,
                   COALESCE(key_type, 'NONE') AS key_type
            FROM tbl_column_metadata
            WHERE table_name = %s
        """, (table,))
        meta_rows = cursor.fetchall()

        metadata   = {}    # col_name → display_label
        pk_columns = set() # col names excluded from template

        for r in meta_rows:
            col_key  = (r.get("column_name") or r.get("col_name") or
                        r.get("column")      or r.get("name") or "").strip()
            label    = (r.get("display_label") or r.get("displayname") or
                        r.get("label") or "").strip()
            key_type = (r.get("key_type") or "NONE").upper().strip()

            if col_key:
                metadata[col_key] = label
                if key_type == "PRIMARY":
                    pk_columns.add(col_key)

        # Merge with real PK info — catches any column the metadata missed
        pk_columns |= real_pk_columns

        # ── 5. Build fillable column list ──
        fillable = []
        for c in db_cols:
            normalized = c.replace("_", "").lower()

            if normalized in {"uploadid", "isapproved", "approved"}:
                continue
            if is_audit_column(c):
                continue
            if is_refno_column(c):
                continue
            if c in pk_columns:   # ← PRIMARY KEY hidden from template
                continue

            fillable.append(c)

        if not fillable:
            raise ValueError("No editable columns found")

        # ── 6. Map DB column names → Excel header labels ──
        headers = []
        for col in fillable:
            label = metadata.get(
                col,
                column_label.get(col, col.replace("_", " ").title())
            )
            headers.append(label)

        # ── 7. Build FK dropdown data ──
        dropdown_sources = {}

        for col in fillable:
            is_fk = col.endswith("_id") or col in lookup_config
            if not is_fk:
                continue

            if col in lookup_config:
                master_table, desc_col, id_col = lookup_config[col]
            else:
                master_table = infer_master_table_from_fk(col)
                id_col, desc_col = detect_master_id_and_desc(cursor, master_table)

            if not master_table or not id_col or not desc_col:
                continue

            cursor.execute(
                f"SELECT `{desc_col}` AS name FROM `{master_table}` ORDER BY name"
            )
            rows = cursor.fetchall()
            dropdown_sources[col] = [
                r.get("name") if isinstance(r, dict) else r[0]
                for r in rows
            ]

        # ── 8. Build Excel workbook ──
        output = io.BytesIO()
        df = pd.DataFrame(columns=headers)

        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df.to_excel(writer, sheet_name="Template", index=False)

            workbook = writer.book
            ws       = writer.sheets["Template"]

            header_fmt = workbook.add_format({
                "bold":       True,
                "bg_color":   "#1e5a8e",
                "font_color": "#ffffff",
                "border":     1,
                "align":      "center",
                "valign":     "vcenter",
            })
            for col_idx, hdr in enumerate(headers):
                ws.write(0, col_idx, hdr, header_fmt)
                ws.set_column(col_idx, col_idx, max(18, len(hdr) + 4))

            if dropdown_sources:
                list_ws = workbook.add_worksheet("_lists")
                list_ws.hide()

                named_ranges = {}
                cur_row = 0

                for col, items in dropdown_sources.items():
                    range_name = f"list_{col}"
                    for i, val in enumerate(items):
                        list_ws.write(cur_row + i, 0, val)

                    first_row = cur_row + 1
                    last_row  = cur_row + len(items)
                    workbook.define_name(
                        range_name,
                        f"'_lists'!$A${first_row}:$A${last_row}"
                    )
                    named_ranges[col] = range_name
                    cur_row += len(items) + 2

                for idx, col in enumerate(fillable):
                    if col in named_ranges:
                        ws.data_validation(
                            1, idx, 5000, idx,
                            {"validate": "list", "source": f"={named_ranges[col]}"}
                        )

        output.seek(0)
        return output

    except Exception as e:
        tb = traceback.format_exc()
        config_obj = current_app.config.get("CONFIG_OBJ")
        log_error_db(session.get("username"), request.path, str(e), tb, config_obj)
        print("🔥 ERROR (template):", e)
        print(tb)
        raise