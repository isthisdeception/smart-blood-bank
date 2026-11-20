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
11. [নতুনদের জন্য বাংলায় স্টেপ-বাই-স্টেপ গাইড (Bangla Beginner Guide)](#-নতুনদের-জন্য-বাংলায়-স্টেপ-বাই-স্টেপ-গাইড-bangla-beginner-guide)

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

## 🇧🇩 নতুনদের জন্য বাংলায় বিস্তারিত ও পুঙ্খানুপুঙ্খ গাইড (In-Depth Bangla Beginner Guide)

আপনি যদি ডাটাবেস বা পাইথনে একদম নতুন হন এবং নিজের ল্যাপটপে এই প্রজেক্টটি ডাউনলোড করে **শূন্য থেকে চালু, টেস্ট ও বুঝতে চান**, তবে এই সেকশনটি আপনার জন্যই। এখানে প্রতিটি ধাপ এতোটাই বিস্তারিতভাবে লেখা হয়েছে যাতে আপনি কোনো সমস্যায় না পড়েন।

---

### 📑 সূচিপত্র (Bangla Guide Index)
1. [প্রজেক্টের মূল দর্শন ও বাস্তব উপযোগিতা](#১-প্রজেক্টের-মূল-দর্শন-ও-বাস্তব-উপযোগিতা)
2. [ল্যাপটপে প্রয়োজনীয় সফটওয়্যার প্রস্তুতকরণ (Step 0: Prerequisites)](#২-ল্যাপটপে-প্রয়োজনীয়-সফটওয়্যার-প্রস্তুতকরণ)
3. [ধাপ ১: প্রজেক্ট ল্যাপটপে নামানো (Download / Clone)](#৩-ধাপ-১-প্রজেক্ট-ল্যাপটপে-নামানো)
4. [ধাপ ২: প্রজেক্ট ফোল্ডারে টার্মিনাল চালু ও ডিপেন্ডেন্সি ইনস্টলেশন](#৪-ধাপ-২-টার্মিনাল-চালু-ও-ডিপেন্ডেন্সি-ইনস্টলেশন)
5. [ধাপ ৩: ডাটাবেস ক্রেডেনশিয়াল ও .env ফাইল কনফিগারেশন](#৫-ধাপ-৩-ডাটাবেস-ক্রেডেনশিয়াল-ও-env-ফাইল-কনফিগারেশন)
6. [ধাপ ৪: এক ক্লিকে ডাটাবেস মাইগ্রেশন স্ক্রিপ্ট চালানো (init_db.py)](#৬-ধাপ-৪-এক-ক্লিকে-ডাটাবেস-মাইগ্রেশন-চালানো)
7. [ধাপ ৫: মূল অ্যাপ্লিকেশন চালু করা (main.py)](#৭-ধাপ-৫-মূল-অ্যাপ্লিকেশন-চালু-করা)
8. [ধাপ ৬: প্রতিটি মেনু ও ফিচারের পুঙ্খানুপুঙ্খ টেস্ট স্ক্রিপ্ট](#৮-ধাপ-৬-প্রতিটি-মেনু-ও-ফিচারের-পুঙ্খানুপুঙ্খ-টেস্ট-স্ক্রিপ্ট)
9. [প্রজেক্টের ফাইল পরিচিতি ও ইন্টারনাল আর্কিটেকচার](#৯-প্রজেক্টের-ফাইল-পরিচিতি-ও-ইন্টারনাল-আর্কিটেকচার)
10. [সম্ভাব্য সকল সমস্যা ও তাৎক্ষণিক সমাধান (Troubleshooting Encyclopedia)](#১০-সম্ভাব্য-সকল-সমস্যা-ও-তাৎক্ষণিক-সমাধান)
11. [পরীক্ষক / ভাইভা বোর্ডের জন্য টেকনিক্যাল প্রশ্নোত্তর](#১১-পরীক্ষক--ভাইভা-বোর্ডের-জন্য-টেকনিক্যাল-প্রশ্নোত্তর)

---

### ১. প্রজেক্টের মূল দর্শন ও বাস্তব উপযোগিতা

বিশ্ববিদ্যালয়ের DBMS কোর্সে সাধারণত ছাত্রছাত্রীরা সাধারণ লাইব্রেরি ম্যানেজমেন্ট বা স্টুডেন্ট ম্যানেজমেন্ট প্রজেক্ট জমা দেয় যা খুবই গতানুগতিক। এই প্রজেক্টটি তৈরি করা হয়েছে **বাস্তব জীবনের ব্লাড ব্যাংক ও ট্রমা সেন্টারের জরুরি লজিস্টিকস** সমাধানের জন্য:

* **রক্তের মেয়াদ ৪২ দিন (Perishable Shelf-Life):** মানুষের রক্তের লোহিত কণিকা (Packed Red Blood Cells) সংরক্ষণের সর্বোচ্চ মেয়াদ ৪২ দিন। ৪২ দিন পার হলে সেই রক্ত আর রোগীর শরীরে দেওয়া যায় না—তা স্বয়ংক্রিয়ভাবে `Expired` হিসেবে আলাদা করতে হয়।
* **রক্তের গ্রুপের সামঞ্জস্যতা (Transfusion Biology):** ভুল গ্রুপের রক্ত দিলে রোগী মারা যেতে পারে। তাই ডাটাবেসে চিকিৎসাবিজ্ঞানসম্মত ৬৪ জোড়া রক্তের গ্রুপ ম্যাট্রিক্স রয়েছে (যেমন: `O-` সর্বজনীন দাতা এবং `AB+` সর্বজনীন গ্রহীতা)।
* **রক্তদাতার ৯০ দিনের কুলডাউন (Donor Safety Cooldown):** একজন রক্তদাতা একবার রক্ত দিলে তার শরীরের আয়রন ও রক্তকণিকা পূরণ হতে ন্যূনতম ৯০ দিন বিশ্রাম প্রয়োজন। সিস্টেম স্বয়ংক্রিয়ভাবে এটি হিসাব করে ৯০ দিনের আগে রক্তদান আটকে দেয়।
* **কনকারেন্ট রিকুয়েস্ট ও রেস কন্ডিশন রোধ (ACID Transaction):** যখন একই সাথে দুটি ভিন্ন হাসপাতাল দুর্লভ গ্রুপের (যেমন `O-`) রক্তের জন্য আবেদন করে, তখন যেন একই ব্যাগ দুটি ভিন্ন হাসপাতালে বরাদ্দ না হয়ে যায়, সেজন্য MySQL InnoDB-এর **`SELECT ... FOR UPDATE`** রো-লেভেল পেসিমিস্টিক লকিং এবং **FIFO (First-In, First-Out)** ব্যবহার করা হয়েছে।

---

### ২. ল্যাপটপে প্রয়োজনীয় সফটওয়্যার প্রস্তুতকরণ

প্রজেক্টটি চালানোর জন্য আপনার ল্যাপটপে মাত্র ২টি সফটওয়্যার প্রয়োজন:

#### ক) Python ইনস্টল করা (Version 3.9 বা তার বেশি):
1. ব্রাউজারে যান: [https://www.python.org/downloads/](https://www.python.org/downloads/)
2. হলুদ রঙের **"Download Python 3.xx"** বাটনে ক্লিক করে ইনস্টলার ফাইল নামান।
3. ডাউনলোড করা ফাইলে ডাবল ক্লিক করে ইনস্টলেশন শুরু করুন।
4. ⚠️ **সবচেয়ে গুরুত্বপূর্ণ ধাপ:** ইনস্টলার উইন্ডোর একদম নিচে থাকা **"Add python.exe to PATH"** বক্সে টিক চিহ্ন দিন! (যদি টিক না দেন, তবে টার্মিনালে পাইথন কমান্ড কাজ করবে না)।
5. এরপর **"Install Now"**-এ ক্লিক করে ফিনিশ করুন।
6. **যাচাই:** আপনার ল্যাপটপের PowerShell বা Command Prompt খুলে লিখুন:
   ```powershell
   python --version
   ```
   যদি `Python 3.11.x` বা অনুরূপ দেখায়, তবে পাইথন প্রস্তুত!

#### খ) MySQL Server প্রস্তুত করা (যেকোনো ১টি উপায় বেছে নিন):

* **উপায় ১ (সবচেয়ে সহজ - XAMPP ব্যবহারকারীদের জন্য):**
  - আপনার ল্যাপটপে যদি [XAMPP](https://www.apachefriends.org/) ইনস্টল থাকে, তবে **XAMPP Control Panel** ওপেন করুন।
  - **MySQL**-এর ডান পাশে থাকা **"Start"** বাটনে ক্লিক করুন। সার্ভিস চালু হলে সবুজ রঙ ধারণ করবে এবং পোর্ট `3306` দেখাবে। (XAMPP-তে ডিফল্ট ইউজার `root` থাকে এবং কোনো পাসওয়ার্ড থাকে না)।
* **উপায় ২ (MySQL Community Server & Workbench):**
  - [MySQL Installer](https://dev.mysql.com/downloads/installer/) ডাউনলোড করে ইনস্টল করুন।
  - ইনস্টলের সময় `root` ইউজারের যে পাসওয়ার্ডটি আপনি নিজে দিয়েছেন, সেটি কোথাও লিখে রাখুন।
  - **যাচাই:** Windows Search-এ `Services` লিখে এন্টার দিন। তালিকায় `MySQL80` খুঁজে দেখুন স্ট্যাটাস `Running` আছে কি না।

---

### ৩. ধাপ ১: প্রজেক্ট ল্যাপটপে নামানো

যেকোনো একটি পদ্ধতিতে প্রজেক্টের ফাইলগুলো আপনার ল্যাপটপে আনুন:

#### অপশন ১ (Git ব্যবহার করে - রিকমেন্ডেড):
আপনার পছন্দের ড্রাইভে (যেমন `D:\Coding` বা `C:\Users\YourName\Documents`) গিয়ে PowerShell ওপেন করুন এবং লিখুন:
```bash
git clone https://github.com/isthisdeception/smart-blood-bank.git
cd smart-blood-bank
```

#### অপশন ২ (ZIP ডাউনলোড করে):
1. ব্রাউজারে যান: [https://github.com/isthisdeception/smart-blood-bank](https://github.com/isthisdeception/smart-blood-bank)
2. সবুজ রঙের **`<> Code`** বাটনে ক্লিক করে **`Download ZIP`** চাপুন।
3. ডাউনলোড করা `smart-blood-bank-main.zip` ফাইলটি Right-Click করে **Extract All...** করুন।
4. এক্সট্র্যাক্ট করা ফোল্ডারের ভেতরে ঢুকুন।

---

### ৪. ধাপ ২: টার্মিনাল চালু ও ডিপেন্ডেন্সি ইনস্টলেশন

1. প্রজেক্ট ফোল্ডারে থাকা অবস্থায়:
   - উইন্ডোজ এক্সপ্লোরারের ওপরের অ্যাড্রেস বারে ক্লিক করে `powershell` অথবা `cmd` লিখে **Enter** চাপুন।
   - অথবা ফোল্ডারের ফাঁকা জায়গায় `Shift` চেপে ধরে মাউসের Right-Click করে **"Open PowerShell window here"** সিলেক্ট করুন।
   - অথবা VS Code-এ ফোল্ডারটি ওপেন করে `Ctrl + ~` চেপে টার্মিনাল খুলুন।

2. **(ঐচ্ছিক কিন্তু স্ট্যান্ডার্ড) ভার্চুয়াল এনভায়রনমেন্ট তৈরি ও সক্রিয়করণ:**
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```
   *(যদি PowerShell-এ স্ক্রিপ্ট রান রেস্ট্রিকশন এরর দেয়, তবে সাধারণ কমান্ড প্রম্পট ব্যবহার করুন অথবা সরাসরি পরের ধাপে চলে যান।)*

3. **প্যাকেজগুলো ইনস্টল করুন:**
   ```powershell
   python -m pip install -r requirements.txt
   ```
   *এটি `mysql-connector-python`, `rich` (রঙিন টার্মিনাল UI-র জন্য), এবং `python-dotenv` প্যাকেজগুলো ইনস্টল করে দেবে।*

---

### ৫. ধাপ ৩: ডাটাবেস ক্রেডেনশিয়াল ও .env ফাইল কনফিগারেশন

ডাটাবেসের সাথে পাইথনের সংযোগ ঘটাতে `.env` ফাইল কনফিগার করতে হবে:

1. প্রজেক্টের ভেতর `.env.example` নামে একটি ফাইল রয়েছে। 
2. টার্মিনালে নিচের কমান্ডটি দিয়ে সেটিকে `.env` নামে কপি করুন:
   ```powershell
   cp .env.example .env
   ```
   *(অথবা ফাইলে রাইট ক্লিক করে কপি করে পেস্ট করে নাম দিন `.env`)*

3. এবার যেকোনো টেক্সট এডিটর (Notepad বা VS Code) দিয়ে `.env` ফাইলটি খুলুন:

   ```ini
   DB_HOST=localhost
   DB_PORT=3306
   DB_USER=root
   DB_PASSWORD=আপনার_ল্যাপটপের_mysql_পাসওয়ার্ড
   DB_NAME=smart_blood_bank
   ```

   * **যদি আপনি XAMPP ব্যবহার করেন:** পাসওয়ার্ড ফাঁকা রাখুন, অর্থাৎ: `DB_PASSWORD=`
   * **যদি আপনি MySQL Workbench / Server ইনস্টল করে থাকেন:** ইনস্টলেশনের সময় আপনি যে রুট পাসওয়ার্ড দিয়েছিলেন (যেমন: `root` বা `1234` বা আপনার নিজস্ব পাসওয়ার্ড), সেটি লিখুন: `DB_PASSWORD=your_password`
4. ফাইলটি সেভ (`Ctrl + S`) করে বন্ধ করুন।

---

### ৬. ধাপ ৪: এক ক্লিকে ডাটাবেস মাইগ্রেশন চালানো (init_db.py)

ম্যানুয়ালি কোনো কুয়েরি লেখা বা MySQL-এ ঢুকে টেবিল বানানোর ঝামেলা নেই! টার্মিনালে শুধু লিখুন:

```powershell
python init_db.py
```

**এই স্ক্রিপ্টটি চলার সময় আপনি স্ক্রিনে কী দেখতে পাবেন?**
- এটি নিজে থেকেই MySQL সার্ভারে কানেক্ট হয়ে `smart_blood_bank` ডাটাবেস তৈরি করবে।
- `schema.sql` ফাইলটি পড়ে ৭টি টেবিল, ফরেন কি, চেক কনস্ট্রেইন্ট এবং ইনডেক্স তৈরি করবে।
- `seed.sql` পড়ে চিকিৎসাবিজ্ঞানসম্মত ৬৪ জোড়া ব্লাড গ্রুপ ম্যাট্রিক্স, ৬টি বড় হাসপাতাল, ১২ জন রক্তদাতা এবং রক্তভাণ্ডারের ডামি ডাটা লোড করবে।
- `advanced_db.sql` পড়ে ২টি ডাটাবেস ট্রিগার, ২টি স্টোরড প্রসিডিউর এবং ২টি স্পেশাল ভিউ কম্পাইল করবে।
- সবশেষে স্ক্রিনে একটি সুন্দর টেবিল দেখাবে যেখানে কোন টেবিলে কয়টি রো তৈরি হয়েছে তার হিসেব চলে আসবে!

---

### ৭. ধাপ ৫: মূল অ্যাপ্লিকেশন চালু করা (main.py)

সব সেটআপ শেষ! এবার অ্যাপ্লিকেশনটি রান করুন:

```powershell
python main.py
```

টার্মিনালে সুন্দর ব্যানারের সাথে প্রধান মেনু স্ক্রিন আসবে:
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

---

### ৮. ধাপ ৬: প্রতিটি মেনু ও ফিচারের পুঙ্খানুপুঙ্খ টেস্ট স্ক্রিপ্ট

পরীক্ষক, শিক্ষক বা নিজে প্রজেক্টের প্রতিটি ফিচার যাচাই করতে নিচের ধাপগুলো ট্রাই করুন:

#### ১. রক্তদাতার ৯০ দিনের কুলডাউন সুরক্ষা টেস্ট (Admin Panel):
1. মেইন মেনু থেকে `1` চেপে **Blood Bank Administrator Panel**-এ যান।
2. এরপর `2` চেপে **Check 90-Day Cooldown & Record Blood Donation** সিলেক্ট করুন।
3. **টেস্ট কেস ক (নিষিদ্ধ দাতা):** রক্তদাতার আইডি হিসেবে লিখুন `4` (Sophia Lin)।
   - *ফলাফল:* সিস্টেম লাল ব্যানারে দেখাবে **"⏳ 90-DAY COOLDOWN RESTRICTION ACTIVE"**। সে ২৫ দিন আগে রক্ত দিয়েছিল, এখনও তার ৬৫ দিন বাকি। রক্তদান স্বয়ংক্রিয়ভাবে ব্লক হয়ে যাবে!
4. **টেস্ট কেস খ (অনুমোদিত দাতা):** এবার আইডি হিসেবে লিখুন `1` (Jonathan Doe)।
   - *ফলাফল:* সিস্টেম সবুজ কালিতে বলবে **"✓ 90-Day Cooldown Satisfied"** (১২৫ দিন আগে রক্ত দিয়েছিল)।
   - প্রসিড করতে `y` চাপুন। রক্তের ভলিউম (যেমন `450` mL), হিমোগ্লোবিন (যেমন `14.5` g/dL) দিন।
   - সিস্টেম স্বয়ংক্রিয়ভাবে আজকের তারিখ থেকে ৪২ দিন যোগ করে এক্সপায়ার ডেট বের করবে এবং ইউনিক বারকোড জেনারেট করে রক্তভাণ্ডারে যুক্ত করবে।

#### ২. ডাটাবেস ট্রিগার টেস্ট (Admin Panel -> Option 3):
1. Admin Panel-এ থাকা অবস্থায় `3` (Update Donor Medical Status) সিলেক্ট করুন।
2. Donor ID দিন `1`।
3. তার বর্তমান স্ট্যাটাস `Eligible` থেকে পরিবর্তন করে দিন `Temporarily Ineligible`।
4. স্ক্রিনিং নোট হিসেবে লিখুন: `Low hemoglobin; prescribed iron supplements`।
5. এন্টার চাপার সাথে সাথে ডাটাবেসের **`trg_donor_status_audit`** ট্রিগারটি স্বয়ংক্রিয়ভাবে ব্যাকগ্রাউন্ডে ফায়ার করবে!
6. টার্মিনালে দেখুন বেগুনি রঙের **"Generated Audit Log Entry (Trigger Verified)"** টেবিল প্রিন্ট হয়েছে, যা প্রমাণ করে ট্রিগার সফলভাবে অডিট টেবিলে পূর্বের এবং নতুন স্ট্যাটাস সেভ করেছে।

#### ৩. এক্সপায়ারি চেকার স্টোরড প্রসিডিউর টেস্ট (Admin Panel -> Option 6):
1. Admin Panel থেকে `6` চাপুন।
2. সিস্টেম MySQL-এর **`ExpireOldBloodBags(@expired_count)`** স্টোরড প্রসিডিউরটি কল করবে।
3. এটি ডাটাবেসের যেসব রক্তের ব্যাগের মেয়াদ শেষ হয়ে গেছে সেগুলোকে এক ক্লিকে চিহ্নিত করে স্ট্যাটাস `Expired` করে দেবে এবং স্ক্রিনে লাল কালিতে সেই রক্ত ব্যাগগুলোর তালিকা ডিসপ্লে করবে।

#### ৪. হাসপাতালের জরুরি রক্ত রিকুয়েস্ট ও ACID ট্রানজ্যাকশন (Coordinator Portal):
1. মেইন মেনুতে ফিরে গিয়ে `2` চেপে **Hospital Emergency Coordinator Portal**-এ যান।
2. রিকুয়েস্ট দেখতে ও রক্ত বরাদ্দ করতে `2` (Real-Time ACID Blood Bag Allocation) চাপুন।
3. পেন্ডিং রিকুয়েস্ট তালিকায় দেখুন **Request ID 2** (Northwestern Memorial Hospital, ৩ ইউনিট A+ রক্ত প্রয়োজন)।
4. আইডি দিন `2` এবং ডিসপ্যাচার নাম লিখুন।
5. **ম্যাজিক দেখুন:**
   - সিস্টেম রক্ত সামঞ্জস্যতা টেবিল ব্যবহার করে A+ রোগীর জন্য A+ এবং ইউনিভার্সাল O- ব্যাগ খুঁজবে।
   - এটি **FIFO (First-In, First-Out)** পদ্ধতিতে সবচেয়ে পুরোনো মেয়াদযুক্ত ব্যাগ আগে আনবে যাতে হাসপাতালে আগে থাকা রক্ত আগে খরচ হয়।
   - MySQL-এ `SELECT ... FOR UPDATE` দিয়ে ওই ব্যাগগুলোকে রো-লেভেলে লক করে রাখবে যাতে অন্য কোনো হাসপাতাল একই সময়ে এই ব্যাগ বরাদ্দ না করতে পারে!
6. আপনি `y` চাপলে ট্রানজ্যাকশন **`COMMIT`** হবে এবং ডাটাবেস ট্রিগার **`trg_after_allocation_insert`** নিজে থেকেই ব্যাগের স্ট্যাটাস `Allocated` বানিয়ে দেবে।

#### ৫. অ্যাডভান্সড এসকিউএল রিপোর্ট দেখা (Analytics Hub):
মেইন মেনু থেকে `3` চেপে **Analytical Intelligence & SQL Reports Hub**-এ যান:
- `1` চাপলে দেখতে পাবেন **Hospital Demand vs. Fulfillment Report**। এখানে `LEFT JOIN`, `GROUP BY`, `COALESCE`, `NULLIF` এবং `SUM(CASE ...)` ব্যবহার করে প্রতিটি হাসপাতালের ফুলফিলমেন্ট পারসেন্টেজ হিসাব করা হয়েছে।
- `2` চাপলে দেখতে পাবেন **Top Regular Donors Leaderboard**। এখানে `HAVING` ক্লজ এবং সাবকোয়েরি (`SELECT AVG(total_donations) FROM donors`) ব্যবহার করে সিস্টেমের গড়ের চেয়ে বেশি রক্তদানকারী নায়কদের র‍্যাঙ্ক করা হয়েছে।
- `3` চাপলে দেখতে পাবেন **Critical Stock Shortage Monitor** (`CriticalShortageView`)। যে গ্রুপের রক্তের স্টক ৩ ইউনিটের কম বা একদম শূন্য, তা লাল কালিতে দেখাবে এবং নিরাপদ স্টকে পৌঁছাতে আর কয় ইউনিট রক্ত লাগবে তা হিসাব করে দেবে।
- `5` চাপলে ওপেন হবে **Interactive SQL Console**। এখানে আপনি যেকোনো `SELECT` কোয়েরি লাইভ লিখে সরাসরি ডাটাবেস থেকে টেবিল আকারে রেজাল্ট দেখতে পারবেন!

---

### ৯. প্রজেক্টের ফাইল পরিচিতি ও ইন্টারনাল আর্কিটেকচার

```
smart-blood-bank/
│
├── schema.sql           <- ডাটাবেস তৈরির পূর্ণাঙ্গ DDL স্ক্রিপ্ট (3NF/BCNF টেবিল, FK, চেক কনস্ট্রেইন্ট, ইনডেক্স)
├── seed.sql             <- বাস্তবসম্মত প্রাথমিক ডামি ডাটা (৬৪টি কম্প্যাটিবিলিটি কম্বিনেশন, হাসপাতাল ও রক্তদাতা)
├── advanced_db.sql      <- অ্যাডভান্সড অবজেক্ট: ২টি ট্রিগার, ২টি স্টোরড প্রসিডিউর এবং ২টি ভিউ
├── db_config.py         <- সুরক্ষিত ডাটাবেস কানেকশন ম্যানেজার, এরর হ্যান্ডলার এবং কনটেক্সট ম্যানেজার
├── init_db.py           <- স্বয়ংক্রিয় মাইগ্রেশন স্ক্রিপ্ট (যা DELIMITER $$ সহ SQL ফাইল নির্বিঘ্নে চালায়)
├── main.py              <- মূল টার্মিনাল অ্যাপ (Rich কালারফুল মেন্যু, ACID ট্রানজ্যাকশন ইঞ্জিন)
├── requirements.txt     <- পাইথনের প্রয়োজনীয় লাইব্রেরির তালিকা
├── .env.example         <- ডাটাবেস পাসওয়ার্ড কনফিগারেশনের ডামি ফাইল
├── .gitignore           <- গিটহাবে যেন .env এবং পাসওয়ার্ড আপলোড না হয় তার সুরক্ষা ফাইল
└── README.md            <- আপনার দেখা এই পূর্ণাঙ্গ ডকুমেন্টেশন ফাইল
```

---

### ১০. সম্ভাব্য সকল সমস্যা ও তাৎক্ষণিক সমাধান (Troubleshooting Encyclopedia)

#### সমস্যা ১: `[Host Unreachable] Cannot connect to MySQL server at localhost:3306`
* **কারণ:** আপনার কম্পিউটারে MySQL সার্ভিসটি স্টার্ট করা নেই।
* **সমাধান:** 
  - **যদি XAMPP ব্যবহার করেন:** XAMPP Control Panel খুলে MySQL-এর পাশে **Start** বাটনে ক্লিক করুন।
  - **যদি MySQL Installer ব্যবহার করেন:** কিবোর্ডে `Win + R` চেপে লিখুন `services.msc` এবং Enter চাপুন। তালিকায় `MySQL80` খুঁজে বের করে Right Click করে **Start** করুন।

#### সমস্যা ২: `[Authentication Failed] Invalid username or password for MySQL user 'root'`
* **কারণ:** `.env` ফাইলে দেওয়া পাসওয়ার্ডের সাথে আপনার ল্যাপটপের MySQL পাসওয়ার্ড মিলছে না।
* **সমাধান:** Notepad দিয়ে `.env` ফাইলটি খুলুন। আপনার আসল পাসওয়ার্ডটি `DB_PASSWORD=` এর পরে লিখে সেভ করুন। (XAMPP হলে কোনো পাসওয়ার্ড থাকে না, তাই `DB_PASSWORD=` ফাঁকা রেখে সেভ করুন)।

#### সমস্যা ৩: `pip : The term 'pip' is not recognized` বা Application Control Blocked
* **কারণ:** উইন্ডোজের সিকিউরিটি বা এনভায়রনমেন্ট ভেরিয়েবল পাথ সঠিকভাবে সেট না থাকা।
* **সমাধান:** সরাসরি `pip` না লিখে সবসময় লিখুন:
  ```powershell
  python -m pip install -r requirements.txt
  ```

#### সমস্যা ৪: PowerShell-এ `activate.ps1 cannot be loaded because running scripts is disabled`
* **কারণ:** উইন্ডোজের স্ক্রিপ্ট এক্সিকিউশন রেস্ট্রিকশন পলিসি।
* **সমাধান:** আপনাকে ভার্চুয়াল এনভায়রনমেন্ট চালু করতেই হবে এমন কোনো বাধ্যবাধকতা নেই। সরাসরি গ্লোবালি `python -m pip install -r requirements.txt` দিলেই চলবে। অথবা পাওয়ারশেলে লিখুন:
  ```powershell
  Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
  ```

---

### ১১. পরীক্ষক / ভাইভা বোর্ডের জন্য টেকনিক্যাল প্রশ্নোত্তর

ভাইভাতে বা প্রেজেন্টেশনে শিক্ষক যদি প্রজেক্ট সম্পর্কে জটিল প্রশ্ন করেন, তবে নিচের পয়েন্টগুলো আত্মবিশ্বাসের সাথে বলুন:

1. **প্রশ্ন: আপনার ডাটাবেস কোন নরমাল ফর্মে (Normal Form) আছে?**
   - **উত্তর:** "স্যার, ডাটাবেসটি ৩NF এবং BCNF পর্যন্ত নরম্যালাইজড। রক্তদাতার তথ্য, হাসপাতালের তথ্য, এবং রক্তের গ্রুপের সামঞ্জস্যতা আলাদা টেবিলে রাখা হয়েছে। কোনো ট্রানজিটিভ বা পার্শিয়াল ডিপেন্ডেন্সি নেই এবং প্রতিটি ডিটারমিন্যান্টই একটি সুপার-কি।"
2. **প্রশ্ন: রক্ত বরাদ্দে আপনি ACID ট্রানজ্যাকশন কীভাবে নিশ্চিত করেছেন?**
   - **উত্তর:** "স্যার, `main.py`-তে রক্ত বরাদ্দের সময় আমরা `conn.autocommit = False` করে দিয়েছি। এরপর `SELECT ... FOR UPDATE` কুয়েরি দিয়ে প্রয়োজনীয় ব্লাড ব্যাগগুলো রো-লেভেলে লক করা হয়েছে এবং FIFO নিয়মে সবচেয়ে পুরোনো মেয়াদযুক্ত ব্যাগ আগে নির্বাচন করা হয়েছে। এরপর অ্যালোকেশন টেবিলে এন্ট্রি দিলে স্বয়ংক্রিয়ভাবে ডাটাবেস ট্রিগার ইনভেন্টরি স্ট্যাটাস 'Allocated' করে দেয়। কোনো ধাপে সমস্যা হলে পুরো অপারেশন `ROLLBACK` হয়, আর সফল হলে `COMMIT` হয়।"
3. **প্রশ্ন: আপনার প্রজেক্টে ট্রিগার ও স্টোরড প্রসিডিউর কী কাজ করছে?**
   - **উত্তর:** 
     - "ট্রিগার `trg_after_allocation_insert` কোনো রক্ত বরাদ্দ হওয়ার সাথে সাথে স্বয়ংক্রিয়ভাবে ব্যাগের স্ট্যাটাস 'Allocated' করে এবং রিকুয়েস্টের সংখ্যা আপডেট করে।"
     - "ট্রিগার `trg_donor_status_audit` রক্তদাতার শারীরিক বা মেডেলিক স্ট্যাটাস বদলালে অডিট টেবিলে পুরনো ও নতুন তথ্য টাইমস্ট্যাম্প সহ লগ করে রাখে।"
     - "স্টোরড প্রসিডিউর `ExpireOldBloodBags` মেয়াদ পার হয়ে যাওয়া ব্যাগ স্বয়ংক্রিয়ভাবে Expired করে দেয়।"
     - "স্টোরড প্রসিডিউর `MatchCompatibleDonors` কম্প্যাটিবিলিটি ম্যাট্রিক্স ও ৯০ দিনের কুলডাউন চেক করে একই শহরের উপযুক্ত রক্তদাতাদের আগে খুঁজে বের করে।"

---

## 🛡️ Security & Engineering Best Practices
* **SQL Injection Prevention:** 100% of user queries in Python utilize parameterized queries (`%s`). Zero raw string concatenation.
* **Exception Resilience:** All database calls are wrapped in `mysql.connector.Error` handlers; the CLI never crashes on constraint violations or duplicate keys.
* **Resource Cleanup:** Context managers (`@contextmanager`) ensure database connections and cursors are properly closed under all circumstances.

---

**Developed for Academic Excellence in Database Management Systems (DBMS).**
