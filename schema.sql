-- ============================================================================
-- DATABASE SCHEMA FOR ESP (Economics and Statistics Portal)
-- Directorate of Economics and Statistics, Government of Puducherry
-- ============================================================================
-- This schema creates all necessary tables for the application
-- Run this script to initialize a fresh database
-- ============================================================================

-- Create database
CREATE DATABASE IF NOT EXISTS crud;
USE crud;

-- ============================================================================
-- SECTION 1: CORE SYSTEM TABLES
-- ============================================================================

-- Users table for authentication and authorization
DROP TABLE IF EXISTS users;
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    department VARCHAR(100),
    role ENUM('admin', 'user') DEFAULT 'user',
    created_by VARCHAR(100),
    permissions_json TEXT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Transaction registry - defines available reports/registers by department
DROP TABLE IF EXISTS txn_registry;
CREATE TABLE txn_registry (
    report_id INT AUTO_INCREMENT PRIMARY KEY,
    department VARCHAR(100) NOT NULL,
    report_name VARCHAR(200) NOT NULL,
    target_table_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_department (department)
);

-- Excel uploads tracking
DROP TABLE IF EXISTS excel_uploads;
CREATE TABLE excel_uploads (
    id INT AUTO_INCREMENT PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    table_name VARCHAR(100) NOT NULL,
    uploaded_by VARCHAR(100),
    department VARCHAR(100),
    uploaded_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_department (department),
    INDEX idx_table_name (table_name)
);

-- Excel templates management
DROP TABLE IF EXISTS excel_templates;
CREATE TABLE excel_templates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    department VARCHAR(100),
    uploaded_by VARCHAR(100),
    uploaded_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Column metadata for user-friendly display labels
DROP TABLE IF EXISTS tbl_column_metadata;
CREATE TABLE tbl_column_metadata (
    table_name VARCHAR(100) NOT NULL,
    column_name VARCHAR(100) NOT NULL,
    display_label VARCHAR(200) NOT NULL,
    PRIMARY KEY (table_name, column_name),
    INDEX idx_table_name (table_name)
);

-- Error logs for debugging and monitoring
DROP TABLE IF EXISTS error_logs;
CREATE TABLE error_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(150),
    endpoint VARCHAR(255),
    error_message TEXT,
    traceback LONGTEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_created_at (created_at)
);

-- ============================================================================
-- SECTION 2: MASTER DATA TABLES (Common Reference Data)
-- ============================================================================

-- Year master - financial/academic years
DROP TABLE IF EXISTS tbl_year_master;
CREATE TABLE tbl_year_master (
    year_id INT PRIMARY KEY CHECK(year_id BETWEEN 1 AND 999),
    year_desc VARCHAR(50) NOT NULL,
    start_date DATETIME NOT NULL,
    end_date DATETIME NOT NULL,
    created_by VARCHAR(50),
    created_date DATETIME,
    updated_by VARCHAR(50),
    updated_date DATETIME,
    status_ BOOLEAN DEFAULT 1
);

-- Region master - Puducherry regions
DROP TABLE IF EXISTS tbl_region_master;
CREATE TABLE tbl_region_master (
    region_id INT PRIMARY KEY CHECK(region_id BETWEEN 1 AND 999),
    region_desc VARCHAR(100) NOT NULL,
    created_by VARCHAR(50),
    created_date DATETIME,
    updated_by VARCHAR(50),
    updated_date DATETIME,
    status_ BOOLEAN DEFAULT 1
);

-- Unit master - measurement units
DROP TABLE IF EXISTS tbl_unit_master;
CREATE TABLE tbl_unit_master (
    unit_id INT PRIMARY KEY CHECK(unit_id BETWEEN 1 AND 999),
    unit_measure VARCHAR(100) NOT NULL,
    created_by VARCHAR(50),
    created_date DATETIME,
    updated_by VARCHAR(50),
    updated_date DATETIME,
    status_ BOOLEAN DEFAULT 1
);

-- Month master
DROP TABLE IF EXISTS tbl_month_master;
CREATE TABLE tbl_month_master (
    month_id INT PRIMARY KEY CHECK(month_id BETWEEN 1 AND 99),
    month_desc VARCHAR(100) NOT NULL,
    created_by VARCHAR(50),
    created_date DATETIME,
    updated_by VARCHAR(50),
    updated_date DATETIME,
    status_ BOOLEAN DEFAULT 1
);

