from reportlab.lib.pagesizes import A4
import os
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus.flowables import Flowable

W, H = A4

# ── Colour palette ──────────────────────────────────────
NAVY    = colors.HexColor("#1e5a8e")
DARK    = colors.HexColor("#0c3d5d")
ACCENT  = colors.HexColor("#fbbf24")
GREEN   = colors.HexColor("#10b981")
RED     = colors.HexColor("#ef4444")
PURPLE  = colors.HexColor("#7c3aed")
TEAL    = colors.HexColor("#0891b2")
GRAY50  = colors.HexColor("#f8fafc")
GRAY100 = colors.HexColor("#f1f5f9")
GRAY200 = colors.HexColor("#e2e8f0")
GRAY600 = colors.HexColor("#475569")
GRAY900 = colors.HexColor("#0f172a")
WHITE   = colors.white
CODE_BG = colors.HexColor("#1e293b")
CODE_FG = colors.HexColor("#e2e8f0")

# ── Styles ───────────────────────────────────────────────
styles = getSampleStyleSheet()

def S(name, **kw):
    return ParagraphStyle(name, **kw)

Title     = S("MyTitle",  fontName="Helvetica-Bold",  fontSize=26, textColor=WHITE,      alignment=TA_CENTER, spaceAfter=6)
SubTitle  = S("MySub",    fontName="Helvetica",        fontSize=12, textColor=ACCENT,     alignment=TA_CENTER, spaceAfter=4)
H1        = S("MyH1",     fontName="Helvetica-Bold",  fontSize=15, textColor=NAVY,       spaceBefore=14, spaceAfter=6, borderPad=4)
H2        = S("MyH2",     fontName="Helvetica-Bold",  fontSize=12, textColor=DARK,       spaceBefore=10, spaceAfter=4)
H3        = S("MyH3",     fontName="Helvetica-Bold",  fontSize=10, textColor=GRAY600,    spaceBefore=8,  spaceAfter=3)
Body      = S("MyBody",   fontName="Helvetica",        fontSize=9.5, textColor=GRAY900,  leading=14, spaceAfter=5, alignment=TA_JUSTIFY)
Bullet    = S("MyBullet", fontName="Helvetica",        fontSize=9.5, textColor=GRAY900,  leading=13, spaceAfter=3, leftIndent=14, firstLineIndent=-10)
Code      = S("MyCode",   fontName="Courier",          fontSize=8,   textColor=CODE_FG,  backColor=CODE_BG, leading=12, leftIndent=8, rightIndent=8, spaceAfter=6, spaceBefore=4, borderPad=6)
CodeLabel = S("CLabel",   fontName="Courier-Bold",     fontSize=7.5, textColor=ACCENT,   backColor=CODE_BG, leading=10, leftIndent=8)
Note      = S("MyNote",   fontName="Helvetica-Oblique",fontSize=8.5, textColor=GRAY600,  leading=12, spaceAfter=4, leftIndent=10)
Tag       = S("MyTag",    fontName="Helvetica-Bold",   fontSize=8,   textColor=WHITE,     alignment=TA_CENTER)

def b(txt):   return f"<b>{txt}</b>"
def i(txt):   return f"<i>{txt}</i>"
def c(txt):   return f'<font name="Courier" color="#1e5a8e">{txt}</font>'
def bullet(txt): return Paragraph(f"• {txt}", Bullet)

class ColorBox(Flowable):
    """A colored rectangle banner."""
    def __init__(self, w, h, fill, radius=6):
        self.bw, self.bh, self.fill, self.radius = w, h, fill, radius
    def wrap(self, *a): return self.bw, self.bh
    def draw(self):
        self.canv.setFillColor(self.fill)
        self.canv.roundRect(0, 0, self.bw, self.bh, self.radius, fill=1, stroke=0)

