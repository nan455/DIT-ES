"""Validation and data conversion utilities."""
import re
import datetime
from typing import Optional, Tuple


def sanitize_name(name: str) -> str:
    """Sanitize a name to be safe for database/URL use."""
    return re.sub(r"[^a-zA-Z0-9_]", "_", name).lower()


def is_audit_column(col: str) -> bool:
    """Check if a column is an audit column."""
    return col in {
        "created_by",
        "created_date",
        "updated_by",
        "updated_date",
        "status_",
        "uploaded_by",
        "created_at",
        "updated_at",
    }


def is_refno_column(col: str) -> bool:
    """Check if a column is a reference number column."""
    cl = col.lower()
    return "refno" in cl or cl.endswith("_refno") or cl.endswith("_ref_no")


def infer_master_table_from_fk(col_name: str) -> Optional[str]:
    """
    Automatically infer master table name from FK column.
    year_id is special; others: crop_id -> tbl_crop_master etc.
    """
    c = col_name.lower()
    if c == "year_id":
        return "tbl_year_master"
    if not c.endswith("_id"):
        return None
    prefix = c[:-3]
    return f"tbl_{prefix}_master"


def detect_master_id_and_desc(cursor, master_table: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Auto-detect id + description columns from master table.
    Returns (id_col, desc_col) tuple.
    """
    try:
        cursor.execute("SHOW TABLES LIKE %s", (master_table,))
        if not cursor.fetchone():
            return None, None

        cursor.execute(f"SHOW COLUMNS FROM `{master_table}`")
        cols_info = cursor.fetchall()
        cols = [c["Field"] for c in cols_info]
        if not cols:
            return None, None

        id_col = None
        desc_col = None

        for c in cols:
            if c.lower().endswith("_id"):
                id_col = c
                break

        for c in cols:
            low = c.lower()
            if "desc" in low or "name" in low or "title" in low:
                desc_col = c
                break

        if not id_col:
            id_col = cols[0]
        if not desc_col:
            for c in cols:
                if c != id_col:
                    desc_col = c
                    break

        return id_col, desc_col
    except Exception:
        return None, None


def convert_dropdown_value_to_id(val) -> Optional[int]:
    """
    From Excel / UI dropdown: "123 - Text" -> 123
    Or numeric string -> int.
    Otherwise returns original string.
    """
    if val is None:
        return None
    s = str(val).strip()
    if s == "":
        return None
    m = re.match(r"^(\d+)\s*[-:]\s*(.+)$", s)
    if m:
        return int(m.group(1))
    if s.isdigit():
        return int(s)
    return s


def resolve_year(cursor, value) -> Optional[int]:
    """
    Accepts: "2025", "2025-26", "2025-2026", or exact year_desc.
    Returns year_id or raises ValueError.
    """
    if value is None:
        return None
    raw = str(value).strip()
    if raw == "":
        return None

    if re.match(r"^\d{4}-\d{4}$", raw):
        raw = raw[:4] + "-" + raw[5:7]

    if re.fullmatch(r"\d{4}", raw):
        y = int(raw)
        cursor.execute(
            """
            SELECT year_id FROM tbl_year_master
            WHERE YEAR(start_date) <= %s AND YEAR(end_date) >= %s
            ORDER BY start_date ASC LIMIT 1
            """,
            (y, y),
        )
        r = cursor.fetchone()
        if r:
            return r["year_id"]
        raise ValueError(f"Year '{raw}' not found in tbl_year_master ranges.")

    cursor.execute(
        "SELECT year_id FROM tbl_year_master WHERE year_desc=%s LIMIT 1",
        (raw,),
    )
    r = cursor.fetchone()
    if r:
        return r["year_id"]

    parsed = convert_dropdown_value_to_id(raw)
    if isinstance(parsed, int):
        return parsed

    raise ValueError(f"Invalid year value: {value}")


def fk_value_to_id(cursor, col: str, value, lookup_config: dict) -> Optional[int]:
    """
    Convert text -> FK ID.
    - "3 - Text" -> 3
    - "3" -> 3
    - "Some name" -> lookup in master table desc column
    """
    
    if value is None or str(value).strip() == "":
        return None

    s = str(value).strip()

    # "123 - Name"
    m = re.match(r"^(\d+)\s*[-:]\s*(.+)$", s)
    if m:
        return int(m.group(1))

    # numeric
    if s.isdigit():
        return int(s)

    # master mapping
    if col in lookup_config:
        master_table, desc_col, id_col = lookup_config[col]
    else:
        master_table = infer_master_table_from_fk(col)
        if not master_table:
            raise ValueError(f"No master table detected for column {col}")
        id_col, desc_col = detect_master_id_and_desc(cursor, master_table)
        if not id_col or not desc_col:
            raise ValueError(f"Cannot detect ID/DESC for {master_table}")

    sql = (
        f"SELECT `{id_col}` AS id FROM `{master_table}` "
        f"WHERE LOWER(`{desc_col}`)=LOWER(%s) LIMIT 1"
    )
    cursor.execute(sql, (s,))
    r = cursor.fetchone()
    if r:
        return r["id"]

    raise ValueError(f"{col}: value '{value}' not found in {master_table}.{desc_col}")