-- ============================================================================
-- SECTION 3: POLICE DEPARTMENT MASTER TABLES
-- ============================================================================

-- Accident master
DROP TABLE IF EXISTS tbl_accident_master;
CREATE TABLE tbl_accident_master (
    accident_id INT PRIMARY KEY CHECK(accident_id BETWEEN 0 AND 99),
    accident_desc VARCHAR(200) NOT NULL,
    created_by VARCHAR(50),
    created_date DATETIME,
    updated_by VARCHAR(50),
    updated_date DATETIME,
    status_ BOOLEAN DEFAULT 1
);

-- Cognizable crime master
DROP TABLE IF EXISTS tbl_cog_crime_master;
CREATE TABLE tbl_cog_crime_master (
    cog_crime_id INT PRIMARY KEY CHECK(cog_crime_id BETWEEN 0 AND 99),
    cog_crime_desc VARCHAR(200) NOT NULL,
    created_by VARCHAR(50),
    created_date DATETIME,
    updated_by VARCHAR(50),
    updated_date DATETIME,
    status_ BOOLEAN DEFAULT 1
);

-- Crime law master
DROP TABLE IF EXISTS tbl_crime_law_master;
CREATE TABLE tbl_crime_law_master (
    crime_law_id INT PRIMARY KEY CHECK(crime_law_id BETWEEN 0 AND 99),
    crime_law_desc VARCHAR(200) NOT NULL,
    created_by VARCHAR(50),
    created_date DATETIME,
    updated_by VARCHAR(50),
    updated_date DATETIME,
    status_ BOOLEAN DEFAULT 1
);

-- Property stolen master
DROP TABLE IF EXISTS tbl_property_stolen_master;
CREATE TABLE tbl_property_stolen_master (
    prop_stolen_id INT PRIMARY KEY CHECK(prop_stolen_id BETWEEN 0 AND 99),
    prop_stolen_desc VARCHAR(200) NOT NULL,
    created_by VARCHAR(50),
    created_date DATETIME,
    updated_by VARCHAR(50),
    updated_date DATETIME,
    status_ BOOLEAN DEFAULT 1
);

-- Offence master
DROP TABLE IF EXISTS tbl_offence_master;
CREATE TABLE tbl_offence_master (
    offence_id INT PRIMARY KEY CHECK(offence_id BETWEEN 0 AND 999),
    offence_desc VARCHAR(200) NOT NULL,
    created_by VARCHAR(50),
    created_date DATETIME,
    updated_by VARCHAR(50),
    updated_date DATETIME,
    status_ BOOLEAN DEFAULT 1
);

-- Offence head master
DROP TABLE IF EXISTS tbl_offence_head_master;
CREATE TABLE tbl_offence_head_master (
    offence_head_id INT PRIMARY KEY CHECK(offence_head_id BETWEEN 0 AND 99),
    offence_head_desc VARCHAR(100) NOT NULL,
    created_by VARCHAR(50),
    created_date DATETIME,
    updated_by VARCHAR(50),
    updated_date DATETIME,
    status_ BOOLEAN DEFAULT 1
);

-- Conviction master
DROP TABLE IF EXISTS tbl_conviction_master;
CREATE TABLE tbl_conviction_master (
    conviction_id INT PRIMARY KEY CHECK(conviction_id BETWEEN 0 AND 99),
    conviction_desc VARCHAR(200) NOT NULL,
    created_by VARCHAR(50),
    created_date DATETIME,
    updated_by VARCHAR(50),
    updated_date DATETIME,
    status_ BOOLEAN DEFAULT 1
);

-- Police station master
DROP TABLE IF EXISTS tbl_police_station_master;
CREATE TABLE tbl_police_station_master (
    police_stn_id INT PRIMARY KEY CHECK(police_stn_id BETWEEN 0 AND 99),
    police_stn_desc VARCHAR(200) NOT NULL,
    region_id INT,
    created_by VARCHAR(50),
    created_date DATETIME,
    updated_by VARCHAR(50),
    updated_date DATETIME,
    status_ BOOLEAN DEFAULT 1,
    FOREIGN KEY (region_id) REFERENCES tbl_region_master(region_id)
);