class SectionBadge(Flowable):
    def __init__(self, text, color, width=None):
        self.text, self.color = text, color
        self.w = width or 180
    def wrap(self, *a): return self.w, 22
    def draw(self):
        c = self.canv
        c.setFillColor(self.color)
        c.roundRect(0, 0, self.w, 22, 4, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(self.w/2, 7, self.text)

def code_block(label, lines):
    story = []
    story.append(Paragraph(f"  {label}", CodeLabel))
    for line in lines:
        story.append(Paragraph(f"  {line}", Code))
    return story

def section_header(title, color=NAVY, sub=None):
    items = []
    items.append(HRFlowable(width="100%", thickness=2, color=color, spaceAfter=4))
    items.append(Paragraph(title, H1))
    if sub:
        items.append(Paragraph(sub, Note))
    return items

def module_card(title, color, items):
    """Colored left-bordered card."""
    rows = [[Paragraph(f"<b>{title}</b>", S("ct", fontName="Helvetica-Bold", fontSize=10, textColor=color))]]
    for it in items:
        rows.append([Paragraph(f"• {it}", S("ci", fontName="Helvetica", fontSize=9, textColor=GRAY900, leading=13))])
    t = Table(rows, colWidths=[W - 4*cm])
    t.setStyle(TableStyle([
        ('LEFTPADDING',  (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING',   (0,0), (-1,-1), 4),
        ('BOTTOMPADDING',(0,0), (-1,-1), 3),
        ('BACKGROUND',   (0,0), (-1,-1), colors.HexColor("#f8fafc")),
        ('LINEBEFORE',   (0,0), (-1,-1), 3, color),
        ('ROUNDEDCORNERS', [4]),
    ]))
    return t

# ═══════════════════════════════════════════════════════
# BUILD STORY
# ═══════════════════════════════════════════════════════
story = []

# ── COVER PAGE ────────────────────────────────────────
story.append(Spacer(1, 1.5*cm))

# Big navy banner
cover_bg = Table([[""]],colWidths=[W-4*cm], rowHeights=[5.5*cm])
cover_bg.setStyle(TableStyle([
    ('BACKGROUND', (0,0),(0,0), NAVY),
    ('ROUNDEDCORNERS', [10]),
]))
story.append(cover_bg)
story.append(Spacer(1, -5.8*cm))

story.append(Paragraph("DIRECTORATE OF ECONOMICS", Title))
story.append(Paragraph("AND STATISTICS", Title))
story.append(Paragraph("Data Management Portal", SubTitle))
story.append(Paragraph("Technical Documentation &amp; Interview Guide", SubTitle))
story.append(Spacer(1, 5*cm))

# Info table
info = [
    ["Project",   "DES Data Management Portal"],
    ["Stack",     "Flask (Python) · MySQL · Vanilla JS · HTML/CSS"],
    ["Modules",   "Admin · Approver · User · Grievance · Statistics"],
    ["Purpose",   "Multi-role Excel register upload, approval &amp; reporting system"],
]
t_info = Table(info, colWidths=[3.5*cm, W - 7.5*cm])
t_info.setStyle(TableStyle([
    ('FONTNAME',    (0,0),(-1,-1),"Helvetica"),
    ('FONTSIZE',    (0,0),(-1,-1), 9.5),
    ('FONTNAME',    (0,0),(0,-1),"Helvetica-Bold"),
    ('TEXTCOLOR',   (0,0),(0,-1), NAVY),
    ('TEXTCOLOR',   (1,0),(1,-1), GRAY900),
    ('ROWBACKGROUNDS',(0,0),(-1,-1),[GRAY50, WHITE]),
    ('TOPPADDING',  (0,0),(-1,-1), 6),
    ('BOTTOMPADDING',(0,0),(-1,-1), 6),
    ('LEFTPADDING', (0,0),(-1,-1), 10),
    ('GRID',        (0,0),(-1,-1), 0.5, GRAY200),
    ('ROUNDEDCORNERS',[4]),
]))
story.append(t_info)
story.append(PageBreak())

# ── TABLE OF CONTENTS ─────────────────────────────────
story += section_header("Table of Contents")
toc = [
    ("1", "System Overview",              "Architecture, tech stack, role hierarchy"),
    ("2", "Admin Module",                 "User management, permissions, uploads, statistics"),
    ("3", "Approver Module",              "Upload queue, row-level approval, remarks"),
    ("4", "User Module",                  "Register upload, history, locked status"),
    ("5", "Statistics Module",            "Department completion, register-wise breakdown"),
    ("6", "Grievance Handling Module",    "Ticket submission, tracking, admin resolution"),
    ("7", "Database Design",              "Master & transaction tables, key relationships"),
    ("8", "Key Code Snippets",            "Backend routes, frontend patterns"),
    ("9", "Interview Q&amp;A",            "Common questions with answers"),
]
toc_data = [[Paragraph(f"<b>{n}.</b>", S("tn",fontName="Helvetica-Bold",fontSize=9.5,textColor=NAVY)),
             Paragraph(t, S("tt",fontName="Helvetica-Bold",fontSize=9.5,textColor=GRAY900)),
             Paragraph(sub, S("ts",fontName="Helvetica",fontSize=8.5,textColor=GRAY600))]
            for n,t,sub in toc]
t_toc = Table(toc_data, colWidths=[1*cm, 5.5*cm, W-10.5*cm])
t_toc.setStyle(TableStyle([
    ('ROWBACKGROUNDS',(0,0),(-1,-1),[GRAY50, WHITE]),
    ('TOPPADDING',(0,0),(-1,-1),7),
    ('BOTTOMPADDING',(0,0),(-1,-1),7),
    ('LEFTPADDING',(0,0),(-1,-1),8),
    ('GRID',(0,0),(-1,-1),0.5,GRAY200),
]))
story.append(t_toc)
story.append(PageBreak())

# ─────────────────────────────────────────────────────
# 1. SYSTEM OVERVIEW
# ─────────────────────────────────────────────────────
story += section_header("1. System Overview",
    sub="A multi-role web portal for the Directorate of Economics & Statistics to manage Excel register uploads, approvals and reporting.")

story.append(Paragraph(b("Purpose"), H2))
story.append(Paragraph(
    "The DES Data Management Portal digitises the collection of statistical registers from departments across Tamil Nadu. "
    "Each department uploads Excel files containing census and survey data. These uploads pass through an approval workflow "
    "before being committed to the central database. The portal provides real-time statistics, grievance management, "
    "and granular permission control.",
    Body))

story.append(Paragraph(b("Tech Stack"), H2))
stack_data = [
    [b("Layer"), b("Technology"), b("Role")],
    ["Backend",   "Flask (Python 3.11)",      "REST API, session auth, business logic"],
    ["Database",  "MySQL 8",                  "All data, permissions, uploads, attachments"],
    ["Frontend",  "Vanilla JS + HTML/CSS",    "SPA-style dashboards, Chart.js charts"],
    ["Excel",     "pandas + openpyxl",        "Template download, data upload, export"],
    ["PDF",       "ReportLab",                "Documentation generation"],
    ["Auth",      "Flask session + bcrypt",   "Role-based access control"],
]
t_stack = Table(stack_data, colWidths=[3*cm, 5*cm, W-12*cm])
t_stack.setStyle(TableStyle([
    ('BACKGROUND',(0,0),(-1,0), DARK),
    ('TEXTCOLOR',(0,0),(-1,0), WHITE),
    ('FONTNAME',(0,0),(-1,0),"Helvetica-Bold"),
    ('FONTSIZE',(0,0),(-1,-1), 9),
    ('ROWBACKGROUNDS',(0,1),(-1,-1),[GRAY50,WHITE]),
    ('GRID',(0,0),(-1,-1),0.5,GRAY200),
    ('TOPPADDING',(0,0),(-1,-1),6),
    ('BOTTOMPADDING',(0,0),(-1,-1),6),
    ('LEFTPADDING',(0,0),(-1,-1),8),
]))
story.append(t_stack)
story.append(Spacer(1, 8))

story.append(Paragraph(b("Role Hierarchy"), H2))
roles = [
    ("Admin",    NAVY,   "Full control — user management, permissions, statistics, grievance resolution"),
    ("Approver", PURPLE, "Reviews uploads — accepts/rejects rows, adds remarks, approves/rejects uploads"),
    ("User",     GREEN,  "Uploads Excel registers, views status, edits rejected rows, submits grievances"),
]
role_data = [[Paragraph(f"<b>{r}</b>", S("rl",fontName="Helvetica-Bold",fontSize=9,textColor=WHITE)),
              Paragraph(desc, S("rd",fontName="Helvetica",fontSize=9,textColor=GRAY900))]
             for r,c,desc in roles]
t_roles = Table(role_data, colWidths=[3*cm, W-7*cm])
t_roles.setStyle(TableStyle([
    ('BACKGROUND',(0,0),(0,0), NAVY),
    ('BACKGROUND',(0,1),(0,1), PURPLE),
    ('BACKGROUND',(0,2),(0,2), GREEN),
    ('ROWBACKGROUNDS',(1,0),(1,-1),[GRAY50]),
    ('TOPPADDING',(0,0),(-1,-1),8),
    ('BOTTOMPADDING',(0,0),(-1,-1),8),
    ('LEFTPADDING',(0,0),(-1,-1),10),
    ('GRID',(0,0),(-1,-1),0.5,GRAY200),
]))
story.append(t_roles)
story.append(PageBreak())

# ─────────────────────────────────────────────────────
# 2. ADMIN MODULE
# ─────────────────────────────────────────────────────
story += section_header("2. Admin Module",
    sub="Central control panel — user CRUD, permission management, upload monitoring, statistics & grievance resolution.")

story.append(Paragraph(b("Key Capabilities"), H2))
for cap in [
    "Add / edit / delete users with department and role assignment",
    "Fine-grained permission control per user per department (View / Edit / Download)",
    "View all uploads across all departments with status badges",
    "Statistics tab: department completion rates, register-wise breakdown with dropdown filter",
    "Error log viewer with traceback display",
    "Grievance ticket dashboard — update status (Submitted → Pending → Closed) with resolution notes",
]:
    story.append(bullet(cap))
story.append(Spacer(1, 6))

story.append(Paragraph(b("Permission System"), H2))
story.append(Paragraph(
    "Permissions are stored per user per department. Three levels exist — they are not additive flags "
    "but represent intent:", Body))
perm_rows = [
    [b("Toggle"),     b("What it grants"),                              b("Auto-rules")],
    ["👁 View",       "Read-only access to uploaded data",              "Removing View also removes Edit"],
    ["✏ Edit",       "View + edit rows + delete rows + download",      "Granting Edit auto-enables View & Download"],
    ["⬇ Download",   "Export data as Excel only",                      "Removing Download also removes Edit"],
]
t_perm = Table(perm_rows, colWidths=[2.5*cm, 6*cm, W-12.5*cm])
t_perm.setStyle(TableStyle([
    ('BACKGROUND',(0,0),(-1,0), DARK), ('TEXTCOLOR',(0,0),(-1,0), WHITE),
    ('FONTNAME',(0,0),(-1,0),"Helvetica-Bold"), ('FONTSIZE',(0,0),(-1,-1),9),
    ('ROWBACKGROUNDS',(0,1),(-1,-1),[GRAY50,WHITE]),
    ('GRID',(0,0),(-1,-1),0.5,GRAY200),
    ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),
    ('LEFTPADDING',(0,0),(-1,-1),8),
]))
story.append(t_perm)
story.append(Spacer(1,6))

story += code_block("Backend — save permissions  (admin_routes.py)",
    ['@admin_bp.route("/permissions/update", methods=["POST"])',
     'def update_permissions(cursor, conn):',
     '    data    = request.get_json()',
     '    user_id = data["user_id"]',
     '    perms   = data["permissions"]   # { "GLOBAL": {view,edit,download}, ... }',
     '    cursor.execute("DELETE FROM user_permissions WHERE user_id=%s", (user_id,))',
     '    for dept, p in perms.items():',
     '        cursor.execute("""INSERT INTO user_permissions',
     '            (user_id, department, can_view, can_edit, can_download)',
     '            VALUES (%s,%s,%s,%s,%s)""",',
     '            (user_id, dept, p["view"], p["edit"], p["download"]))',
     '    conn.commit()',
     '    return jsonify({"message": "Permissions saved"})'])

story.append(PageBreak())

# ─────────────────────────────────────────────────────
# 3. APPROVER MODULE
# ─────────────────────────────────────────────────────
story += section_header("3. Approver Module",
    sub="Reviews uploads from departments — approves or rejects at both upload and row level with a structured workflow.")

story.append(Paragraph(b("Approval Workflow"), H2))
workflow = [
    ["Step", "Action",                       "Status Change"],
    ["1",    "Department uploads Excel",      "Upload → Pending"],
    ["2",    "Approver opens upload",         "Reviews each row"],
    ["3",    "Row-level Accept / Reject",     "Row: is_approved = 1 or 0"],
    ["4",    "Approver adds row remark",      "Row gets rejection explanation"],
    ["5",    "All rows reviewed",             "Finalize Approval button shown"],
    ["6",    "Approver finalizes",            "Upload → Approved or Rejected"],
    ["7",    "User sees result",              "Green/Red badge on dashboard"],
]
t_wf = Table(workflow, colWidths=[1*cm, 5.5*cm, W-10.5*cm])
t_wf.setStyle(TableStyle([
    ('BACKGROUND',(0,0),(-1,0), DARK), ('TEXTCOLOR',(0,0),(-1,0), WHITE),
    ('FONTNAME',(0,0),(-1,0),"Helvetica-Bold"), ('FONTSIZE',(0,0),(-1,-1),9),
    ('ROWBACKGROUNDS',(0,1),(-1,-1),[GRAY50,WHITE]),
    ('GRID',(0,0),(-1,-1),0.5,GRAY200),
    ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),
    ('LEFTPADDING',(0,0),(-1,-1),8),
]))
story.append(t_wf)
story.append(Spacer(1,8))

story.append(Paragraph(b("Safe Bulk Approval"), H2))
story.append(Paragraph(
    "A key design decision: clicking 'Select All Accept' does NOT immediately approve the upload. "
    "It only marks all rows as accepted in the database and shows a yellow confirmation banner. "
    "The approver must explicitly click 'Finalize Approval'. "
    "If any row is later rejected, the upload status automatically reverts to Pending.", Body))

story += code_block("Frontend — finalizeUploadApproval()  (view_excel_data.html)",
    ['async function finalizeUploadApproval() {',
     '    // Safety check before calling approve_upload',
     '    const anyRejected = allRowsData.some(r =>',
     '        approvalStatus(r["is_approved"]) === 0);',
     '    if (anyRejected) {',
     '        flash("Cannot approve — some rows are Rejected");',
     '        return;',
     '    }',
     '    await fetch("/api/approve_upload", {',
     '        method: "POST",',
     '        body: JSON.stringify({ upload_id: parseInt(uploadId) })',
     '    });',
     '}'])

story += code_block("Backend — revert to pending when row is rejected  (approver_routes.py)",
    ['@approver_bp.route("/api/revert_upload_pending", methods=["POST"])',
     '@with_db_connection',
     'def revert_upload_pending(cursor, conn):',
     '    upload_id = request.get_json()["upload_id"]',
     '    cursor.execute(',
     '        "UPDATE excel_uploads SET status_ = NULL WHERE id = %s",',
     '        (upload_id,)',
     '    )',
     '    conn.commit()',
     '    return jsonify({"message": "Reverted to pending"})'])

story.append(Paragraph(b("Row Remarks"), H2))
story.append(Paragraph(
    "When a row is rejected, the approver can add a free-text remark explaining why. "
    "Remarks are stored in a separate table linked to the row PK and upload ID. "
    "Users see these remarks as inline badges and can open a modal to read the full explanation.", Body))

story += code_block("DB — row_remarks table",
    ['CREATE TABLE row_remarks (',
     '    id         INT AUTO_INCREMENT PRIMARY KEY,',
     '    upload_id  INT NOT NULL,',
     '    table_name VARCHAR(100) NOT NULL,',
     '    row_id     INT NOT NULL,',
     '    remark     TEXT,',
     '    created_by VARCHAR(100),',
     '    created_at DATETIME DEFAULT CURRENT_TIMESTAMP',
     ');'])

story.append(PageBreak())

# ─────────────────────────────────────────────────────
# 4. USER MODULE
# ─────────────────────────────────────────────────────
story += section_header("4. User Module",
    sub="Department staff upload Excel registers, monitor approval status, and re-edit rejected data.")

story.append(Paragraph(b("Key Features"), H2))
for f in [
    "Select register from dropdown → download the Excel template with correct columns",
    "Upload filled template — file is validated and stored with upload tracking",
    "Upload History tab shows all submissions with filter tabs (All / Pending / Approved / Rejected)",
    "Approved uploads show a Lock icon — no further edits allowed",
    "Rejected uploads show an Edit Rejected button — user edits only the rejected rows",
    "View Row Remarks button shows the approver's row-level explanations",
    "Request Re-Approval button resubmits corrected rows to the approver queue",
    "Submit Grievance option in the user dropdown menu",
]:
    story.append(bullet(f))
story.append(Spacer(1,6))

story.append(Paragraph(b("Ticket Number Format"), H2))
story.append(Paragraph(
    f"Upload ticket number: {c('AGR-2026-03-0001')} where {c('AGR')} = first 3 letters of department, "
    f"{c('2026-03')} = year-month, {c('0001')} = 4-digit running sequence (resets each month per department).", Body))
story.append(PageBreak())

# ─────────────────────────────────────────────────────
# 5. STATISTICS MODULE
# ─────────────────────────────────────────────────────
story += section_header("5. Statistics Module",
    sub="Real-time dashboard showing department-level and register-level completion rates.")

story.append(Paragraph(b("Department Details Tab"), H2))
for f in [
    "Shows all departments with status: Submitted / Pending / Not Submitted",
    "Color-coded rows: green = approved, yellow = pending, red = not submitted",
    "Inline progress bar showing completion percentage per department",
    "Live search filter — type to instantly narrow the department list",
]:
    story.append(bullet(f))

story.append(Paragraph(b("Register-wise Breakdown Tab"), H2))
story.append(Paragraph(
    "Select a department from the dropdown. The system queries txn_registry for all registers "
    "assigned to that department and matches each against excel_uploads to determine status.", Body))

story += code_block("Backend — dept_register_breakdown  (statistics_routes.py)",
    ['@statistics_bp.route("/api/statistics/dept_register_breakdown")',
     '@with_db_connection',
     'def dept_register_breakdown(cursor, conn):',
     '    dept = request.args.get("department")',
     '    # Get all registers for this dept from txn_registry',
     '    cursor.execute("""SELECT report_name, target_table_name',
     '        FROM txn_registry WHERE department = %s""", (dept,))',
     '    registers = cursor.fetchall()',
     '    for reg in registers:',
     '        # Count uploads and get latest status',
     '        cursor.execute("""SELECT COUNT(*) AS cnt, status_,',
     '            updated_date, updated_by FROM excel_uploads',
     '            WHERE department=%s AND table_name=%s',
     '            ORDER BY updated_date DESC LIMIT 1""",',
     '            [dept, reg["target_table_name"]])',
     '        upload = cursor.fetchone()',
     '        # status: approved / rejected / pending / not_uploaded'])

story.append(Paragraph(b("Summary Cards"), H2))
summary_rows = [
    [b("Card"), b("Calculation")],
    ["Total Registers",   "COUNT(*) from txn_registry WHERE department = selected"],
    ["Approved",          "Rows where upload status_ = 1"],
    ["Pending",           "Rows where upload exists but status_ = NULL"],
    ["Not Uploaded",      "Registers with no matching row in excel_uploads"],
    ["Completion %",      "(Approved / Total) * 100"],
]
t_sum = Table(summary_rows, colWidths=[4*cm, W-8*cm])
t_sum.setStyle(TableStyle([
    ('BACKGROUND',(0,0),(-1,0), DARK), ('TEXTCOLOR',(0,0),(-1,0), WHITE),
    ('FONTNAME',(0,0),(-1,0),"Helvetica-Bold"), ('FONTSIZE',(0,0),(-1,-1),9),
    ('ROWBACKGROUNDS',(0,1),(-1,-1),[GRAY50,WHITE]),
    ('GRID',(0,0),(-1,-1),0.5,GRAY200),
    ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),
    ('LEFTPADDING',(0,0),(-1,-1),8),
]))
story.append(t_sum)
story.append(PageBreak())

