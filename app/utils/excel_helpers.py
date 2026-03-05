"""Excel processing and template generation utilities."""
import io
import pandas as pd
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
    import traceback
    from flask import session, request
    from app.utils.database import log_error_db
    from flask import current_app
    
    try:
        cursor.execute("""
            SELECT column_name, display_label
            FROM tbl_column_metadata
            WHERE table_name = %s
        """, (table_name,))
        rows = cursor.fetchall()

        mapping = {}
        for r in rows:
            # r is dict like {'column_name': 'vet_aid_id', 'display_label': 'Veterinary Aid Type'}
            db_col = r.get("column_name") or r.get("col_name") or r.get("column") or ""
            label = r.get("display_label") or r.get("displayname") or r.get("label") or ""
            db_col = (db_col or "").strip()
            label = (label or "").strip()
            if not db_col or not label:
                continue
            key1 = label.lower()
            key2 = label.replace(" ", "_").lower()
            mapping[key1] = db_col
            mapping[key2] = db_col
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

def generate_excel_template(
    cursor,
    table: str,
    lookup_config: dict,
    column_label: dict
) -> io.BytesIO:
    """
    Generate an Excel template for a transaction table with dropdowns for FKs.
    Returns a BytesIO object containing the Excel file.
    """
    import traceback
    from flask import session, request, current_app
    from app.utils.database import log_error_db
    from app.utils.validators import is_audit_column, is_refno_column
    
    try:
        # Validate table exists
        cursor.execute("SHOW TABLES LIKE %s", (table,))
        if not cursor.fetchone():
            raise ValueError(f"Table '{table}' not found")

        # Get table columns
        cursor.execute(f"SHOW COLUMNS FROM `{table}`")
        cols_info = cursor.fetchall()
        db_cols = [c["Field"] for c in cols_info]

        # Fetch metadata labels from tbl_column_metadata
        cursor.execute("""
            SELECT column_name, display_label
            FROM tbl_column_metadata
            WHERE table_name=%s
        """, (table,))
        meta_rows = cursor.fetchall()

        # meta_rows may return keys column_name/display_label depending on how table is set up
        # unify keys defensively
        metadata = {}
        for r in meta_rows:
            # r may be dict with keys exactly 'column_name' and 'display_label'
            # or might have different capitalizations — handle gracefully
            try:
                col_key = r.get("column_name") or r.get("col_name") or r.get("column") or r.get("name")
                label = r.get("display_label") or r.get("displayname") or r.get("label") or ""
            except Exception:
                col_key = None
                label = ""
            if col_key:
                metadata[col_key] = label

        # Determine fillable columns (skip PK, audit fields)
        fillable = []
        for c in db_cols:
            normalized = c.replace("_", "").lower()  # 🔥 KEY LINE

            # remove upload_id, isApproved, approved
            if normalized in {"uploadid", "isapproved", "approved"}:
               continue
            if is_audit_column(c):
               continue
            if is_refno_column(c):
               continue
            fillable.append(c)
        if not fillable:
            raise ValueError("No editable columns found")

        # Excel header names using metadata where present
        headers = []
        for col in fillable:
            label = metadata.get(col, column_label.get(col, col.replace("_", " ").title()))
            headers.append(label)

        # Prepare dropdown lists for foreign keys
        dropdown_sources = {}   # col → [name1, name2, ...]

        for col in fillable:
            is_fk = col.endswith("_id") or col in lookup_config

            if not is_fk:
                continue

            # Determine master table
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
            # rows likely each a dict with 'name'
            dropdown_sources[col] = [r.get("name") if isinstance(r, dict) else r[0] for r in rows]

        # Create Excel file with header + FK dropdowns
        output = io.BytesIO()
        df = pd.DataFrame(columns=headers)

        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df.to_excel(writer, sheet_name="Template", index=False)

            workbook = writer.book
            ws = writer.sheets["Template"]

            # If there are dropdowns, create hidden list sheet
            if dropdown_sources:
                list_ws = workbook.add_worksheet("_lists")
                list_ws.hide()

                named_ranges = {}
                cur_row = 0

                for col, items in dropdown_sources.items():
                    range_name = f"list_{col}"

                    # Write each dropdown item into the hidden sheet
                    for i, val in enumerate(items):
                        list_ws.write(cur_row + i, 0, val)

                    first_row = cur_row + 1
                    last_row = cur_row + len(items)
                    ref = f"'_lists'!$A${first_row}:$A${last_row}"

                    workbook.define_name(range_name, ref)
                    named_ranges[col] = range_name

                    cur_row += len(items) + 2

                # Apply dropdown validation to each FK column
                for idx, col in enumerate(fillable):
                    if col in named_ranges:
                        ws.data_validation(
                            1, idx, 5000, idx,
                            {
                                "validate": "list",
                                "source": f"={named_ranges[col]}"
                            }
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