-- Civil police master
DROP TABLE IF EXISTS tbl_civil_police_master;
CREATE TABLE tbl_civil_police_master (
    civil_pol_id INT PRIMARY KEY CHECK(civil_pol_id BETWEEN 0 AND 99),
    civil_pol_desc VARCHAR(200) NOT NULL,
    created_by VARCHAR(50),
    created_date DATETIME,
    updated_by VARCHAR(50),
    updated_date DATETIME,
    status_ BOOLEAN DEFAULT 1
);

-- Police post master
DROP TABLE IF EXISTS tbl_police_post_master;
CREATE TABLE tbl_police_post_master (
    police_post_id INT PRIMARY KEY CHECK(police_post_id BETWEEN 0 AND 99),
    police_post_desc VARCHAR(200) NOT NULL,
    created_by VARCHAR(50),
    created_date DATETIME,
    updated_by VARCHAR(50),
    updated_date DATETIME,
    status_ BOOLEAN DEFAULT 1
);

-- Case type master
DROP TABLE IF EXISTS tbl_case_type_master;
CREATE TABLE tbl_case_type_master (
    case_type_id INT PRIMARY KEY CHECK(case_type_id BETWEEN 0 AND 99),
    case_type_desc VARCHAR(100) NOT NULL,
    created_by VARCHAR(50),
    created_date DATETIME,
    updated_by VARCHAR(50),
    updated_date DATETIME,
    status_ BOOLEAN DEFAULT 1
);

-- Case status master
DROP TABLE IF EXISTS tbl_case_status_master;
CREATE TABLE tbl_case_status_master (
    case_stat_id INT PRIMARY KEY CHECK(case_stat_id BETWEEN 0 AND 99),
    case_stat_desc VARCHAR(200) NOT NULL,
    created_by VARCHAR(50),
    created_date DATETIME,
    updated_by VARCHAR(50),
    updated_date DATETIME,
    status_ BOOLEAN DEFAULT 1
);

-- Currency denomination master
DROP TABLE IF EXISTS tbl_currency_denom_master;
CREATE TABLE tbl_currency_denom_master (
    currency_denom_id INT PRIMARY KEY CHECK(currency_denom_id BETWEEN 0 AND 99),
    currency_denom_desc VARCHAR(100) NOT NULL,
    created_by VARCHAR(50),
    created_date DATETIME,
    updated_by VARCHAR(50),
    updated_date DATETIME,
    status_ BOOLEAN DEFAULT 1
);

-- ============================================================================
-- SECTION 4: POLICE DEPARTMENT TRANSACTION TABLES
-- ============================================================================

-- Accident details
DROP TABLE IF EXISTS tbl_accident_details;
CREATE TABLE tbl_accident_details (
    accident_det_refno INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    accident_id INT NOT NULL,
    year_id INT NOT NULL,
    region_id INT NOT NULL,
    accident_num INT CHECK(accident_num BETWEEN 1 AND 999999999),
    created_by VARCHAR(50),
    created_date DATETIME,
    updated_by VARCHAR(50),
    updated_date DATETIME,
    status_ BOOLEAN DEFAULT 1,
    FOREIGN KEY (accident_id) REFERENCES tbl_accident_master(accident_id),
    FOREIGN KEY (year_id) REFERENCES tbl_year_master(year_id),
    FOREIGN KEY (region_id) REFERENCES tbl_region_master(region_id),
    INDEX idx_year_region (year_id, region_id)
);

-- Cognizable crime
DROP TABLE IF EXISTS tbl_cogniz_crime;
CREATE TABLE tbl_cogniz_crime (
    cogniz_crime_refno INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    cog_crime_id INT NOT NULL,
    year_id INT NOT NULL,
    region_id INT NOT NULL,
    cog_crime_num INT CHECK(cog_crime_num BETWEEN 1 AND 999999999),
    created_by VARCHAR(50),
    created_date DATETIME,
    updated_by VARCHAR(50),
    updated_date DATETIME,
    status_ BOOLEAN DEFAULT 1,
    FOREIGN KEY (cog_crime_id) REFERENCES tbl_cog_crime_master(cog_crime_id),
    FOREIGN KEY (year_id) REFERENCES tbl_year_master(year_id),
    FOREIGN KEY (region_id) REFERENCES tbl_region_master(region_id),
    INDEX idx_year_region (year_id, region_id)
);