# ─────────────────────────────────────────────────────
# 6. GRIEVANCE MODULE
# ─────────────────────────────────────────────────────
story += section_header("6. Grievance Handling Module",
    sub="Users and approvers submit support tickets. Admin resolves and closes them with activity logging.")

story.append(Paragraph(b("Database Design"), H2))
grv_tables = [
    ("tbl_grievance_type",       "Master — 6 grievance categories (Download Excel, Upload Excel, Approval, etc.)"),
    ("tbl_grievance_status",     "Master — Submitted / Pending / Closed with color codes"),
    ("tbl_grievance_ticket",     "Transaction — every ticket: ticket_no, details, status, admin_remark"),
    ("tbl_grievance_attachment", "Stores image/PDF as LONGBLOB in MySQL, linked to ticket"),
    ("tbl_grievance_log",        "Audit trail — every status change logged with timestamp and actor"),
]
for tbl, desc in grv_tables:
    story.append(Paragraph(f"• {c(tbl)} — {desc}", Bullet))
story.append(Spacer(1,6))

story.append(Paragraph(b("Ticket Number Generation"), H2))
story += code_block("grievance_routes.py — generate_ticket_no()",
    ['def generate_ticket_no(cursor, department=""):',
     '    # AGR-2026-03-0001 format',
     '    dept_code = (department[:3].upper() if department else "GEN")',
     '    prefix    = f"{dept_code}-{datetime.now().strftime(\'%Y-%m\')}-"',
     '    cursor.execute(',
     '        "SELECT COUNT(*) AS cnt FROM tbl_grievance_ticket',
     '         WHERE ticket_no LIKE %s", (f"{prefix}%",))',
     '    cnt = cursor.fetchone()["cnt"]',
     '    return f"{prefix}{str(cnt + 1).zfill(4)}"',
     '    # Result: AGR-2026-03-0001, AGR-2026-03-0002 ...'])

