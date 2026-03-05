# app/utils/report_config.py

"""
Central report configuration.
Matches REAL MySQL schema exactly.
"""

REPORT_CONFIG = {

    # --------------------------------------------------
    # LIVESTOCK CENSUS
    # --------------------------------------------------
    "tbl_livestock_census": {
        "title": "Livestock Census Report", 
        "value_column": "livestock_num",
        "year_column": "year_id",

        "group": {
            "table": "tbl_livestock_div_master",
            "id": "livestock_div_id",
            "label": "livestock_div_desc",
            "join": "c.livestock_div_id = g.livestock_div_id"
        },

        "item": {
            "table": "tbl_livestock_master",
            "id": "livestock_id",
            "label": "livestock_desc",
            "join": "c.livestock_id = i.livestock_id"
        }
    },

    # --------------------------------------------------
    # LIVESTOCK PRODUCTION
    # --------------------------------------------------
    "tbl_livestock_prod": {
        "title": "Livestock Production Report", 
        "value_column": "livestock_prod_num",
        "year_column": "year_id",

        "group": {
            "table": "tbl_livestock_master",
            "id": "livestock_id",
            "label": "livestock_desc",
            "join": "c.livestock_id = g.livestock_id"
        },

        "item": {
            "table": "tbl_livestock_prod_master",
            "id": "livestock_prod_id",
            "label": "livestock_prod_desc",
            "join": "c.livestock_prod_id = i.livestock_prod_id"
        }
    },

    # --------------------------------------------------
    # VETERINARY AID
    # --------------------------------------------------
    "tbl_vet_aid": {
        "title": "Veterinary AID Report",
        "value_column": "vet_aid_num",
        "year_column": "year_id",

        "group": {
            "table": "tbl_vet_aid_master",
            "id": "vet_aid_id",
            "label": "vet_aid_desc",
            "join": "c.vet_aid_id = g.vet_aid_id"
        },

        "item": None
    },

    # --------------------------------------------------
    # VETERINARY INFRASTRUCTURE
    # --------------------------------------------------
    "tbl_vet_infra": {
        "title": "Veterinary Infrastructure Report", 
        "value_column": "vet_infra_num",
        "year_column": "year_id",

        "group": {
            "table": "tbl_vet_infra_cat_master",
            "id": "vet_infra_cat_id",
            "label": "vet_infra_cat_desc",
            "join": "c.vet_infra_cat_id = g.vet_infra_cat_id"
        },

        "item": None
    }
}