-- Crime law details
DROP TABLE IF EXISTS tbl_crime_law_details;
CREATE TABLE tbl_crime_law_details (
    crime_law_det_refno INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    crime_law_id INT NOT NULL,
    year_id INT NOT NULL,
    region_id INT NOT NULL,
    crime_det_num INT CHECK(crime_det_num BETWEEN 1 AND 999999999),
    created_by VARCHAR(50),
    created_date DATETIME,
    updated_by VARCHAR(50),
    updated_date DATETIME,
    status_ BOOLEAN DEFAULT 1,
    FOREIGN KEY (crime_law_id) REFERENCES tbl_crime_law_master(crime_law_id),
    FOREIGN KEY (year_id) REFERENCES tbl_year_master(year_id),
    FOREIGN KEY (region_id) REFERENCES tbl_region_master(region_id),
    INDEX idx_year_region (year_id, region_id)
);

-- Stolen property recovery details
DROP TABLE IF EXISTS tbl_stole_recov_det;
CREATE TABLE tbl_stole_recov_det (
    stole_recov_refno INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    prop_stolen_id INT NOT NULL,
    year_id INT NOT NULL,
    region_id INT NOT NULL,
    stole_recov_num INT CHECK(stole_recov_num BETWEEN 1 AND 999999999),
    created_by VARCHAR(50),
    created_date DATETIME,
    updated_by VARCHAR(50),
    updated_date DATETIME,
    status_ BOOLEAN DEFAULT 1,
    FOREIGN KEY (prop_stolen_id) REFERENCES tbl_property_stolen_master(prop_stolen_id),
    FOREIGN KEY (year_id) REFERENCES tbl_year_master(year_id),
    FOREIGN KEY (region_id) REFERENCES tbl_region_master(region_id),
    INDEX idx_year_region (year_id, region_id)
);

-- Civil police details
DROP TABLE IF EXISTS tbl_civil_pol_det;
CREATE TABLE tbl_civil_pol_det (
    civil_pol_det_refno INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    civil_pol_id INT NOT NULL,
    year_id INT NOT NULL,
    region_id INT NOT NULL,
    unit_id INT,
    civil_pol_value DECIMAL(15,2),
    created_by VARCHAR(50),
    created_date DATETIME,
    updated_by VARCHAR(50),
    updated_date DATETIME,
    status_ BOOLEAN DEFAULT 1,
    FOREIGN KEY (civil_pol_id) REFERENCES tbl_civil_police_master(civil_pol_id),
    FOREIGN KEY (year_id) REFERENCES tbl_year_master(year_id),
    FOREIGN KEY (region_id) REFERENCES tbl_region_master(region_id),
    FOREIGN KEY (unit_id) REFERENCES tbl_unit_master(unit_id),
    INDEX idx_year_region (year_id, region_id)
);

-- Police working strength details
DROP TABLE IF EXISTS tbl_pol_work_strgth_det;
CREATE TABLE tbl_pol_work_strgth_det (
    pol_workstgth_refno INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    police_stn_id INT NOT NULL,
    police_post_id INT NOT NULL,
    year_id INT NOT NULL,
    pol_workstgth_num INT CHECK(pol_workstgth_num BETWEEN 1 AND 999999999),
    created_by VARCHAR(50),
    created_date DATETIME,
    updated_by VARCHAR(50),
    updated_date DATETIME,
    status_ BOOLEAN DEFAULT 1,
    FOREIGN KEY (police_stn_id) REFERENCES tbl_police_station_master(police_stn_id),
    FOREIGN KEY (police_post_id) REFERENCES tbl_police_post_master(police_post_id),
    FOREIGN KEY (year_id) REFERENCES tbl_year_master(year_id),
    INDEX idx_year (year_id)
);