story.append(Paragraph(b("Attachment Storage"), H2))
story.append(Paragraph(
    "Attachments (screenshots, PDFs) are stored directly as LONGBLOB in MySQL — no filesystem dependency. "
    "When viewing, the backend fetches the bytes and returns them as base64 JSON. "
    "The frontend renders images inline or PDFs in an iframe popup.", Body))

story += code_block("Backend — return attachment as base64  (grievance_routes.py)",
    ['@grievance_bp.route("/api/grievance/attachment/<int:ticket_id>")',
     '@with_db_connection',
     'def download_attachment(cursor, conn, ticket_id):',
     '    cursor.execute(',
     '        "SELECT filename, mimetype, file_data",',
     '        "FROM tbl_grievance_attachment WHERE ticket_id=%s LIMIT 1",',
     '        (ticket_id,))',
     '    row = cursor.fetchone()',
     '    if request.args.get("mode") == "base64":',
     '        import base64',
     '        b64 = base64.b64encode(row["file_data"]).decode("utf-8")',
     '        return jsonify({"filename": row["filename"],',
     '                        "mimetype": row["mimetype"],',
     '                        "data":     b64})'])

story.append(Paragraph(b("Status Lifecycle"), H2))
lifecycle = [
    [b("Status"),    b("Meaning"),                        b("Who sets it")],
    ["Submitted",    "Ticket just raised by user",         "System on submit"],
    ["Pending",      "Admin is investigating",             "Admin — Update modal"],
    ["Closed",       "Issue resolved, ticket locked",      "Admin — with resolution note"],
]
t_lc = Table(lifecycle, colWidths=[2.5*cm, 6*cm, W-12.5*cm])
t_lc.setStyle(TableStyle([
    ('BACKGROUND',(0,0),(-1,0), DARK), ('TEXTCOLOR',(0,0),(-1,0), WHITE),
    ('FONTNAME',(0,0),(-1,0),"Helvetica-Bold"), ('FONTSIZE',(0,0),(-1,-1),9),
    ('ROWBACKGROUNDS',(0,1),(-1,-1),[GRAY50,WHITE]),
    ('GRID',(0,0),(-1,-1),0.5,GRAY200),
    ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),
    ('LEFTPADDING',(0,0),(-1,-1),8),
]))
story.append(t_lc)
story.append(PageBreak())

