-- ============================================================
--  GRIEVANCE HANDLING SYSTEM — DATABASE SCHEMA
--  Compatible with existing DES application
-- ============================================================

-- ──────────────────────────────────────────
--  MASTER TABLE 1: Grievance Types
-- ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tbl_grievance_type (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    type_name   VARCHAR(150) NOT NULL UNIQUE,
    description VARCHAR(300),
    is_active   TINYINT(1)   NOT NULL DEFAULT 1,
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Seed data matching whiteboard types
INSERT INTO tbl_grievance_type (type_name, description) VALUES
    ('Download of Excel Sheet',  'Issue with downloading the Excel template or data'),
    ('Upload of Excel Sheet',    'Problem while uploading an Excel register file'),
    ('Upload of JSON',           'Issue related to JSON data upload'),
    ('Approval of Data',         'Problem with the data approval/rejection workflow'),
    ('Login / Access Issue',     'Cannot login or access a page'),
    ('Other',                    'Any other issue not listed above');

-- ──────────────────────────────────────────
--  MASTER TABLE 2: Grievance Status
-- ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tbl_grievance_status (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    status_name VARCHAR(50)  NOT NULL UNIQUE,  -- Submitted, Pending, Closed
    color_hex   VARCHAR(10)  NOT NULL DEFAULT '#6b7280'
);

INSERT INTO tbl_grievance_status (status_name, color_hex) VALUES
    ('Submitted', '#3b82f6'),
    ('Pending',   '#f59e0b'),
    ('Closed',    '#10b981');

-- ──────────────────────────────────────────
--  TRANSACTION TABLE: Grievance Tickets
-- ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tbl_grievance_ticket (
    id              INT AUTO_INCREMENT PRIMARY KEY,

    -- Auto-generated ticket number e.g. GRV-2026-03-0001
    ticket_no       VARCHAR(20)   NOT NULL UNIQUE,

    -- Who raised it
    submitted_by    VARCHAR(100)  NOT NULL,          -- username
    department      VARCHAR(150),

    -- What is the problem
    grievance_type_id INT         NOT NULL,
    details         TEXT          NOT NULL,

    -- Attachment (stored as LONGBLOB in tbl_grievance_attachment)
    has_attachment  TINYINT(1)    NOT NULL DEFAULT 0,

    -- Workflow
    status_id       INT           NOT NULL DEFAULT 1, -- 1=Submitted
    assigned_to     VARCHAR(100),                     -- admin username
    admin_remark    TEXT,                             -- admin reply / resolution note
    closed_by       VARCHAR(100),
    closed_at       DATETIME,

    -- Audit
    created_at      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (grievance_type_id) REFERENCES tbl_grievance_type(id),
    FOREIGN KEY (status_id)         REFERENCES tbl_grievance_status(id)
);

-- ──────────────────────────────────────────
--  TRANSACTION TABLE: Attachments
--  Store image/file as LONGBLOB in DB
-- ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tbl_grievance_attachment (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    ticket_id       INT           NOT NULL,
    filename        VARCHAR(255)  NOT NULL,
    mimetype        VARCHAR(100)  NOT NULL,
    file_data       LONGBLOB      NOT NULL,       -- raw bytes
    file_size_kb    INT,
    uploaded_at     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (ticket_id) REFERENCES tbl_grievance_ticket(id) ON DELETE CASCADE
);

-- ──────────────────────────────────────────
--  TRANSACTION TABLE: Ticket Activity Log
--  Every status change / admin comment is logged
-- ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tbl_grievance_log (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    ticket_id   INT           NOT NULL,
    action_by   VARCHAR(100)  NOT NULL,
    action      VARCHAR(100)  NOT NULL,  -- e.g. "Status changed to Pending"
    remark      TEXT,
    created_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (ticket_id) REFERENCES tbl_grievance_ticket(id) ON DELETE CASCADE
);

-- ──────────────────────────────────────────
--  USEFUL INDEXES
-- ──────────────────────────────────────────
CREATE INDEX idx_grv_ticket_user   ON tbl_grievance_ticket(submitted_by);
CREATE INDEX idx_grv_ticket_status ON tbl_grievance_ticket(status_id);
CREATE INDEX idx_grv_ticket_type   ON tbl_grievance_ticket(grievance_type_id);
CREATE INDEX idx_grv_log_ticket    ON tbl_grievance_log(ticket_id);