-- Riot hurt details
DROP TABLE IF EXISTS tbl_riot_hurt_det;
CREATE TABLE tbl_riot_hurt_det (
    riot_hurt_refno INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    police_stn_id INT NOT NULL,
    case_type_id INT NOT NULL,
    year_id INT NOT NULL,
    region_id INT NOT NULL,
    riot_hurt_num INT CHECK(riot_hurt_num BETWEEN 1 AND 999999999),
    created_by VARCHAR(50),
    created_date DATETIME,
    updated_by VARCHAR(50),
    updated_date DATETIME,
    status_ BOOLEAN DEFAULT 1,
    FOREIGN KEY (police_stn_id) REFERENCES tbl_police_station_master(police_stn_id),
    FOREIGN KEY (case_type_id) REFERENCES tbl_case_type_master(case_type_id),
    FOREIGN KEY (year_id) REFERENCES tbl_year_master(year_id),
    FOREIGN KEY (region_id) REFERENCES tbl_region_master(region_id),
    INDEX idx_year_region (year_id, region_id)
);

-- Currency crime details
DROP TABLE IF EXISTS tbl_currency_crime_det;
CREATE TABLE tbl_currency_crime_det (
    curr_crime_refno INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    police_stn_id INT NOT NULL,
    currency_denom_id INT NOT NULL,
    year_id INT NOT NULL,
    region_id INT NOT NULL,
    curr_crime_num INT CHECK(curr_crime_num BETWEEN 1 AND 999999999),
    created_by VARCHAR(50),
    created_date DATETIME,
    updated_by VARCHAR(50),
    updated_date DATETIME,
    status_ BOOLEAN DEFAULT 1,
    FOREIGN KEY (police_stn_id) REFERENCES tbl_police_station_master(police_stn_id),
    FOREIGN KEY (currency_denom_id) REFERENCES tbl_currency_denom_master(currency_denom_id),
    FOREIGN KEY (year_id) REFERENCES tbl_year_master(year_id),
    FOREIGN KEY (region_id) REFERENCES tbl_region_master(region_id),
    INDEX idx_year_region (year_id, region_id)
);

-- Crime statistics details
DROP TABLE IF EXISTS tbl_crime_stat_det;
CREATE TABLE tbl_crime_stat_det (
    crime_stat_refno INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    offence_head_id INT NOT NULL,
    offence_id INT NOT NULL,
    year_id INT NOT NULL,
    region_id INT NOT NULL,
    crime_stat_num INT CHECK(crime_stat_num BETWEEN 1 AND 999999999),
    created_by VARCHAR(50),
    created_date DATETIME,
    updated_by VARCHAR(50),
    updated_date DATETIME,
    status_ BOOLEAN DEFAULT 1,
    FOREIGN KEY (offence_head_id) REFERENCES tbl_offence_head_master(offence_head_id),
    FOREIGN KEY (offence_id) REFERENCES tbl_offence_master(offence_id),
    FOREIGN KEY (year_id) REFERENCES tbl_year_master(year_id),
    FOREIGN KEY (region_id) REFERENCES tbl_region_master(region_id),
    INDEX idx_year_region (year_id, region_id)
);

-- Crime status details
DROP TABLE IF EXISTS tbl_crime_status_det;
CREATE TABLE tbl_crime_status_det (
    crime_status_refno INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    offence_head_id INT NOT NULL,
    case_stat_id INT NOT NULL,
    year_id INT NOT NULL,
    region_id INT NOT NULL,
    crime_status_num INT CHECK(crime_status_num BETWEEN 1 AND 999999999),
    created_by VARCHAR(50),
    created_date DATETIME,
    updated_by VARCHAR(50),
    updated_date DATETIME,
    status_ BOOLEAN DEFAULT 1,
    FOREIGN KEY (offence_head_id) REFERENCES tbl_offence_head_master(offence_head_id),
    FOREIGN KEY (case_stat_id) REFERENCES tbl_case_status_master(case_stat_id),
    FOREIGN KEY (year_id) REFERENCES tbl_year_master(year_id),
    FOREIGN KEY (region_id) REFERENCES tbl_region_master(region_id),
    INDEX idx_year_region (year_id, region_id)
);