# ─────────────────────────────────────────────────────
# 7. DATABASE DESIGN
# ─────────────────────────────────────────────────────
story += section_header("7. Database Design",
    sub="MySQL schema with master tables for lookups and transaction tables for data.")

story.append(Paragraph(b("Master Tables"), H2))
master = [
    ("users",                  "All users — username, password hash, department, role"),
    ("tbl_departments",        "Department list — name, code"),
    ("txn_registry",           "Register catalogue — report_name, target_table_name, department"),
    ("tbl_column_metadata",    "Display labels per column per table — used for Excel headers"),
    ("tbl_grievance_type",     "Grievance categories"),
    ("tbl_grievance_status",   "Ticket status definitions"),
]
for tbl, desc in master:
    story.append(Paragraph(f"• {c(tbl)} — {desc}", Bullet))

story.append(Paragraph(b("Transaction Tables"), H2))
trans = [
    ("excel_uploads",           "Each upload attempt — filename, table_name, department, status_"),
    ("tbl_livestock_census",   "Example register — one row per submission, upload_id FK"),
    ("row_remarks",             "Per-row rejection notes from approver"),
    ("user_permissions",        "Per-user per-department access flags"),
    ("tbl_grievance_ticket",    "Grievance tickets"),
    ("tbl_grievance_attachment","Binary attachments linked to tickets"),
    ("tbl_grievance_log",       "Activity audit trail for tickets"),
    ("error_logs",              "System error logs for debugging"),
]
for tbl, desc in trans:
    story.append(Paragraph(f"• {c(tbl)} — {desc}", Bullet))
