"""Application constants and configuration mappings."""

# Excel human labels
COLUMN_LABEL = {
    "year_id": "Year",
    "region_id": "Region",
    # Police – accident details example
    "accident_id": "Accident Type",
    "accident_num": "Accident Count",
    # Civil police
    "civil_pol_id": "Civil Pol Id",
    # Unit
    "unit_id": "Unit",
}

# FK → (master_table, desc_col, id_col)
LOOKUP_CONFIG = {
    # Common FK fields
    "year_id": ("tbl_year_master", "year_desc", "year_id"),
    "region_id": ("tbl_region_master", "region_desc", "region_id"),
    # Livestock module
    "livestock_id": ("tbl_livestock_master", "livestock_desc", "livestock_id"),
    "livestock_div_id": ("tbl_livestock_div_master", "livestock_div_desc", "livestock_div_id"),
    "livestock_prod_id": ("tbl_livestock_prod_master", "livestock_prod_desc", "livestock_prod_id"),
    # Veterinary
    "vet_aid_id": ("tbl_vet_aid_master", "vet_aid_desc", "vet_aid_id"),
    "vet_infra_cat_id": ("tbl_vet_infra_cat_master", "vet_infra_cat_desc", "vet_infra_cat_id"),
    # Police/crime masters
    "accident_id": ("tbl_accident_master", "accident_desc", "accident_id"),
    "cog_crime_id": ("tbl_cog_crime_master", "cog_crime_desc", "cog_crime_id"),
    "crime_law_id": ("tbl_crime_law_master", "crime_law_desc", "crime_law_id"),
    "prop_stolen_id": ("tbl_property_stolen_master", "prop_stolen_desc", "prop_stolen_id"),
    "offence_id": ("tbl_offence_master", "offence_desc", "offence_id"),
    "offence_head_id": ("tbl_offence_head_master", "offence_head_desc", "offence_head_id"),
    "conviction_id": ("tbl_conviction_master", "conviction_desc", "conviction_id"),
    "civil_pol_id": ("tbl_civil_police_master", "civil_pol_desc", "civil_pol_id"),
    "police_stn_id": ("tbl_police_station_master", "police_stn_desc", "police_stn_id"),
    "police_post_id": ("tbl_police_post_master", "police_post_desc", "police_post_id"),
    "case_type_id": ("tbl_case_type_master", "case_type_desc", "case_type_id"),
    "case_stat_id": ("tbl_case_status_master", "case_stat_desc", "case_stat_id"),
    "currency_denom_id": ("tbl_currency_denom_master", "currency_denom_desc", "currency_denom_id"),
    "unit_id": ("tbl_unit_master", "unit_measure", "unit_id"),
    "ely_conn_type_id": ("tbl_ely_conn_type_master", "ely_conn_type_desc", "ely_conn_type_id"),
    
      "wsch_det_id": (
        "tbl_welfare_scheme_det_master",
        "wsch_det_desc",
        "wsch_det_id"),
}