-- Crime status law details
DROP TABLE IF EXISTS tbl_crime_status_law;
CREATE TABLE tbl_crime_status_law (
    crime_status_law_refno INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    offence_head_id INT NOT NULL,
    offence_id INT NOT NULL,
    year_id INT NOT NULL,
    region_id INT NOT NULL,
    crime_status_law_num INT CHECK(crime_status_law_num BETWEEN 1 AND 999999999),
    created_by VARCHAR(50),
    created_date DATETIME,
    updated_by VARCHAR(50),
    updated_date DATETIME,
    status_ BOOLEAN DEFAULT 1,
    FOREIGN KEY (offence_head_id) REFERENCES tbl_offence_head_master(offence_head_id),
    FOREIGN KEY (offence_id) REFERENCES tbl_offence_master(offence_id),
    FOREIGN KEY (year_id) REFERENCES tbl_year_master(year_id),
    FOREIGN KEY (region_id) REFERENCES tbl_region_master(region_id),
    INDEX idx_year_region (year_id, region_id)
);

-- Crime conviction details
DROP TABLE IF EXISTS tbl_crime_convict_det;
CREATE TABLE tbl_crime_convict_det (
    crime_convict_refno INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    conviction_id INT NOT NULL,
    year_id INT NOT NULL,
    region_id INT NOT NULL,
    crime_convict_num INT CHECK(crime_convict_num BETWEEN 1 AND 999999999),
    created_by VARCHAR(50),
    created_date DATETIME,
    updated_by VARCHAR(50),
    updated_date DATETIME,
    status_ BOOLEAN DEFAULT 1,
    FOREIGN KEY (conviction_id) REFERENCES tbl_conviction_master(conviction_id),
    FOREIGN KEY (year_id) REFERENCES tbl_year_master(year_id),
    FOREIGN KEY (region_id) REFERENCES tbl_region_master(region_id),
    INDEX idx_year_region (year_id, region_id)
);

-- ============================================================================
-- SECTION 5: ANIMAL HUSBANDRY DEPARTMENT MASTER TABLES
-- ============================================================================

-- Livestock master
DROP TABLE IF EXISTS tbl_livestock_master;
CREATE TABLE tbl_livestock_master (
    livestock_id INT PRIMARY KEY CHECK(livestock_id BETWEEN 0 AND 99),
    livestock_desc VARCHAR(100) NOT NULL,
    created_by VARCHAR(50),
    created_date DATETIME,
    updated_by VARCHAR(50),
    updated_date DATETIME,
    status_ BOOLEAN DEFAULT 1
);

-- Livestock division master
DROP TABLE IF EXISTS tbl_livestock_div_master;
CREATE TABLE tbl_livestock_div_master (
    livestock_div_id INT PRIMARY KEY CHECK(livestock_div_id BETWEEN 0 AND 99),
    livestock_div_desc VARCHAR(100) NOT NULL,
    created_by VARCHAR(50),
    created_date DATETIME,
    updated_by VARCHAR(50),
    updated_date DATETIME,
    status_ BOOLEAN DEFAULT 1
);

-- Livestock product master
DROP TABLE IF EXISTS tbl_livestock_prod_master;
CREATE TABLE tbl_livestock_prod_master (
    livestock_prod_id INT PRIMARY KEY CHECK(livestock_prod_id BETWEEN 0 AND 99),
    livestock_prod_desc VARCHAR(100) NOT NULL,
    livestock_unit VARCHAR(100),
    created_by VARCHAR(50),
    created_date DATETIME,
    updated_by VARCHAR(50),
    updated_date DATETIME,
    status_ BOOLEAN DEFAULT 1
);

-- Veterinary aid master
DROP TABLE IF EXISTS tbl_vet_aid_master;
CREATE TABLE tbl_vet_aid_master (
    vet_aid_id INT PRIMARY KEY CHECK(vet_aid_id BETWEEN 0 AND 999),
    vet_aid_desc VARCHAR(200) NOT NULL,
    created_by VARCHAR(50),
    created_date DATETIME,
    updated_by VARCHAR(50),
    updated_date DATETIME,
    status_ BOOLEAN DEFAULT 1
);

-- Veterinary infrastructure category master
DROP TABLE IF EXISTS tbl_vet_infra_cat_master;
CREATE TABLE tbl_vet_infra_cat_master (
    vet_infra_cat_id INT PRIMARY KEY CHECK(vet_infra_cat_id BETWEEN 0 AND 999),
    vet_infra_cat_desc VARCHAR(300) NOT NULL,
    created_by VARCHAR(50),
    created_date DATETIME,
    updated_by VARCHAR(50),
    updated_date DATETIME,
    status_ BOOLEAN DEFAULT 1
);