story.append(Spacer(1,8))

story += code_block("Key schema — excel_uploads",
    ['CREATE TABLE excel_uploads (',
     '    id           INT AUTO_INCREMENT PRIMARY KEY,',
     '    filename     VARCHAR(255),',
     '    table_name   VARCHAR(100),  -- which register',
     '    department   VARCHAR(150),',
     '    uploaded_by  VARCHAR(100),  -- username',
     '    status_      TINYINT,       -- NULL=pending 1=approved 0=rejected',
     '    rejection_reason TEXT,      -- upload-level remark from approver',
     '    updated_date DATETIME',
     ');'])

story.append(PageBreak())

# ─────────────────────────────────────────────────────
# 8. KEY CODE SNIPPETS
# ─────────────────────────────────────────────────────
story += section_header("8. Key Code Snippets",
    sub="The most interview-relevant patterns in the codebase.")

story.append(Paragraph(b("DB Connection Decorator"), H2))
story.append(Paragraph("All routes use a @with_db_connection decorator that injects cursor and conn:", Body))
story += code_block("app/utils/database.py",
    ['def with_db_connection(f):',
     '    @wraps(f)',
     '    def decorated(*args, **kwargs):',
     '        conn   = get_connection()   # from config',
     '        cursor = conn.cursor(dictionary=True)',
     '        try:',
     '            return f(cursor, conn, *args, **kwargs)',
     '        finally:',
     '            cursor.close()',
     '            conn.close()',
     '    return decorated'])

