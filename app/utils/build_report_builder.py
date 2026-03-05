# app/utils/report_builder.py

from app.constants import LOOKUP_CONFIG

def build_report_query(table_name, filters=None):
    """
    Build SELECT query dynamically with FK → name joins
    """

    filters = filters or {}

    select_cols = []
    joins = []
    where = []

    for col, cfg in LOOKUP_CONFIG.items():
        if cfg:
            master, desc_col, id_col = cfg
            alias = col.replace("_id", "")
            joins.append(
                f"LEFT JOIN {master} {alias} ON t.{col} = {alias}.{id_col}"
            )
            select_cols.append(f"{alias}.{desc_col} AS {alias}")
    
    select_cols.append("t.*")

    if filters.get("year"):
        where.append("t.year_id = %(year)s")
    if filters.get("region"):
        where.append("t.region_id = %(region)s")
    if filters.get("unit"):
        where.append("t.unit_id = %(unit)s")

    sql = f"""
        SELECT {', '.join(select_cols)}
        FROM {table_name} t
        {' '.join(joins)}
        {'WHERE ' + ' AND '.join(where) if where else ''}
        ORDER BY t.year_id, t.region_id
    """

    return sql