-- ============================================================================
-- SECTION 6: ANIMAL HUSBANDRY DEPARTMENT TRANSACTION TABLES
-- ============================================================================

-- Livestock census
DROP TABLE IF EXISTS tbl_livestock_census;
CREATE TABLE tbl_livestock_census (
    livestock_census_refno INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    livestock_id INT NOT NULL,
    livestock_div_id INT NOT NULL,
    year_id INT NOT NULL,
    region_id INT NOT NULL,
    livestock_num INT NOT NULL,
    created_by VARCHAR(50),
    created_date DATETIME,
    updated_by VARCHAR(50),
    updated_date DATETIME,
    status_ BOOLEAN DEFAULT 1,
    FOREIGN KEY (livestock_id) REFERENCES tbl_livestock_master(livestock_id),
    FOREIGN KEY (livestock_div_id) REFERENCES tbl_livestock_div_master(livestock_div_id),
    FOREIGN KEY (year_id) REFERENCES tbl_year_master(year_id),
    FOREIGN KEY (region_id) REFERENCES tbl_region_master(region_id),
    INDEX idx_year_region (year_id, region_id)
);

-- Veterinary aid
DROP TABLE IF EXISTS tbl_vet_aid;
CREATE TABLE tbl_vet_aid (
    vet_aid_refno INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    vet_aid_id INT NOT NULL,
    unit_id INT NOT NULL,
    year_id INT NOT NULL,
    region_id INT NOT NULL,
    vet_aid_num INT NOT NULL,
    created_by VARCHAR(50),
    created_date DATETIME,
    updated_by VARCHAR(50),
    updated_date DATETIME,
    status_ BOOLEAN DEFAULT 1,
    FOREIGN KEY (vet_aid_id) REFERENCES tbl_vet_aid_master(vet_aid_id),
    FOREIGN KEY (unit_id) REFERENCES tbl_unit_master(unit_id),
    FOREIGN KEY (year_id) REFERENCES tbl_year_master(year_id),
    FOREIGN KEY (region_id) REFERENCES tbl_region_master(region_id),
    INDEX idx_year_region (year_id, region_id)
);

-- Veterinary infrastructure
DROP TABLE IF EXISTS tbl_vet_infra;
CREATE TABLE tbl_vet_infra (
    vet_infra_refno INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    vet_infra_cat_id INT NOT NULL,
    unit_id INT NOT NULL,
    year_id INT NOT NULL,
    region_id INT NOT NULL,
    vet_infra_num INT NOT NULL,
    created_by VARCHAR(50),
    created_date DATETIME,
    updated_by VARCHAR(50),
    updated_date DATETIME,
    status_ BOOLEAN DEFAULT 1,
    FOREIGN KEY (vet_infra_cat_id) REFERENCES tbl_vet_infra_cat_master(vet_infra_cat_id),
    FOREIGN KEY (unit_id) REFERENCES tbl_unit_master(unit_id),
    FOREIGN KEY (year_id) REFERENCES tbl_year_master(year_id),
    FOREIGN KEY (region_id) REFERENCES tbl_region_master(region_id),
    INDEX idx_year_region (year_id, region_id)
);

-- Livestock production
DROP TABLE IF EXISTS tbl_livestock_prod;
CREATE TABLE tbl_livestock_prod (
    livestock_prod_refno INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    livestock_prod_id INT NOT NULL,
    year_id INT NOT NULL,
    region_id INT NOT NULL,
    unit_id INT,
    livestock_prod_num INT CHECK(livestock_prod_num BETWEEN 1 AND 9999999),
    created_by VARCHAR(50),
    created_date DATETIME,
    updated_by VARCHAR(50),
    updated_date DATETIME,
    status_ BOOLEAN DEFAULT 1,
    FOREIGN KEY (livestock_prod_id) REFERENCES tbl_livestock_prod_master(livestock_prod_id),
    FOREIGN KEY (year_id) REFERENCES tbl_year_master(year_id),
    FOREIGN KEY (region_id) REFERENCES tbl_region_master(region_id),
    FOREIGN KEY (unit_id) REFERENCES tbl_unit_master(unit_id),
    INDEX idx_year_region (year_id, region_id)
);