story.append(Paragraph(b("Dynamic PK Resolution"), H2))
story.append(Paragraph("Each register table has a different primary key column. We query information_schema to find it:", Body))
story += code_block("row_remark_routes.py",
    ['def _get_pk_column(cursor, table):',
     '    cursor.execute("""',
     '        SELECT COLUMN_NAME FROM information_schema.KEY_COLUMN_USAGE',
     '        WHERE TABLE_NAME=%s AND CONSTRAINT_NAME=\'PRIMARY\'',
     '        LIMIT 1""", (table,))',
     '    row = cursor.fetchone()',
     '    return row["COLUMN_NAME"] if row else "id"'])

story.append(Paragraph(b("Excel Upload Processing"), H2))
story += code_block("data_routes.py — upload_transaction()",
    ['@data_bp.route("/upload_transaction", methods=["POST"])',
     '@with_db_connection',
     'def upload_transaction(cursor, conn):',
     '    file       = request.files["file"]',
     '    table_name = request.form["table_name"]',
     '    df = pd.read_excel(file)',
     '    # Map display labels back to column names',
     '    reverse_map = {v:k for k,v in col_to_label.items()}',
     '    df.rename(columns=reverse_map, inplace=True)',
     '    # Insert rows + create excel_uploads record',
     '    upload_id = create_upload_record(cursor, conn, ...)',
     '    df["upload_id"] = upload_id',
     '    df.to_sql(table_name, conn_alchemy, if_exists="append")'])

story.append(PageBreak())

# ─────────────────────────────────────────────────────
# 9. INTERVIEW Q&A
# ─────────────────────────────────────────────────────
story += section_header("9. Common Interview Questions & Answers")

