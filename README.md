# 🩸 Smart Blood Bank & Emergency Donor Matching System (CLI)

[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![MySQL 8.0+](https://img.shields.io/badge/MySQL-8.0%2B-orange.svg)](https://www.mysql.com/)
[![Rich CLI](https://img.shields.io/badge/UI-Rich%20Terminal-green.svg)](https://github.com/Textualize/rich)
[![Database Normalization](https://img.shields.io/badge/Normalization-3NF%20%2F%20BCNF-purple.svg)]()
[![ACID Compliant](https://img.shields.io/badge/Transactions-ACID%20InnoDB-red.svg)]()

> A production-grade, terminal-based Database Management System (DBMS) engineered in **Python 3** and **MySQL 8.0+ (InnoDB)**. Designed specifically for an undergraduate Database Management Systems course, replacing generic clichés with a mission-critical healthcare logistics platform enforcing strict transfusion biology rules, FIFO inventory shelf-life tracking, and ACID-compliant transactional blood allocation.

---

## 📋 Table of Contents
1. [System Architecture & High-Level Design](#-system-architecture--high-level-design)
2. [Relational Database Design & Normalization (3NF/BCNF)](#-relational-database-design--normalization-3nfbcnf)
3. [Advanced Database Components (Triggers, Procedures, Views)](#-advanced-database-components)
4. [ACID Transactional Allocation Engine](#-acid-transactional-allocation-engine)
5. [Project File Structure](#-project-file-structure)
6. [Prerequisites & Environment Setup](#-prerequisites--environment-setup)
7. [Database Setup & Migration (Two Methods)](#-database-setup--migration)
8. [Interactive CLI User Manual](#-interactive-cli-user-manual)
9. [Complex Analytical Queries Explained](#-complex-analytical-queries-explained)
10. [Demonstration & Grading Evaluation Script](#-demonstration--grading-evaluation-script)

---

## 🏥 System Architecture & High-Level Design

Blood bank inventory management is fundamentally different from generic inventory systems:
- **Perishable Stock:** Whole blood / Packed Red Blood Cells (RBC) have an inviolable shelf life of **42 days** from collection. Once expired, units are biologically hazardous and must be quarantined.
- **Strict Biological Compatibility:** A patient with Blood Group B+ cannot receive A+ blood. Only compatible blood groups (determined by antigen-antibody serology) can be transfused. O- is the Universal Donor; AB+ is the Universal Recipient.
- **Donor Safety (90-Day Cooldown):** Donors must rest at least 90 days between donations to allow iron reserves and erythrocyte volume to regenerate.
- **Race Condition Prevention:** In mass casualties, multiple trauma centers simultaneously requisition scarce blood (e.g., O-). Allocations must run within strict **ACID transactions** utilizing row-level pessimistic locking (`SELECT ... FOR UPDATE`) with **FIFO (First-In, First-Out)** rotation to prevent double-allocation and reduce expiration spoilage.

```
       +-------------------------------------------------------------+
       |                     Interactive CLI (Rich)                  |
       |        [Blood Bank Admin]        [Hospital Coordinator]      |
       +-------------------------------------------------------------+
                                      |
                      mysql-connector-python (Parameterized)
                                      |
       +-------------------------------------------------------------+
       |                      MySQL 8.0 (InnoDB)                     |
       +-------------------------------------------------------------+
       |  Tables:                                                    |
       |    - blood_group_compatibility (Lookup Matrix 3NF)          |
       |    - hospitals (Health Centers & Trauma Tiers)              |
       |    - donors (Biometrics, Cooldown, Status)                  |
       |    - blood_inventory (Bags, Expiration Dates, Locations)    |
       |    - emergency_requests (Requisitions & Urgencies)          |
       |    - request_allocations (1-to-1 Bag Dispatch Bridge)       |
       |    - donor_audit_log (Regulatory Medical Change Log)        |
       |                                                             |
       |  Triggers:                                                  |
       |    - trg_after_allocation_insert (Sync status & inventory)  |
       |    - trg_donor_status_audit (Regulatory audit logging)      |
       |                                                             |
       |  Stored Procedures:                                         |
       |    - MatchCompatibleDonors(hospital_id, blood_group)        |
       |    - ExpireOldBloodBags(OUT p_expired_count)                |
       |                                                             |
       |  Views:                                                     |
       |    - AvailableBloodStockView (Fresh, unallocated units)     |
       |    - CriticalShortageView (< 3 units threshold alerts)      |
       +-------------------------------------------------------------+
```

---

## 🗄️ Relational Database Design & Normalization (3NF/BCNF)

The schema is rigorously normalized up to **3NF / Boyce-Codd Normal Form (BCNF)** to eliminate data anomalies (insertion, update, and deletion anomalies):

### 1. Proof of Normalization
* **First Normal Form (1NF):**
  * All attributes contain atomic, indivisible values.
  * Every table possesses an unambiguous Primary Key (`donor_id`, `hospital_id`, `bag_id`, `request_id`, etc.).
  * No repeating groups or array columns.
* **Second Normal Form (2NF):**
  * Meets 1NF.
  * No partial functional dependencies on composite candidate keys.
  * In `blood_group_compatibility(donor_group, recipient_group)`, the non-key attribute `is_compatible` is fully dependent on both parts of the primary key.
* **Third Normal Form (3NF) & BCNF:**
  * Meets 2NF.
  * Zero transitive dependencies ($X \to Y$ and $Y \to Z$).
  * Hospital address details reside strictly in `hospitals`, referenced by `emergency_requests` only via Foreign Key `hospital_id`.
  * Donor details reside in `donors`, referenced by `blood_inventory` via `donor_id`.
  * Blood compatibility is isolated into its own matrix table rather than being computed or duplicated inside requisition records.
  * For every functional dependency $X \to Y$, $X$ is a superkey.

### 2. Constraints & Integrity Enforcement
* **Primary & Foreign Keys:** Enforce entity and referential integrity.
* **Referential Actions:**
  * `ON DELETE RESTRICT` on `donors -> blood_inventory` (prevents deletion of donors whose blood is on shelf).
  * `ON DELETE CASCADE` on `donors -> donor_audit_log` (cleans audit trails when a donor is archived).
  * `ON DELETE CASCADE` on `emergency_requests -> request_allocations` (cleans line items if a requisition is cancelled).
* **CHECK Constraints:**
  * `chk_bag_volume`: `volume_ml BETWEEN 350 AND 550` (valid medical blood collection unit).
  * `chk_bag_hemoglobin`: `hemoglobin_g_dl >= 12.0` (minimum safe threshold for donation).
  * `chk_bag_expiry`: `expiry_date >= collection_date`.
  * `chk_units_requested`: `units_requested > 0`.
  * `chk_units_allocated`: `units_allocated <= units_requested`.
* **ENUM Types:**
  * Blood groups: `'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'`
  * Bag Status: `'Available', 'Allocated', 'Transfused', 'Expired', 'Discarded'`
  * Urgency Levels: `'CRITICAL', 'HIGH', 'MEDIUM', 'ROUTINE'`
  * Request Status: `'Pending', 'Partially Fulfilled', 'Fulfilled', 'Cancelled'`

---

## ⚡ Advanced Database Components

### 1. Triggers
* **Trigger 1: `trg_after_allocation_insert`**
  * **Event:** `AFTER INSERT ON request_allocations`
  * **Business Rule:** Whenever a blood bag is allocated to a hospital request, this trigger automatically:
    1. Updates `blood_inventory.status = 'Allocated'` for the bag.
    2. Increments `emergency_requests.units_allocated`.
    3. Checks if `units_allocated >= units_requested`; if so, sets `status = 'Fulfilled'` and timestamps `completion_date = NOW()`. Otherwise, sets `status = 'Partially Fulfilled'`.
  * **Safeguard Companion:** `trg_after_allocation_delete` safely reverses the allocation if an allocation record is deleted/cancelled, returning the bag status to `'Available'`.
* **Trigger 2: `trg_donor_status_audit`**
  * **Event:** `AFTER UPDATE ON donors`
  * **Business Rule:** Monitors changes to `eligibility_status` or `medical_screening_notes`.
  * **Action:** Automatically records `old_eligibility_status`, `new_eligibility_status`, `old_medical_notes`, `new_medical_notes`, user identity (`CURRENT_USER()`), and timestamp in `donor_audit_log`.

### 2. Stored Procedures
* **Procedure 1: `MatchCompatibleDonors(IN p_hospital_id INT, IN p_required_blood_group VARCHAR(5))`**
  * Retrieves the requesting hospital's city.
  * Joins `donors` with `blood_group_compatibility` where `is_compatible = TRUE`.
  * Filters for `eligibility_status = 'Eligible'`.
  * Enforces cooldown: `last_donation_date IS NULL OR DATEDIFF(CURRENT_DATE(), last_donation_date) >= 90`.
  * Sorts donors prioritizing local candidates in the same city (`d.city = h.city`), followed by days since donation and total lifetime donations.
* **Procedure 2: `ExpireOldBloodBags(OUT p_expired_count INT)`**
  * Evaluates all blood bags where `status = 'Available'` and `expiry_date < CURRENT_DATE()`.
  * Executes bulk status transition to `'Expired'`.
  * Stores the affected row count in `p_expired_count` and outputs the dataset of expired units for audit review.

### 3. Views
* **View 1: `AvailableBloodStockView`**
  * Displays non-expired, unallocated blood units ready for immediate transfusion.
  * Aggregates by `blood_group`: total units available, total volume in mL, oldest collection date, earliest expiry date, and days until next expiration.
* **View 2: `CriticalShortageView`**
  * Emergency preparedness monitor for blood groups with **fewer than 3 available units**.
  * Employs an exhaustive domain union of all 8 blood groups `LEFT JOIN`ed with `AvailableBloodStockView`. This guarantees that blood types with **0 units in stock** are not dropped by `GROUP BY`, but instead displayed prominently with `'CRITICAL (EMPTY)'` status and calculated deficit units.

---

## 🔒 ACID Transactional Allocation Engine

When allocating blood bags in `main.py`, standard auto-commit is disabled (`conn.autocommit = False`) to enforce full ACID properties:

1. **Atomicity:** The entire allocation (locking candidate bags, creating allocation records, updating inventory statuses, and marking requisition fulfillment) either succeeds completely or rolls back entirely without orphaned updates.
2. **Consistency:** Database check constraints (`units_allocated <= units_requested`, `volume_ml BETWEEN 350 AND 550`) and foreign keys prevent invalid states.
3. **Isolation (Pessimistic Concurrency Control):**
   * Executes `SELECT ... FOR UPDATE` on candidate bags matching the compatibility matrix:
     ```sql
     SELECT bag_id, bag_code, blood_group, expiry_date, storage_location
     FROM blood_inventory
     WHERE blood_group IN (%s, ...)
       AND status = 'Available'
       AND expiry_date >= CURRENT_DATE()
     ORDER BY expiry_date ASC, collection_date ASC
     LIMIT %s
     FOR UPDATE;
     ```
   * **FIFO Rotation:** Oldest non-expired bags are selected first to prevent expiration wastage.
   * **Row-Level Locking:** Locks candidate rows at the InnoDB storage engine level, preventing race conditions where two hospital dispatchers could claim the same blood bag simultaneously.
4. **Durability:** Changes are committed to the InnoDB Write-Ahead Log (WAL) and disk tablespace upon `conn.commit()`.

---

## 📁 Project File Structure

```
smart-blood-bank/
│
├── schema.sql           # Complete DDL: Database creation, Tables, PKs, FKs, CHECK constraints, ENUMs, Indexes
├── seed.sql             # Realistic DML: Compatibility matrix (64 rows), Hospitals, Donors, Inventory, Requests
├── advanced_db.sql      # Procedural SQL: 2 Triggers, 2 Stored Procedures, 2 Analytical Views
├── db_config.py         # Database connection manager with context managers, pooling, and exception handling
├── init_db.py           # Automated Python database migrator (handles DELIMITER blocks & multi-statement scripts)
├── main.py              # Interactive, role-based terminal application (Rich UI, parameterization, ACID engine)
├── requirements.txt     # Python package dependencies (mysql-connector-python, rich, python-dotenv)
├── .env.example         # Template for MySQL credentials and port configuration
└── README.md            # Comprehensive project documentation & evaluation guide
```

---

## 🚀 Prerequisites & Environment Setup

### 1. Requirements
* **Python:** Version 3.9 or higher
* **MySQL Server:** Version 8.0 or higher (or MariaDB 10.5+)

### 2. Python Environment Installation
Open your terminal in the project directory:

```bash
# Optional: Create and activate virtual environment
python -m venv venv

# Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# Linux / macOS:
source venv/bin/activate

# Install required dependencies
pip install -r requirements.txt
```

### 3. Database Credentials Configuration
Copy `.env.example` to `.env` and fill in your MySQL root/user password:

```bash
cp .env.example .env
```

Edit `.env`:
```ini
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_actual_mysql_password
DB_NAME=smart_blood_bank
```

---

## 💾 Database Setup & Migration

You can initialize the database using either the **Automated Python Migrator** or the **Native MySQL CLI**:

### Method A: Automated Python Migrator (Recommended)
This script automatically connects to your MySQL server, creates the `smart_blood_bank` database, correctly parses `DELIMITER $$` procedural blocks, executes all 3 SQL scripts, and prints a summary catalog table:

```bash
python init_db.py
```

### Method B: Native MySQL Command-Line Client
If you prefer running via the standard MySQL terminal client:

```bash
# 1. Import Schema (DDL)
mysql -u root -p < schema.sql

# 2. Import Seed Data (DML)
mysql -u root -p < seed.sql

# 3. Import Advanced Procedural Logic (Triggers, Procedures, Views)
mysql -u root -p < advanced_db.sql
```

---

## 🖥️ Interactive CLI User Manual

Launch the terminal application:

```bash
python main.py
```

### Main Menu Navigation:
```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃      🩸 SMART BLOOD BANK & EMERGENCY DONOR MATCHING SYSTEM      ┃
┃   Healthcare Logistics & ACID Allocation Engine | DBMS Project  ┃
┃         Connected DB: smart_blood_bank @ localhost:3306         ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

 ╭────────────────────── MAIN SYSTEM PORTAL ──────────────────────╮
 │                                                                │
 │  [1] Blood Bank Administrator Panel                            │
 │  [2] Hospital Emergency Coordinator Portal                     │
 │  [3] Analytical Intelligence & SQL Reports Hub                 │
 │  [4] System Diagnostics & Database Health                      │
 │  [5] Run Database Migration / Reset (schema, seed, advanced)   │
 │  [0] Exit Application                                          │
 │                                                                │
 ╰────────────────────────────────────────────────────────────────╯
```

### Role 1: Blood Bank Administrator
1. **Register New Blood Donor:** Input legal name, NID, gender, age validation (>= 17 years), blood group, contact info, and medical notes.
2. **Check 90-Day Cooldown & Record Blood Donation:**
   * Enter Donor ID or Phone number.
   * The system automatically computes `(CURRENT_DATE - last_donation_date)`.
   * If < 90 days, rejects donation and displays exact days remaining in cooldown.
   * If eligible, prompts for collection volume, tests minimum hemoglobin (>= 12.0 g/dL), auto-calculates 42-day expiration date, assigns unique barcode, updates donor lifetime count, and shelves the bag.
3. **Update Donor Medical Status:**
   * Modify eligibility (e.g., defer a donor due to low iron).
   * Automatically fires the database trigger `trg_donor_status_audit` and displays the generated audit entry.
4. **Live Inventory Dashboard:** Color-coded table displaying all blood bags with status badges (Green = healthy, Yellow = expiring <= 7 days, Red = expired, Cyan = allocated).
5. **Run Expiry Maintenance:** Calls stored procedure `ExpireOldBloodBags()`, transitions past-due units, and outputs an audit table of expired stock.

### Role 2: Hospital Emergency Coordinator
1. **Submit Emergency Requisition:** Select requesting hospital, patient case ID, required blood group, units needed, and urgency level (`CRITICAL`, `HIGH`, `MEDIUM`, `ROUTINE`).
2. **Real-Time ACID Blood Bag Allocation:**
   * Displays pending emergency requisitions ordered by urgency and deadline.
   * Select a requisition ID.
   * Executes atomic FIFO query with `SELECT ... FOR UPDATE`.
   * Previews candidate blood bags.
   * Confirms transaction: inserts allocation records, fires trigger `trg_after_allocation_insert` to update inventory status, commits transaction, or executes clean rollback on rejection.
3. **Smart Compatible Donor Matchmaker:**
   * Calls stored procedure `MatchCompatibleDonors(hospital_id, blood_group)`.
   * Identifies eligible donors whose 90-day cooldown has passed, prioritizing local donors in the same city.
4. **View Available Blood Stock View:** Real-time summary of fresh, unallocated units grouped by blood group.
5. **View Dispatch & Allocation History:** Complete dispatch ledger showing donor-to-recipient blood transfusions.

---

## 📊 Complex Analytical Queries Explained

To satisfy undergraduate DBMS course criteria for complex query design, the system features queries demonstrating multiple advanced SQL constructs:

### Query 1: Hospital Demand vs. Fulfillment Report
* **Techniques:** `LEFT JOIN`, `GROUP BY`, `COALESCE`, `NULLIF`, `SUM(CASE ...)`, Arithmetic Aggregations.
* **SQL:**
```sql
SELECT 
    h.hospital_id,
    h.hospital_code,
    h.name AS hospital_name,
    h.city,
    h.urgency_tier,
    COUNT(er.request_id) AS total_requests,
    COALESCE(SUM(er.units_requested), 0) AS total_units_requested,
    COALESCE(SUM(er.units_allocated), 0) AS total_units_allocated,
    ROUND(
        (COALESCE(SUM(er.units_allocated), 0) / NULLIF(SUM(er.units_requested), 0)) * 100, 
        1
    ) AS fulfillment_rate_pct,
    SUM(CASE WHEN er.status = 'Pending' THEN 1 ELSE 0 END) AS pending_requests,
    SUM(CASE WHEN er.status = 'Fulfilled' THEN 1 ELSE 0 END) AS fulfilled_requests
FROM hospitals h
LEFT JOIN emergency_requests er ON h.hospital_id = er.hospital_id
GROUP BY h.hospital_id, h.hospital_code, h.name, h.city, h.urgency_tier
ORDER BY total_units_requested DESC, h.name ASC;
```
* **Explanation:** Evaluates healthcare logistics performance across all partner hospitals, even those with zero historical requisitions (`LEFT JOIN`), while safeguarding against division-by-zero errors via `NULLIF`.

### Query 2: Top Regular Donors Leaderboard
* **Techniques:** Uncorrelated Subquery inside `HAVING` clause, Aggregate functions, Multi-table Join.
* **SQL:**
```sql
SELECT 
    d.donor_id,
    d.full_name,
    d.blood_group,
    d.city,
    d.total_donations,
    COUNT(bi.bag_id) AS recorded_units_on_shelf,
    COALESCE(SUM(bi.volume_ml), 0) AS total_ml_on_shelf,
    (d.total_donations * 3) AS estimated_lives_saved
FROM donors d
LEFT JOIN blood_inventory bi ON d.donor_id = bi.donor_id
GROUP BY d.donor_id, d.full_name, d.blood_group, d.city, d.total_donations
HAVING d.total_donations >= (
    SELECT AVG(total_donations) FROM donors
)
ORDER BY d.total_donations DESC, estimated_lives_saved DESC;
```
* **Explanation:** Dynamically calculates fleet-wide average donations using an aggregate subquery inside the `HAVING` clause, ranking only donors meeting or exceeding the average threshold.

---

## 🧪 Demonstration & Grading Evaluation Script

Follow this step-by-step sequence during a live course demonstration:

1. **Database Verification:**
   * Run `python main.py` -> Option `[4]` (System Diagnostics) to confirm active connection and schema health.
2. **Demonstrate 90-Day Cooldown Protection:**
   * Go to `[1]` (Admin Panel) -> `[2]` (Check Cooldown & Donate).
   * Search for Donor ID `4` (Sophia Lin).
   * Observe: The CLI displays **"90-DAY COOLDOWN RESTRICTION ACTIVE"** (donated 25 days ago; 65 days remaining).
   * Search for Donor ID `1` (Jonathan Doe - donated 125 days ago).
   * Observe: Cooldown satisfied. Proceed to record donation; watch the system automatically assign a 42-day expiry date and generate unique barcode.
3. **Demonstrate Database Audit Trigger:**
   * Go to `[1]` (Admin Panel) -> `[3]` (Update Donor Medical Status).
   * Select Donor ID `1`. Change status from `Eligible` to `Temporarily Ineligible` with reason `"Dental surgery antibiotics"`.
   * Observe: Trigger `trg_donor_status_audit` immediately fires and the generated `donor_audit_log` row is printed.
4. **Demonstrate Stored Procedure for Expiration Tracking:**
   * Go to `[1]` (Admin Panel) -> `[6]` (Run Expiry Check Stored Procedure).
   * Observe: `ExpireOldBloodBags()` executes, transitions past-due units (`BB-NY-2026-004`, `BB-CHI-2026-007`), and prints the newly flagged expired units.
5. **Demonstrate ACID FIFO Allocation Engine:**
   * Go to `[2]` (Coordinator Portal) -> `[2]` (Real-Time ACID Blood Bag Allocation).
   * Select Request ID `2` (Northwestern Memorial Hospital, needing 3 units of A+).
   * Notice that the engine matches both A+ and compatible universal O- bags, sorts by `expiry_date ASC` (FIFO), and locks them with `SELECT ... FOR UPDATE`.
   * Confirm the commit.
   * Observe: Trigger `trg_after_allocation_insert` fires, marking bags as `Allocated` and advancing the request status.
6. **Demonstrate Complex Views & Reports:**
   * Go to `[3]` (Analytics Hub) -> `[3]` (Critical Stock Shortage Monitor).
   * Observe: Even blood types with 0 units available appear clearly in `CriticalShortageView` with `CRITICAL (EMPTY)` alert and deficit unit counts.
   * Go to `[3]` -> `[1]` (Hospital Fulfillment Report) to show `LEFT JOIN` and `GROUP BY` analytics.

---

## 🛡️ Security & Engineering Best Practices
* **SQL Injection Prevention:** 100% of user queries in Python utilize parameterized queries (`%s`). Zero raw string concatenation.
* **Exception Resilience:** All database calls are wrapped in `mysql.connector.Error` handlers; the CLI never crashes on constraint violations or duplicate keys.
* **Resource Cleanup:** Context managers (`@contextmanager`) ensure database connections and cursors are properly closed under all circumstances.

---

**Developed for Academic Excellence in Database Management Systems (DBMS).**