-- ============================================================================
-- SECTION 7: SEED DATA - ESSENTIAL MASTER DATA
-- ============================================================================

-- Insert regions
INSERT INTO tbl_region_master (region_id, region_desc, created_by, created_date) VALUES
(1, 'Puducherry', 'admin', CURRENT_TIMESTAMP),
(2, 'Karaikal', 'admin', CURRENT_TIMESTAMP),
(3, 'Yanam', 'admin', CURRENT_TIMESTAMP),
(4, 'Mahe', 'admin', CURRENT_TIMESTAMP)
ON DUPLICATE KEY UPDATE region_desc=VALUES(region_desc);

-- Insert years (example data)
INSERT INTO tbl_year_master (year_id, year_desc, start_date, end_date, created_by, created_date) VALUES
(1, '2025-26', '2025-04-01', '2026-03-31', 'admin', CURRENT_TIMESTAMP),
(2, '2024-25', '2024-04-01', '2025-03-31', 'admin', CURRENT_TIMESTAMP),
(101, '2025-26', '2025-06-01', '2026-05-31', 'admin', CURRENT_TIMESTAMP),
(102, '2024-25', '2024-06-01', '2025-05-31', 'admin', CURRENT_TIMESTAMP)
ON DUPLICATE KEY UPDATE year_desc=VALUES(year_desc);

-- Insert units
INSERT INTO tbl_unit_master (unit_id, unit_measure, created_by, created_date) VALUES
(1, 'Hectares', 'admin', CURRENT_TIMESTAMP),
(2, 'Acres', 'admin', CURRENT_TIMESTAMP),
(3, 'Square Kilometers', 'admin', CURRENT_TIMESTAMP),
(4, 'Square Meters', 'admin', CURRENT_TIMESTAMP),
(5, 'Numbers', 'admin', CURRENT_TIMESTAMP),
(6, 'Litres', 'admin', CURRENT_TIMESTAMP),
(7, 'Eggs (Number)', 'admin', CURRENT_TIMESTAMP)
ON DUPLICATE KEY UPDATE unit_measure=VALUES(unit_measure);

-- Insert offence master
INSERT INTO tbl_offence_master (offence_id, offence_desc, created_by, created_date) VALUES
(1, 'Reported', 'admin', CURRENT_TIMESTAMP),
(2, 'Detected', 'admin', CURRENT_TIMESTAMP)
ON DUPLICATE KEY UPDATE offence_desc=VALUES(offence_desc);

-- Register transaction tables in txn_registry
INSERT INTO txn_registry (department, report_name, target_table_name) VALUES
-- Police Department
('Police', 'Accident Details', 'tbl_accident_details'),
('Police', 'Cognizable Crime Details', 'tbl_cogniz_crime'),
('Police', 'Crime Law Details', 'tbl_crime_law_details'),
('Police', 'Stolen Property Recovery Details', 'tbl_stole_recov_det'),
('Police', 'Civil Police Details', 'tbl_civil_pol_det'),
('Police', 'Police Working Strength', 'tbl_pol_work_strgth_det'),
('Police', 'Riot Hurt Details', 'tbl_riot_hurt_det'),
('Police', 'Currency Crime Details', 'tbl_currency_crime_det'),
('Police', 'Crime Statistics Details', 'tbl_crime_stat_det'),
('Police', 'Crime Status Details', 'tbl_crime_status_det'),
('Police', 'Crime Status Law Details', 'tbl_crime_status_law'),
('Police', 'Crime Conviction Details', 'tbl_crime_convict_det'),
-- Animal Husbandry Department
('Animal Husbandry', 'Livestock Census Details', 'tbl_livestock_census'),
('Animal Husbandry', 'Veterinary Aid Details', 'tbl_vet_aid'),
('Animal Husbandry', 'Veterinary Infrastructure Details', 'tbl_vet_infra'),
('Animal Husbandry', 'Livestock Production Details', 'tbl_livestock_prod')
ON DUPLICATE KEY UPDATE report_name=VALUES(report_name);

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================
-- Note: Additional master data and seed data can be added as needed
-- For production, ensure proper user creation and password hashing
-- ============================================================================