qa = [
    ("How does the approval workflow work?",
     "Departments upload Excel files. Approvers see them in a queue. They review each row using Accept/Reject toggles. "
     "After reviewing all rows, they click 'Finalize Approval' which calls /api/approve_upload. "
     "If any row is rejected, the upload stays pending. The user is notified and can edit rejected rows and re-request approval."),

    ("Why is a confirmation step needed before bulk approval?",
     "Without it, clicking 'Select All Accept' would immediately lock the upload as Approved. "
     "If the approver then rejected a row, the row would be rejected in the data table but the upload would still show "
     "as Approved in the dashboard — an inconsistent state. The two-step design (mark + finalize) ensures consistency."),

    ("How do you handle dynamic primary keys across different register tables?",
     "Each register table has a different PK column name (e.g. livestock_census_refno). "
     "We query information_schema.KEY_COLUMN_USAGE at runtime to discover the PK column, "
     "then use it dynamically in all UPDATE and DELETE queries."),

    ("How are attachments stored?",
     "As LONGBLOB in MySQL in the tbl_grievance_attachment table. "
     "No filesystem is involved, so the application works identically on any server without directory configuration. "
     "For display, bytes are base64-encoded and sent as JSON — images render in an img tag, PDFs in an iframe."),

    ("How is the permissions system designed?",
     "Permissions are stored in user_permissions (user_id, department, can_view, can_edit, can_download). "
     "Edit is a superset — granting it auto-enables view and download. "
     "GLOBAL overrides apply to all departments not explicitly listed. "
     "The backend checks permissions on every route; the frontend shows/hides buttons accordingly."),

    ("How does the statistics module know register completion?",
     "txn_registry lists all registers per department. For each register, we query excel_uploads "
     "matching department + table_name. If no row exists, status = not_uploaded. "
     "If a row exists, we read status_ (NULL=pending, 1=approved, 0=rejected). "
     "The completion % = approved count / total register count for that department."),

    ("How are grievance ticket numbers generated?",
     "Format: DEP-YYYY-MM-NNNN. DEP = first 3 letters of the submitter's department. "
     "The sequence is per-department per-month, reset each month by counting existing tickets with that prefix. "
     "Example: AGR-2026-03-0001 for the first Animal Husbandry ticket in March 2026."),

    ("How do you prevent the 'Missing table parameter' error on back navigation?",
     "The view_excel_data page uses Jinja2 template variables like {{ table }}. "
     "browser history.back() replays the cached HTML without re-rendering the template, "
     "so {{ table }} appears literally. The fix: goBack() always navigates by role "
     "(/approver_dashboard, /user_dashboard etc.) instead of using history.back()."),
]

for q, a in qa:
    story.append(KeepTogether([
        Paragraph(f"Q: {b(q)}", S("qq", fontName="Helvetica-Bold", fontSize=10, textColor=NAVY, spaceBefore=10, spaceAfter=3)),
        Paragraph(f"A: {a}", S("aa", fontName="Helvetica", fontSize=9.5, textColor=GRAY900, leading=14, spaceAfter=6,
                               leftIndent=12, borderPad=4, backColor=GRAY50)),
    ]))

story.append(PageBreak())

# ── BACK COVER ────────────────────────────────────────
story.append(Spacer(1, 3*cm))
story.append(HRFlowable(width="100%", thickness=2, color=NAVY))
story.append(Spacer(1, 0.5*cm))
story.append(Paragraph("Directorate of Economics and Statistics", S("bc1",fontName="Helvetica-Bold",fontSize=14,textColor=NAVY,alignment=TA_CENTER)))
story.append(Paragraph("Data Management Portal — Technical Documentation", S("bc2",fontName="Helvetica",fontSize=10,textColor=GRAY600,alignment=TA_CENTER,spaceAfter=6)))
story.append(Paragraph("Confidential — For Interview Use Only", S("bc3",fontName="Helvetica-Oblique",fontSize=9,textColor=GRAY600,alignment=TA_CENTER)))
story.append(HRFlowable(width="100%", thickness=1, color=GRAY200))

# ── BUILD ─────────────────────────────────────────────
def add_page_number(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(GRAY600)
    canvas.setFont("Helvetica", 8)
    page_num = canvas.getPageNumber()
    if page_num > 1:
        canvas.drawRightString(W - 2*cm, 1.2*cm, f"Page {page_num}")
        canvas.drawString(2*cm, 1.2*cm, "DES Data Management Portal — Technical Documentation")
        canvas.setStrokeColor(GRAY200)
        canvas.line(2*cm, 1.5*cm, W-2*cm, 1.5*cm)
    canvas.restoreState()


output_path = os.path.join(os.getcwd(), "DES_Portal_Documentation.pdf")
doc = SimpleDocTemplate(
    output_path, pagesize=A4,
    leftMargin=2*cm, rightMargin=2*cm,
    topMargin=2.5*cm, bottomMargin=2.5*cm,
    title="DES Portal Technical Documentation",
    author="DES Development Team"
)
doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
print(f"✅ PDF saved → {output_path}")
