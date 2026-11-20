"""
===============================================================================
SMART BLOOD BANK & EMERGENCY DONOR MATCHING SYSTEM (CLI)
Production-Grade Terminal Application for DBMS Course Project
===============================================================================
Author: Senior Software Engineer & Database Architect
Stack: Python 3 | MySQL 8.0+ | Rich Terminal UI | InnoDB ACID Transactions
"""

import sys
import os
import datetime
from typing import Optional, List, Dict, Any

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.text import Text
from rich import box
import mysql.connector

from db_config import get_db_connection, get_db_cursor, test_connection, DB_CONFIG
from init_db import run_init

console = Console()

BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]


# =============================================================================
# UI & BANNER UTILITIES
# =============================================================================

def print_banner():
    """Prints the system header and active database status."""
    console.clear()
    title_text = Text("🩸 SMART BLOOD BANK & EMERGENCY DONOR MATCHING SYSTEM", style="bold red")
    subtitle = Text("Healthcare Logistics & ACID Allocation Engine | DBMS Project", style="bold cyan")
    db_info = Text(f"Connected DB: {DB_CONFIG['database']} @ {DB_CONFIG['host']}:{DB_CONFIG['port']}", style="dim")

    banner_panel = Panel(
        Text.assemble(title_text, "\n", subtitle, "\n", db_info, justify="center"),
        border_style="red",
        box=box.DOUBLE
    )
    console.print(banner_panel)


def pause_prompt():
    """Prompts the user to press Enter before returning to the menu."""
    console.print("\n[dim]Press [Enter] to return to menu...[/dim]", end="")
    try:
        input()
    except (KeyboardInterrupt, EOFError):
        pass


def handle_db_error(err: Exception, context: str = "Database Operation"):
    """Displays formatted error messages without crashing the CLI."""
    console.print(f"\n[bold red]❌ [{context} Failed]:[/] {err}")
    if isinstance(err, mysql.connector.Error):
        console.print(f"[dim]MySQL Error Code: {err.errno} | SQLState: {err.sqlstate}[/dim]")
    pause_prompt()


# =============================================================================
# 1. DONOR & ELIGIBILITY MANAGEMENT
# =============================================================================

def register_donor_screen():
    """Interactive screen to register a new blood donor with integrity validation."""
    console.print(Panel("[bold cyan]Donor Registration & Health Intake[/]", border_style="cyan"))

    try:
        full_name = Prompt.ask("[bold white]Full Legal Name[/]").strip()
        if not full_name:
            console.print("[red]Name cannot be empty.[/red]")
            pause_prompt()
            return

        national_id = Prompt.ask("[bold white]National ID / NID[/]").strip()
        gender = Prompt.ask("[bold white]Gender[/]", choices=["Male", "Female", "Other"], default="Male")

        # Validate Date of Birth
        while True:
            dob_str = Prompt.ask("[bold white]Date of Birth (YYYY-MM-DD)[/]")
            try:
                dob = datetime.datetime.strptime(dob_str, "%Y-%m-%d").date()
                age = (datetime.date.today() - dob).days // 365
                if age < 17:
                    console.print("[red]Donor must be at least 17 years old to donate blood.[/red]")
                    continue
                break
            except ValueError:
                console.print("[red]Invalid date format. Please use YYYY-MM-DD.[/red]")

        blood_group = Prompt.ask("[bold white]Blood Group[/]", choices=BLOOD_GROUPS)
        phone = Prompt.ask("[bold white]Contact Phone Number[/]").strip()
        email = Prompt.ask("[bold white]Email Address[/]").strip()
        city = Prompt.ask("[bold white]Current City[/]").strip()
        address = Prompt.ask("[bold white]Street Address (Optional)[/]", default="")

        # Initial donation date check
        had_prior = Confirm.ask("[bold white]Has this donor donated blood previously?[/]", default=False)
        last_donation_date = None
        if had_prior:
            while True:
                ld_str = Prompt.ask("[bold white]Last Donation Date (YYYY-MM-DD)[/]")
                try:
                    ld = datetime.datetime.strptime(ld_str, "%Y-%m-%d").date()
                    if ld > datetime.date.today():
                        console.print("[red]Last donation date cannot be in the future.[/red]")
                        continue
                    last_donation_date = ld
                    break
                except ValueError:
                    console.print("[red]Invalid date format. Use YYYY-MM-DD.[/red]")

        screening_notes = Prompt.ask(
            "[bold white]Medical Screening Notes[/]",
            default="Passed standard vitals and hemoglobin check"
        )

        with get_db_cursor(commit=True) as (conn, cursor):
            query = """
                INSERT INTO donors (
                    national_id, full_name, gender, date_of_birth, blood_group,
                    phone, email, city, address, eligibility_status,
                    medical_screening_notes, last_donation_date, total_donations
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'Eligible', %s, %s, %s)
            """
            cursor.execute(query, (
                national_id, full_name, gender, dob, blood_group,
                phone, email, city, address if address else None,
                screening_notes, last_donation_date, 1 if had_prior else 0
            ))
            donor_id = cursor.lastrowid

        console.print(Panel(
            f"[bold green]✓ Donor Successfully Registered![/]\n"
            f"[white]Donor ID:[/] [cyan]{donor_id}[/] | [white]Name:[/] [cyan]{full_name}[/]\n"
            f"[white]Blood Group:[/] [bold yellow]{blood_group}[/] | [white]City:[/] [cyan]{city}[/]\n"
            f"[white]Status:[/] [bold green]Eligible[/]",
            border_style="green"
        ))
    except Exception as ex:
        handle_db_error(ex, "Donor Registration")
        return

    pause_prompt()


def check_cooldown_and_donate():
    """
    Checks donor's 90-day cooldown period. If eligible, logs a new blood unit donation
    with auto-calculated 42-day expiration date, and updates donor records.
    """
    console.print(Panel("[bold cyan]Blood Donation Intake & 90-Day Cooldown Verification[/]", border_style="cyan"))

    search_term = Prompt.ask("[bold white]Enter Donor ID, Phone Number, or National ID[/]").strip()
    if not search_term:
        return

    try:
        with get_db_cursor() as (conn, cursor):
            # Parameterized search
            cursor.execute("""
                SELECT donor_id, national_id, full_name, blood_group, city,
                       eligibility_status, medical_screening_notes, last_donation_date, total_donations
                FROM donors
                WHERE donor_id = %s OR phone = %s OR national_id = %s
                LIMIT 1;
            """, (search_term if search_term.isdigit() else -1, search_term, search_term))
            donor = cursor.fetchone()

        if not donor:
            console.print("[bold red]No donor found matching that identifier.[/bold red]")
            pause_prompt()
            return

        # Display donor status card
        donor_id = donor["donor_id"]
        full_name = donor["full_name"]
        blood_group = donor["blood_group"]
        elig_status = donor["eligibility_status"]
        last_date = donor["last_donation_date"]
        total_donations = donor["total_donations"]

        status_color = "green" if elig_status == "Eligible" else "red"
        console.print(f"\n[bold white]Donor:[/] {full_name} (ID: {donor_id}) | [bold yellow]Group:[/] {blood_group}")
        console.print(f"[bold white]Eligibility:[/] [{status_color}]{elig_status}[/{status_color}]")
        console.print(f"[bold white]Screening Notes:[/] {donor['medical_screening_notes']}")
        console.print(f"[bold white]Lifetime Donations:[/] {total_donations}")

        # Check Medical Eligibility
        if elig_status != "Eligible":
            console.print(Panel(
                f"[bold red]⛔ DONATION BLOCKED[/]\n"
                f"Donor is currently flagged as [bold]{elig_status}[/].\n"
                f"Medical Note: {donor['medical_screening_notes']}",
                border_style="red"
            ))
            pause_prompt()
            return

        # Check 90-Day Cooldown Rule
        today = datetime.date.today()
        can_donate = True
        days_since = None

        if last_date is not None:
            days_since = (today - last_date).days
            if days_since < 90:
                can_donate = False
                days_left = 90 - days_since
                eligible_date = last_date + datetime.timedelta(days=90)
                console.print(Panel(
                    f"[bold red]⏳ 90-DAY COOLDOWN RESTRICTION ACTIVE[/]\n"
                    f"Last Donation: [cyan]{last_date}[/] ([yellow]{days_since} days ago[/])\n"
                    f"Days remaining in cooldown: [bold red]{days_left} days[/]\n"
                    f"Eligible for next donation on: [bold green]{eligible_date}[/]",
                    border_style="red"
                ))
                pause_prompt()
                return
            else:
                console.print(f"[bold green]✓ 90-Day Cooldown Satisfied:[/] Last donated {days_since} days ago.")
        else:
            console.print("[bold green]✓ First-Time Donor:[/] No prior donation cooldown.")

        # Proceed to Record Donation
        if not Confirm.ask("\n[bold white]Proceed to log a new blood unit donation for this donor?[/]", default=True):
            return

        # Donation Bag Parameters
        volume_ml = IntPrompt.ask("[bold white]Collection Volume (mL)[/]", default=450)
        while True:
            hb_str = Prompt.ask("[bold white]Screened Hemoglobin Level (g/dL, min 12.0)[/]", default="14.0")
            try:
                hemoglobin = float(hb_str)
                if hemoglobin < 12.0:
                    console.print("[red]Hemoglobin level too low (< 12.0 g/dL). Donation disallowed.[/red]")
                    return
                break
            except ValueError:
                console.print("[red]Invalid number.[/red]")

        storage_location = Prompt.ask("[bold white]Cold Storage Vault Location[/]", default="Cold Room 1, Rack A")

        # Auto-calculate expiry date (Standard Whole Blood shelf life = 42 days)
        collection_date = today
        expiry_date = collection_date + datetime.timedelta(days=42)
        bag_code = f"BB-{donor['city'][:3].upper()}-{today.strftime('%Y%m')}-{donor_id:04d}-{total_donations + 1:02d}"

        # Transactional Execution: Create Bag & Update Donor
        with get_db_cursor(commit=True) as (conn, cursor):
            # 1. Insert new blood bag
            cursor.execute("""
                INSERT INTO blood_inventory (
                    bag_code, donor_id, blood_group, volume_ml,
                    collection_date, expiry_date, hemoglobin_g_dl,
                    storage_location, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'Available');
            """, (bag_code, donor_id, blood_group, volume_ml, collection_date, expiry_date, hemoglobin, storage_location))
            bag_id = cursor.lastrowid

            # 2. Update donor last donation date & count
            cursor.execute("""
                UPDATE donors
                SET last_donation_date = %s,
                    total_donations = total_donations + 1
                WHERE donor_id = %s;
            """, (collection_date, donor_id))

        console.print(Panel(
            f"[bold green]✓ Blood Unit Successfully Logged & Shelved![/]\n"
            f"[white]Bag ID:[/] [cyan]{bag_id}[/] | [white]Bag Barcode:[/] [bold cyan]{bag_code}[/]\n"
            f"[white]Blood Group:[/] [bold yellow]{blood_group}[/] | [white]Volume:[/] [cyan]{volume_ml} mL[/]\n"
            f"[white]Collection Date:[/] [cyan]{collection_date}[/] | [white]Expiration Date (42 Days):[/] [bold green]{expiry_date}[/]\n"
            f"[white]Storage Location:[/] [yellow]{storage_location}[/]\n"
            f"[white]Updated Donor Lifetime Donations:[/] [cyan]{total_donations + 1}[/]",
            border_style="green"
        ))

    except Exception as ex:
        handle_db_error(ex, "Donation Intake")
        return

    pause_prompt()


def update_donor_status_screen():
    """
    Updates donor eligibility and notes. Demonstrates the automated donor_audit_log trigger.
    """
    console.print(Panel("[bold cyan]Update Donor Eligibility & Trigger Medical Audit Log[/]", border_style="cyan"))

    donor_id = Prompt.ask("[bold white]Enter Donor ID to update[/]").strip()
    if not donor_id.isdigit():
        console.print("[red]Invalid Donor ID.[/red]")
        pause_prompt()
        return

    try:
        with get_db_cursor() as (conn, cursor):
            cursor.execute("""
                SELECT donor_id, full_name, blood_group, eligibility_status, medical_screening_notes
                FROM donors WHERE donor_id = %s;
            """, (int(donor_id),))
            donor = cursor.fetchone()

        if not donor:
            console.print("[red]Donor not found.[/red]")
            pause_prompt()
            return

        console.print(f"\n[bold white]Current Record for {donor['full_name']} (ID: {donor['donor_id']}):[/]")
        console.print(f"Current Status: [yellow]{donor['eligibility_status']}[/]")
        console.print(f"Current Notes:  [dim]{donor['medical_screening_notes']}[/dim]\n")

        new_status = Prompt.ask(
            "[bold white]Select New Eligibility Status[/]",
            choices=["Eligible", "Temporarily Ineligible", "Permanently Ineligible"],
            default=donor["eligibility_status"]
        )
        new_notes = Prompt.ask(
            "[bold white]Enter New Medical Screening Notes / Deferral Reason[/]",
            default=donor["medical_screening_notes"]
        )

        with get_db_cursor(commit=True) as (conn, cursor):
            cursor.execute("""
                UPDATE donors
                SET eligibility_status = %s,
                    medical_screening_notes = %s
                WHERE donor_id = %s;
            """, (new_status, new_notes, int(donor_id)))

        console.print("\n[bold green]✓ Donor record updated successfully![/]")
        console.print("[dim]The database trigger 'trg_donor_status_audit' has recorded this change in donor_audit_log.[/dim]")

        # Fetch and display the triggered audit record
        with get_db_cursor() as (conn, cursor):
            cursor.execute("""
                SELECT audit_id, action_type, old_eligibility_status, new_eligibility_status,
                       new_medical_notes, changed_by, changed_at
                FROM donor_audit_log
                WHERE donor_id = %s
                ORDER BY audit_id DESC
                LIMIT 1;
            """, (int(donor_id),))
            audit_entry = cursor.fetchone()

        if audit_entry:
            audit_table = Table(title="[bold magenta]Generated Audit Log Entry (Trigger Verified)[/]", box=box.ROUNDED)
            audit_table.add_column("Audit ID", style="cyan")
            audit_table.add_column("Action", style="yellow")
            audit_table.add_column("Old Status", style="dim")
            audit_table.add_column("New Status", style="green")
            audit_table.add_column("Screening Notes", style="white")
            audit_table.add_column("Changed At", style="dim")
            audit_table.add_row(
                str(audit_entry["audit_id"]),
                audit_entry["action_type"],
                str(audit_entry["old_eligibility_status"]),
                str(audit_entry["new_eligibility_status"]),
                str(audit_entry["new_medical_notes"]),
                str(audit_entry["changed_at"])
            )
            console.print(audit_table)

    except Exception as ex:
        handle_db_error(ex, "Update Donor Status")
        return

    pause_prompt()


def view_all_donors():
    """Renders formatted table of all registered donors."""
    console.print(Panel("[bold cyan]Registered Blood Donors Roster[/]", border_style="cyan"))

    try:
        with get_db_cursor() as (conn, cursor):
            cursor.execute("""
                SELECT donor_id, national_id, full_name, blood_group, city, phone,
                       eligibility_status, last_donation_date, total_donations
                FROM donors
                ORDER BY donor_id ASC;
            """)
            donors = cursor.fetchall()

        table = Table(box=box.ROUNDED, expand=True)
        table.add_column("ID", style="cyan", justify="right")
        table.add_column("Name", style="bold white")
        table.add_column("Blood", style="bold yellow", justify="center")
        table.add_column("City", style="cyan")
        table.add_column("Phone", style="dim")
        table.add_column("Status", justify="center")
        table.add_column("Last Donation", style="dim")
        table.add_column("Total", justify="right", style="green")

        for d in donors:
            status_style = "[bold green]Eligible[/]" if d["eligibility_status"] == "Eligible" else f"[bold red]{d['eligibility_status']}[/]"
            table.add_row(
                str(d["donor_id"]),
                d["full_name"],
                d["blood_group"],
                d["city"],
                d["phone"],
                status_style,
                str(d["last_donation_date"]) if d["last_donation_date"] else "Never",
                str(d["total_donations"])
            )

        console.print(table)
    except Exception as ex:
        handle_db_error(ex, "Donor Roster")
        return

    pause_prompt()


# =============================================================================
# 2. BLOOD INVENTORY & EXPIRY TRACKING
# =============================================================================

def view_inventory_dashboard():
    """
    Displays color-coded blood inventory table:
      - Green: Available and healthy (> 7 days remaining)
      - Yellow: Expiring soon (<= 7 days remaining)
      - Bold Red: Expired
      - Cyan: Allocated
    """
    console.print(Panel("[bold cyan]Blood Inventory & Shelf-Life Monitor[/]", border_style="cyan"))

    try:
        with get_db_cursor() as (conn, cursor):
            cursor.execute("""
                SELECT bi.bag_id, bi.bag_code, bi.blood_group, bi.volume_ml,
                       bi.collection_date, bi.expiry_date, bi.hemoglobin_g_dl,
                       bi.storage_location, bi.status,
                       DATEDIFF(bi.expiry_date, CURRENT_DATE()) AS days_remaining,
                       d.full_name AS donor_name
                FROM blood_inventory bi
                JOIN donors d ON bi.donor_id = d.donor_id
                ORDER BY bi.status ASC, bi.expiry_date ASC;
            """)
            bags = cursor.fetchall()

        table = Table(title="[bold green]Live Blood Inventory Bags[/]", box=box.ROUNDED, expand=True)
        table.add_column("ID", style="cyan", justify="right")
        table.add_column("Bag Code", style="bold white")
        table.add_column("Blood", style="bold yellow", justify="center")
        table.add_column("Vol (mL)", justify="right")
        table.add_column("Collected", style="dim")
        table.add_column("Expires", style="bold")
        table.add_column("Days Left", justify="right")
        table.add_column("Location", style="dim")
        table.add_column("Status", justify="center")

        for b in bags:
            days = b["days_remaining"]
            status = b["status"]

            # Color coding logic
            if status == "Expired" or days < 0:
                days_str = f"[bold red]{days}d (EXPIRED)[/]"
                status_badge = "[bold red]EXPIRED[/]"
            elif status == "Allocated":
                days_str = f"[dim]{days}d[/]"
                status_badge = "[bold cyan]ALLOCATED[/]"
            elif days <= 7:
                days_str = f"[bold yellow]{days}d (URGENT)[/]"
                status_badge = "[yellow]AVAILABLE[/]"
            else:
                days_str = f"[bold green]{days}d[/]"
                status_badge = "[green]AVAILABLE[/]"

            table.add_row(
                str(b["bag_id"]),
                b["bag_code"],
                b["blood_group"],
                str(b["volume_ml"]),
                str(b["collection_date"]),
                str(b["expiry_date"]),
                days_str,
                b["storage_location"],
                status_badge
            )

        console.print(table)

    except Exception as ex:
        handle_db_error(ex, "Inventory View")
        return

    pause_prompt()


def run_expiry_procedure():
    """
    Executes the stored procedure ExpireOldBloodBags() to automatically transition
    expired units and display results.
    """
    console.print(Panel("[bold cyan]Execute Stored Procedure: ExpireOldBloodBags()[/]", border_style="cyan"))

    try:
        with get_db_cursor(commit=True) as (conn, cursor):
            # Call procedure with OUT parameter
            cursor.execute("CALL ExpireOldBloodBags(@expired_count);")
            
            # Fetch affected rows result set from procedure
            expired_bags = cursor.fetchall()
            
            # Fetch OUT parameter value
            cursor.execute("SELECT @expired_count AS newly_expired;")
            out_res = cursor.fetchone()
            count = out_res["newly_expired"] if out_res else 0

        console.print(Panel(
            f"[bold yellow]⚙️ Stored Procedure Execution Complete![/]\n"
            f"[white]Units newly transitioned to 'Expired':[/] [bold red]{count}[/]\n"
            f"[white]Total current expired units in repository:[/] [red]{len(expired_bags)}[/]",
            border_style="yellow"
        ))

        if expired_bags:
            table = Table(title="[bold red]Expired Blood Units Repository[/]", box=box.ROUNDED)
            table.add_column("Bag ID", style="cyan")
            table.add_column("Bag Barcode", style="white")
            table.add_column("Group", style="bold yellow")
            table.add_column("Collected", style="dim")
            table.add_column("Expired Date", style="red")
            table.add_column("Days Past Due", justify="right", style="bold red")
            table.add_column("Storage Location", style="dim")

            for eb in expired_bags:
                table.add_row(
                    str(eb["bag_id"]),
                    eb["bag_code"],
                    eb["blood_group"],
                    str(eb["collection_date"]),
                    str(eb["expiry_date"]),
                    str(eb["days_expired"]),
                    eb["storage_location"]
                )
            console.print(table)
        else:
            console.print("[bold green]✓ All available inventory units are strictly within shelf-life![/]")

    except Exception as ex:
        handle_db_error(ex, "Procedure ExpireOldBloodBags")
        return

    pause_prompt()


# =============================================================================
# 3. EMERGENCY HOSPITAL REQUISITIONS & ACID ALLOCATION ENGINE
# =============================================================================

def create_emergency_request_screen():
    """Hospital coordinator or admin files an emergency blood request."""
    console.print(Panel("[bold cyan]New Emergency Blood Requisition Form[/]", border_style="cyan"))

    try:
        with get_db_cursor() as (conn, cursor):
            cursor.execute("SELECT hospital_id, hospital_code, name, city, urgency_tier FROM hospitals ORDER BY hospital_id;")
            hospitals = cursor.fetchall()

        if not hospitals:
            console.print("[red]No hospitals registered in database.[/red]")
            pause_prompt()
            return

        hosp_table = Table(title="Partner Hospital Directory", box=box.SIMPLE)
        hosp_table.add_column("ID", style="cyan")
        hosp_table.add_column("Code", style="white")
        hosp_table.add_column("Hospital Name", style="bold")
        hosp_table.add_column("City", style="dim")
        hosp_table.add_column("Tier", style="yellow")
        for h in hospitals:
            hosp_table.add_row(str(h["hospital_id"]), h["hospital_code"], h["name"], h["city"], h["urgency_tier"])
        console.print(hosp_table)

        hospital_ids = [str(h["hospital_id"]) for h in hospitals]
        hosp_choice = Prompt.ask("[bold white]Select Hospital ID[/]", choices=hospital_ids)
        hospital_id = int(hosp_choice)

        patient_case_id = Prompt.ask("[bold white]Patient Clinical Case ID[/]", default="CASE-EMERGENCY-01").strip()
        required_blood = Prompt.ask("[bold white]Required Blood Group[/]", choices=BLOOD_GROUPS)
        units_requested = IntPrompt.ask("[bold white]Units Requested (Bags)[/]", default=2)

        if units_requested <= 0:
            console.print("[red]Units requested must be greater than zero.[/red]")
            pause_prompt()
            return

        urgency_level = Prompt.ask(
            "[bold white]Urgency Level[/]",
            choices=["CRITICAL", "HIGH", "MEDIUM", "ROUTINE"],
            default="HIGH"
        )
        hours_needed = IntPrompt.ask("[bold white]Required within (hours)[/]", default=3)

        req_code = f"REQ-{datetime.datetime.now().strftime('%Y%m')}-{hospital_id:02d}-{int(datetime.datetime.now().timestamp()) % 10000:04d}"
        required_by_time = datetime.datetime.now() + datetime.timedelta(hours=hours_needed)

        with get_db_cursor(commit=True) as (conn, cursor):
            cursor.execute("""
                INSERT INTO emergency_requests (
                    request_code, hospital_id, patient_case_id, required_blood_group,
                    units_requested, units_allocated, urgency_level, status,
                    required_by_time, request_date
                ) VALUES (%s, %s, %s, %s, %s, 0, %s, 'Pending', %s, NOW());
            """, (req_code, hospital_id, patient_case_id, required_blood, units_requested, urgency_level, required_by_time))
            request_id = cursor.lastrowid

        console.print(Panel(
            f"[bold green]✓ Emergency Request Successfully Submitted![/]\n"
            f"[white]Request ID:[/] [cyan]{request_id}[/] | [white]Code:[/] [bold cyan]{req_code}[/]\n"
            f"[white]Patient Case:[/] [yellow]{patient_case_id}[/] | [white]Group Needed:[/] [bold red]{required_blood}[/]\n"
            f"[white]Units Needed:[/] [cyan]{units_requested}[/] | [white]Urgency:[/] [bold red]{urgency_level}[/]\n"
            f"[white]Required By:[/] [cyan]{required_by_time.strftime('%Y-%m-%d %H:%M')}[/]",
            border_style="green"
        ))

    except Exception as ex:
        handle_db_error(ex, "Create Emergency Request")
        return

    pause_prompt()


def allocate_blood_transaction_screen():
    """
    ACID Transaction Engine:
    Performs transactional FIFO blood bag allocation with row-level locks
    (SELECT ... FOR UPDATE) to ensure concurrency safety.
    Triggers automatically mark bags as 'Allocated' and update request status.
    """
    console.print(Panel("[bold cyan]Emergency Blood Allocation Engine (ACID Transaction)[/]", border_style="cyan"))

    try:
        # Fetch pending or partially fulfilled requests
        with get_db_cursor() as (conn, cursor):
            cursor.execute("""
                SELECT er.request_id, er.request_code, h.name AS hospital_name,
                       er.patient_case_id, er.required_blood_group,
                       er.units_requested, er.units_allocated,
                       (er.units_requested - er.units_allocated) AS units_needed,
                       er.urgency_level, er.status, er.required_by_time
                FROM emergency_requests er
                JOIN hospitals h ON er.hospital_id = h.hospital_id
                WHERE er.status IN ('Pending', 'Partially Fulfilled')
                ORDER BY (er.urgency_level = 'CRITICAL') DESC, er.required_by_time ASC;
            """)
            requests = cursor.fetchall()

        if not requests:
            console.print("[bold green]No pending emergency requests! All requisitions are fulfilled.[/]")
            pause_prompt()
            return

        table = Table(title="[bold yellow]Pending Emergency Requisitions[/]", box=box.ROUNDED, expand=True)
        table.add_column("Req ID", style="cyan", justify="right")
        table.add_column("Request Code", style="bold white")
        table.add_column("Hospital", style="white")
        table.add_column("Blood", style="bold red", justify="center")
        table.add_column("Req/Alloc/Need", justify="center")
        table.add_column("Urgency", justify="center")
        table.add_column("Deadline", style="dim")

        for r in requests:
            urgency_style = "[bold red]CRITICAL[/]" if r["urgency_level"] == "CRITICAL" else f"[yellow]{r['urgency_level']}[/]"
            table.add_row(
                str(r["request_id"]),
                r["request_code"],
                r["hospital_name"][:28],
                r["required_blood_group"],
                f"{r['units_requested']} / {r['units_allocated']} / [bold yellow]{r['units_needed']}[/]",
                urgency_style,
                str(r["required_by_time"])[:16]
            )
        console.print(table)

        req_choice = Prompt.ask("[bold white]Enter Request ID to allocate units for (or 0 to cancel)[/]").strip()
        if not req_choice.isdigit() or int(req_choice) == 0:
            return

        target_request_id = int(req_choice)
        allocated_by = Prompt.ask("[bold white]Dispatcher / Coordinator Name[/]", default="COORD_OFFICER").strip()

        # START STRICT TRANSACTION
        conn = get_db_connection(use_database=True)
        conn.autocommit = False  # Enforce transaction boundary
        cursor = conn.cursor(dictionary=True)

        try:
            # 1. Lock the emergency request row FOR UPDATE
            cursor.execute("""
                SELECT request_id, request_code, required_blood_group,
                       units_requested, units_allocated, status
                FROM emergency_requests
                WHERE request_id = %s
                FOR UPDATE;
            """, (target_request_id,))
            req_locked = cursor.fetchone()

            if not req_locked:
                console.print("[red]Request not found.[/red]")
                conn.rollback()
                return

            if req_locked["status"] == "Fulfilled":
                console.print("[yellow]This request has already been completely fulfilled.[/yellow]")
                conn.rollback()
                return

            units_needed = req_locked["units_requested"] - req_locked["units_allocated"]
            recipient_group = req_locked["required_blood_group"]

            # 2. Query compatible blood groups via matrix
            cursor.execute("""
                SELECT donor_group
                FROM blood_group_compatibility
                WHERE recipient_group = %s AND is_compatible = TRUE;
            """, (recipient_group,))
            compat_groups = [row["donor_group"] for row in cursor.fetchall()]

            console.print(f"\n[cyan]Target Group:[/] [bold yellow]{recipient_group}[/] | "
                          f"[cyan]Units Needed:[/] [bold yellow]{units_needed}[/]")
            console.print(f"[dim]Transfusion Compatible Donor Groups:[/] [white]{', '.join(compat_groups)}[/dim]")

            # 3. SELECT candidate blood bags with FIFO locking (oldest non-expired first)
            # Row lock candidate bags so no other concurrent transaction can claim them!
            format_strings = ','.join(['%s'] * len(compat_groups))
            candidate_query = f"""
                SELECT bag_id, bag_code, blood_group, volume_ml,
                       collection_date, expiry_date, storage_location
                FROM blood_inventory
                WHERE blood_group IN ({format_strings})
                  AND status = 'Available'
                  AND expiry_date >= CURRENT_DATE()
                ORDER BY expiry_date ASC, collection_date ASC
                LIMIT %s
                FOR UPDATE;
            """
            cursor.execute(candidate_query, tuple(compat_groups) + (units_needed,))
            candidate_bags = cursor.fetchall()

            if not candidate_bags:
                console.print(Panel(
                    f"[bold red]❌ ALLOCATION ABORTED - INSUFFICIENT COMPATIBLE STOCK[/]\n"
                    f"Zero compatible available bags found for recipient group [yellow]{recipient_group}[/].\n"
                    f"Transaction rolled back. Please trigger the Smart Donor Matchmaker to mobilize donors.",
                    border_style="red"
                ))
                conn.rollback()
                pause_prompt()
                return

            # Display candidate allocation preview
            alloc_table = Table(title="[bold cyan]FIFO Candidate Bags Selected for Locking & Allocation[/]", box=box.ROUNDED)
            alloc_table.add_column("Bag ID", style="cyan")
            alloc_table.add_column("Bag Code", style="bold white")
            alloc_table.add_column("Donor Group", style="bold yellow")
            alloc_table.add_column("Volume", justify="right")
            alloc_table.add_column("Collection", style="dim")
            alloc_table.add_column("Expiry Date (FIFO)", style="green")
            alloc_table.add_column("Vault Shelf", style="dim")

            for cb in candidate_bags:
                alloc_table.add_row(
                    str(cb["bag_id"]),
                    cb["bag_code"],
                    cb["blood_group"],
                    f"{cb['volume_ml']} mL",
                    str(cb["collection_date"]),
                    str(cb["expiry_date"]),
                    cb["storage_location"]
                )
            console.print(alloc_table)

            if len(candidate_bags) < units_needed:
                console.print(f"[bold yellow]⚠️ Partial Stock Notice:[/] Needed {units_needed} units, but only {len(candidate_bags)} available.")

            # 4. Confirmation step
            if not Confirm.ask(f"[bold white]Commit ACID transaction to allocate these {len(candidate_bags)} unit(s)?[/]", default=True):
                console.print("[yellow]Transaction intentionally cancelled by user. Executing ROLLBACK...[/yellow]")
                conn.rollback()
                console.print("[bold green]✓ Rollback complete. No inventory rows were altered.[/bold green]")
                pause_prompt()
                return

            # 5. Insert allocations (Trigger 'trg_after_allocation_insert' will fire on MySQL!)
            for bag in candidate_bags:
                cursor.execute("""
                    INSERT INTO request_allocations (request_id, bag_id, allocated_by, dispatch_status)
                    VALUES (%s, %s, %s, 'Dispatched');
                """, (target_request_id, bag["bag_id"], allocated_by))

            # 6. COMMIT TRANSACTION
            conn.commit()

            # Verify updated requisition status
            cursor.execute("""
                SELECT request_code, units_requested, units_allocated, status
                FROM emergency_requests WHERE request_id = %s;
            """, (target_request_id,))
            updated_req = cursor.fetchone()

            console.print(Panel(
                f"[bold green]✓ TRANSACTION COMMITTED SUCCESSFULLY![/]\n"
                f"[white]Request Code:[/] [cyan]{updated_req['request_code']}[/]\n"
                f"[white]Allocated Units:[/] [bold green]{len(candidate_bags)} unit(s)[/]\n"
                f"[white]New Requisition Status:[/] [bold yellow]{updated_req['status']}[/] "
                f"({updated_req['units_allocated']}/{updated_req['units_requested']} units fulfilled)\n"
                f"[dim]The trigger 'trg_after_allocation_insert' has synchronized blood_inventory status to 'Allocated'.[/dim]",
                border_style="green"
            ))

        except Exception as tx_err:
            conn.rollback()
            console.print(f"\n[bold red]❌ Transaction failed and was rolled back automatically:[/bold red] {tx_err}")
            pause_prompt()
            return
        finally:
            cursor.close()
            conn.close()

    except Exception as ex:
        handle_db_error(ex, "Allocation Transaction")
        return

    pause_prompt()


def view_allocation_history():
    """Displays history of all fulfilled/dispatched blood bag allocations."""
    console.print(Panel("[bold cyan]Historical Blood Bag Dispatch & Allocation Records[/]", border_style="cyan"))

    try:
        with get_db_cursor() as (conn, cursor):
            cursor.execute("""
                SELECT ra.allocation_id, er.request_code, h.name AS hospital_name,
                       bi.bag_code, bi.blood_group AS bag_blood_group,
                       er.required_blood_group AS patient_blood_group,
                       ra.allocated_by, ra.dispatch_status, ra.allocated_at
                FROM request_allocations ra
                JOIN emergency_requests er ON ra.request_id = er.request_id
                JOIN hospitals h ON er.hospital_id = h.hospital_id
                JOIN blood_inventory bi ON ra.bag_id = bi.bag_id
                ORDER BY ra.allocation_id DESC
                LIMIT 50;
            """)
            allocs = cursor.fetchall()

        if not allocs:
            console.print("[dim]No allocation records found in database.[/dim]")
            pause_prompt()
            return

        table = Table(box=box.ROUNDED, expand=True)
        table.add_column("Alloc ID", style="cyan")
        table.add_column("Req Code", style="white")
        table.add_column("Hospital", style="bold")
        table.add_column("Bag Code", style="yellow")
        table.add_column("Donor -> Recipient", justify="center", style="bold magenta")
        table.add_column("Dispatcher", style="dim")
        table.add_column("Status", style="green")
        table.add_column("Timestamp", style="dim")

        for a in allocs:
            table.add_row(
                str(a["allocation_id"]),
                a["request_code"],
                a["hospital_name"][:25],
                a["bag_code"],
                f"{a['bag_blood_group']} ➔ {a['patient_blood_group']}",
                a["allocated_by"],
                a["dispatch_status"],
                str(a["allocated_at"])[:19]
            )
        console.print(table)

    except Exception as ex:
        handle_db_error(ex, "Allocation History")
        return

    pause_prompt()


# =============================================================================
# 4. COMPLEX ANALYTICAL QUERIES (Joins, Subqueries, Group By, Having, Views)
# =============================================================================

def smart_donor_matchmaker():
    """
    Invokes Stored Procedure MatchCompatibleDonors(hospital_id, required_blood_group).
    Demonstrates procedural matrix lookup, cooldown filtering, and city proximity sorting.
    """
    console.print(Panel("[bold cyan]Smart Compatible Donor Matchmaker (Stored Procedure)[/]", border_style="cyan"))

    try:
        with get_db_cursor() as (conn, cursor):
            cursor.execute("SELECT hospital_id, name, city FROM hospitals ORDER BY hospital_id;")
            hospitals = cursor.fetchall()

        hosp_table = Table(box=box.SIMPLE)
        hosp_table.add_column("ID", style="cyan")
        hosp_table.add_column("Hospital Name", style="bold")
        hosp_table.add_column("City", style="dim")
        for h in hospitals:
            hosp_table.add_row(str(h["hospital_id"]), h["name"], h["city"])
        console.print(hosp_table)

        hosp_ids = [str(h["hospital_id"]) for h in hospitals]
        hosp_choice = Prompt.ask("[bold white]Select Requesting Hospital ID[/]", choices=hosp_ids)
        target_group = Prompt.ask("[bold white]Required Blood Group for Patient[/]", choices=BLOOD_GROUPS)

        with get_db_cursor() as (conn, cursor):
            cursor.execute("CALL MatchCompatibleDonors(%s, %s);", (int(hosp_choice), target_group))
            matched_donors = cursor.fetchall()

        if not matched_donors:
            console.print(Panel(
                f"[bold red]No matching eligible donors currently available for {target_group}.[/]\n"
                f"All compatible donors are either in their 90-day cooldown or flagged ineligible.",
                border_style="red"
            ))
            pause_prompt()
            return

        table = Table(
            title=f"[bold green]Compatible Donors for Recipient Blood Group: {target_group}[/]",
            box=box.ROUNDED,
            expand=True
        )
        table.add_column("ID", style="cyan", justify="right")
        table.add_column("Donor Name", style="bold white")
        table.add_column("Donor Blood", style="bold yellow", justify="center")
        table.add_column("Proximity", style="bold")
        table.add_column("City", style="white")
        table.add_column("Phone Contact", style="cyan")
        table.add_column("Cooldown Status", style="green")
        table.add_column("Donations", justify="right")

        for md in matched_donors:
            prox_style = "[bold green]Local (Same City)[/]" if "Local" in md["proximity_status"] else "[dim]Out-of-City[/]"
            table.add_row(
                str(md["donor_id"]),
                md["full_name"],
                md["donor_blood_group"],
                prox_style,
                md["city"],
                md["phone"],
                md["donation_history"],
                str(md["total_donations"])
            )
        console.print(table)

    except Exception as ex:
        handle_db_error(ex, "Smart Matchmaker")
        return

    pause_prompt()


def hospital_fulfillment_report():
    """
    Complex Analytical Query:
    Demonstrates LEFT JOIN, GROUP BY, COALESCE, NULLIF, and conditional SUM(CASE).
    Computes real-time fulfillment rates per healthcare institution.
    """
    console.print(Panel("[bold cyan]Analytical Report: Hospital Demand vs. Fulfillment Rates[/]", border_style="cyan"))

    try:
        with get_db_cursor() as (conn, cursor):
            query = """
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
            """
            cursor.execute(query)
            report_data = cursor.fetchall()

        table = Table(
            title="[bold yellow]Hospital Demand vs. Fulfillment Aggregates (LEFT JOIN & GROUP BY)[/]",
            box=box.ROUNDED,
            expand=True
        )
        table.add_column("Code", style="cyan")
        table.add_column("Hospital Name", style="bold white")
        table.add_column("City", style="dim")
        table.add_column("Tier", style="dim")
        table.add_column("Requests", justify="right")
        table.add_column("Requested", justify="right")
        table.add_column("Allocated", justify="right")
        table.add_column("Rate %", justify="right", style="bold")
        table.add_column("Pending", justify="right", style="yellow")
        table.add_column("Fulfilled", justify="right", style="green")

        for row in report_data:
            pct = row["fulfillment_rate_pct"]
            pct_str = f"{pct}%" if pct is not None else "[dim]N/A[/]"
            pct_style = "bold green" if pct and pct >= 80 else ("bold yellow" if pct and pct >= 40 else "bold red")

            table.add_row(
                row["hospital_code"],
                row["hospital_name"][:26],
                row["city"],
                row["urgency_tier"][:12],
                str(row["total_requests"]),
                str(row["total_units_requested"]),
                str(row["total_units_allocated"]),
                f"[{pct_style}]{pct_str}[/{pct_style}]",
                str(row["pending_requests"]),
                str(row["fulfilled_requests"])
            )
        console.print(table)

    except Exception as ex:
        handle_db_error(ex, "Hospital Fulfillment Report")
        return

    pause_prompt()


def top_donors_leaderboard():
    """
    Complex Analytical Query:
    Demonstrates Subqueries and HAVING clause.
    Ranks repeat donors whose donation count exceeds the fleet-wide average.
    """
    console.print(Panel("[bold cyan]Hero Donors Leaderboard (HAVING Clause & Subqueries)[/]", border_style="cyan"))

    try:
        with get_db_cursor() as (conn, cursor):
            query = """
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
            """
            cursor.execute(query)
            leaders = cursor.fetchall()

            # Also fetch fleet average for presentation
            cursor.execute("SELECT ROUND(AVG(total_donations), 2) AS avg_donations FROM donors;")
            avg_res = cursor.fetchone()
            avg_donations = avg_res["avg_donations"] if avg_res else 0

        console.print(f"[bold cyan]Fleet-Wide Average Lifetime Donations:[/] [bold yellow]{avg_donations}[/]\n")

        table = Table(
            title="[bold green]Top Donors Exceeding System Average (HAVING total_donations >= AVG)[/]",
            box=box.ROUNDED,
            expand=True
        )
        table.add_column("Rank", justify="center", style="bold cyan")
        table.add_column("Hero Donor", style="bold white")
        table.add_column("Blood Group", style="bold yellow", justify="center")
        table.add_column("City", style="dim")
        table.add_column("Lifetime Donations", justify="right", style="bold green")
        table.add_column("Bags on Shelf", justify="right")
        table.add_column("Volume on Shelf", justify="right")
        table.add_column("Lives Impacted (est.)", justify="right", style="bold magenta")

        for rank, l in enumerate(leaders, start=1):
            table.add_row(
                f"#{rank}",
                l["full_name"],
                l["blood_group"],
                l["city"],
                str(l["total_donations"]),
                str(l["recorded_units_on_shelf"]),
                f"{l['total_ml_on_shelf']} mL",
                f"~{l['estimated_lives_saved']} lives"
            )
        console.print(table)

    except Exception as ex:
        handle_db_error(ex, "Donors Leaderboard")
        return

    pause_prompt()


def view_critical_shortage_view():
    """Queries and displays the SQL View: CriticalShortageView."""
    console.print(Panel("[bold cyan]Database View: CriticalShortageView[/]", border_style="cyan"))

    try:
        with get_db_cursor() as (conn, cursor):
            cursor.execute("""
                SELECT blood_group, current_stock_units, total_volume_ml,
                       earliest_expiry_date, shortage_severity,
                       units_needed_to_safe_threshold
                FROM CriticalShortageView;
            """)
            shortages = cursor.fetchall()

        table = Table(
            title="[bold red]Critical Blood Inventory Shortage Monitor (< 3 Units Available)[/]",
            box=box.ROUNDED,
            expand=True
        )
        table.add_column("Blood Group", style="bold yellow", justify="center")
        table.add_column("Current Units", justify="right", style="bold")
        table.add_column("Volume (mL)", justify="right")
        table.add_column("Earliest Expiry", style="dim")
        table.add_column("Shortage Severity", justify="center")
        table.add_column("Deficit to Safety (Units)", justify="right", style="bold red")

        for s in shortages:
            severity = s["shortage_severity"]
            sev_style = "bold red" if "CRITICAL" in severity or "EXTREME" in severity else "yellow"
            table.add_row(
                s["blood_group"],
                str(s["current_stock_units"]),
                f"{s['total_volume_ml']} mL",
                str(s["earliest_expiry_date"]) if s["earliest_expiry_date"] else "[dim]No Stock[/]",
                f"[{sev_style}]{severity}[/{sev_style}]",
                str(s["units_needed_to_safe_threshold"])
            )
        console.print(table)

    except Exception as ex:
        handle_db_error(ex, "CriticalShortageView")
        return

    pause_prompt()


def view_available_stock_view():
    """Queries and displays the SQL View: AvailableBloodStockView."""
    console.print(Panel("[bold cyan]Database View: AvailableBloodStockView[/]", border_style="cyan"))

    try:
        with get_db_cursor() as (conn, cursor):
            cursor.execute("""
                SELECT blood_group, units_available, total_volume_ml,
                       oldest_collection_date, earliest_expiry_date, days_until_next_expiry
                FROM AvailableBloodStockView
                ORDER BY blood_group ASC;
            """)
            stock = cursor.fetchall()

        table = Table(
            title="[bold green]Available Unallocated Blood Stock (Non-Expired)[/]",
            box=box.ROUNDED,
            expand=True
        )
        table.add_column("Blood Group", style="bold yellow", justify="center")
        table.add_column("Units Ready", justify="right", style="bold green")
        table.add_column("Total Volume", justify="right")
        table.add_column("Oldest Bag Collected", style="dim")
        table.add_column("Earliest Expiry Date", style="bold white")
        table.add_column("Days Until Expiry", justify="right", style="cyan")

        for st in stock:
            table.add_row(
                st["blood_group"],
                str(st["units_available"]),
                f"{st['total_volume_ml']} mL",
                str(st["oldest_collection_date"]),
                str(st["earliest_expiry_date"]),
                f"{st['days_until_next_expiry']} days"
            )
        console.print(table)

    except Exception as ex:
        handle_db_error(ex, "AvailableBloodStockView")
        return

    pause_prompt()


def view_donor_audit_log_screen():
    """Displays regulatory donor audit log created by the database trigger."""
    console.print(Panel("[bold cyan]Regulatory Audit Log (Trigger: trg_donor_status_audit)[/]", border_style="cyan"))

    try:
        with get_db_cursor() as (conn, cursor):
            cursor.execute("""
                SELECT al.audit_id, d.full_name, al.action_type,
                       al.old_eligibility_status, al.new_eligibility_status,
                       al.old_medical_notes, al.new_medical_notes,
                       al.changed_by, al.changed_at
                FROM donor_audit_log al
                JOIN donors d ON al.donor_id = d.donor_id
                ORDER BY al.audit_id DESC
                LIMIT 50;
            """)
            logs = cursor.fetchall()

        if not logs:
            console.print("[dim]No audit log records found.[/dim]")
            pause_prompt()
            return

        table = Table(box=box.ROUNDED, expand=True)
        table.add_column("Audit ID", style="cyan")
        table.add_column("Donor Name", style="bold white")
        table.add_column("Action", style="yellow")
        table.add_column("Status Transition", style="magenta")
        table.add_column("New Medical Notes", style="dim")
        table.add_column("User", style="cyan")
        table.add_column("Timestamp", style="dim")

        for l in logs:
            transition = f"{l['old_eligibility_status']} ➔ {l['new_eligibility_status']}"
            table.add_row(
                str(l["audit_id"]),
                l["full_name"],
                l["action_type"],
                transition,
                l["new_medical_notes"][:35] if l["new_medical_notes"] else "-",
                l["changed_by"],
                str(l["changed_at"])[:19]
            )
        console.print(table)

    except Exception as ex:
        handle_db_error(ex, "Donor Audit Log")
        return

    pause_prompt()


# =============================================================================
# 5. DIAGNOSTICS & RAW SQL QUERY CONSOLE (For Academic Demos)
# =============================================================================

def interactive_sql_console():
    """Safe interactive SQL query console for live grading demonstrations."""
    console.print(Panel(
        "[bold cyan]Interactive SQL Console (Read-Only Demo Runner)[/]\n"
        "[dim]Enter any SELECT statement to inspect database tables dynamically.\n"
        "Type 'exit' to return to menu.[/dim]",
        border_style="cyan"
    ))

    while True:
        try:
            sql = Prompt.ask("\n[bold yellow]mysql>[/]").strip()
            if not sql:
                continue
            if sql.lower() in ("exit", "quit", "q"):
                break

            # Safety check: allow SELECT queries or explain
            first_word = sql.split()[0].upper()
            if first_word not in ("SELECT", "SHOW", "DESCRIBE", "EXPLAIN"):
                console.print("[red]For safety, the interactive console only supports SELECT, SHOW, DESCRIBE, and EXPLAIN queries.[/red]")
                continue

            with get_db_cursor(dictionary=False) as (conn, cursor):
                cursor.execute(sql)
                rows = cursor.fetchall()
                col_names = [desc[0] for desc in cursor.description] if cursor.description else []

            if not col_names:
                console.print("[yellow]Query executed. No rows returned.[/yellow]")
                continue

            query_table = Table(box=box.ROUNDED)
            for col in col_names:
                query_table.add_column(col, style="bold cyan")

            for r in rows[:100]:  # Limit 100 rows for terminal safety
                query_table.add_row(*[str(val) if val is not None else "[dim]NULL[/]" for val in r])

            console.print(query_table)
            console.print(f"[dim]({len(rows)} row(s) returned)[/dim]")

        except Exception as ex:
            console.print(f"[bold red]SQL Error:[/] {ex}")


def system_diagnostics_screen():
    """Tests connection and outputs server telemetry."""
    console.print(Panel("[bold cyan]Database System Diagnostics & Health Check[/]", border_style="cyan"))
    success, msg, info = test_connection()

    if success:
        console.print(Panel(
            f"[bold green]✓ MySQL Server Connection Active[/]\n"
            f"[white]Server Version:[/] [cyan]{info.get('version')}[/]\n"
            f"[white]Connected User:[/] [cyan]{info.get('user')}[/]\n"
            f"[white]Host Node:[/] [cyan]{info.get('host')}[/]\n"
            f"[white]Target Database:[/] [yellow]{info.get('target_database')}[/] "
            f"({'[green]EXISTS[/green]' if info.get('database_exists') else '[red]MISSING - Run Migration[/red]'})",
            border_style="green"
        ))
    else:
        console.print(Panel(
            f"[bold red]❌ Connection Diagnostics Failed[/]\n{msg}",
            border_style="red"
        ))
    pause_prompt()


# =============================================================================
# ROLE-BASED SUB-MENUS & MAIN LOOP
# =============================================================================

def admin_menu():
    """Blood Bank Administrator Operations Menu."""
    while True:
        print_banner()
        console.print(Panel(
            "[bold white]BLOOD BANK ADMINISTRATOR CONTROL PANEL[/]\n\n"
            " [1] Register New Blood Donor\n"
            " [2] Check 90-Day Cooldown & Record Blood Donation\n"
            " [3] Update Donor Medical Status (Fires Audit Trigger)\n"
            " [4] View Donor Roster\n"
            " [5] View Blood Inventory Dashboard (Color-Coded)\n"
            " [6] Run Expiry Check Stored Procedure (ExpireOldBloodBags)\n"
            " [7] View Regulatory Donor Audit Log\n"
            " [0] Return to Main Menu",
            border_style="cyan"
        ))

        choice = Prompt.ask("[bold cyan]Select Administrator Option[/]", choices=["0", "1", "2", "3", "4", "5", "6", "7"])

        if choice == "1":
            register_donor_screen()
        elif choice == "2":
            check_cooldown_and_donate()
        elif choice == "3":
            update_donor_status_screen()
        elif choice == "4":
            view_all_donors()
        elif choice == "5":
            view_inventory_dashboard()
        elif choice == "6":
            run_expiry_procedure()
        elif choice == "7":
            view_donor_audit_log_screen()
        elif choice == "0":
            break


def coordinator_menu():
    """Hospital Logistics Coordinator Operations Menu."""
    while True:
        print_banner()
        console.print(Panel(
            "[bold white]HOSPITAL COORDINATOR EMERGENCY PORTAL[/]\n\n"
            " [1] Submit Emergency Hospital Blood Request\n"
            " [2] Real-Time ACID Blood Bag Allocation (FIFO & Locking)\n"
            " [3] Smart Compatible Donor Matchmaker (Stored Procedure)\n"
            " [4] View Available Blood Stock View (Non-Expired Units)\n"
            " [5] View Blood Bag Dispatch & Allocation History\n"
            " [0] Return to Main Menu",
            border_style="yellow"
        ))

        choice = Prompt.ask("[bold yellow]Select Coordinator Option[/]", choices=["0", "1", "2", "3", "4", "5"])

        if choice == "1":
            create_emergency_request_screen()
        elif choice == "2":
            allocate_blood_transaction_screen()
        elif choice == "3":
            smart_donor_matchmaker()
        elif choice == "4":
            view_available_stock_view()
        elif choice == "5":
            view_allocation_history()
        elif choice == "0":
            break


def analytics_menu():
    """Analytical Reports and SQL Demonstrations Menu."""
    while True:
        print_banner()
        console.print(Panel(
            "[bold white]ANALYTICAL INTELLIGENCE & SQL CAPABILITIES[/]\n\n"
            " [1] Hospital Demand vs. Fulfillment Report (LEFT JOIN & GROUP BY)\n"
            " [2] Top Regular Donors Leaderboard (HAVING Clause & Subquery)\n"
            " [3] Critical Stock Shortage Monitor (CriticalShortageView)\n"
            " [4] Available Stock Summary (AvailableBloodStockView)\n"
            " [5] Interactive SQL Query Console (Academic Demo)\n"
            " [0] Return to Main Menu",
            border_style="magenta"
        ))

        choice = Prompt.ask("[bold magenta]Select Analytics Option[/]", choices=["0", "1", "2", "3", "4", "5"])

        if choice == "1":
            hospital_fulfillment_report()
        elif choice == "2":
            top_donors_leaderboard()
        elif choice == "3":
            view_critical_shortage_view()
        elif choice == "4":
            view_available_stock_view()
        elif choice == "5":
            interactive_sql_console()
        elif choice == "0":
            break


def main_menu():
    """Top-Level Application Entry Point."""
    while True:
        print_banner()
        console.print(Panel(
            "[bold white]MAIN SYSTEM PORTAL[/]\n\n"
            " [1] Blood Bank Administrator Panel\n"
            " [2] Hospital Emergency Coordinator Portal\n"
            " [3] Analytical Intelligence & SQL Reports Hub\n"
            " [4] System Diagnostics & Database Health\n"
            " [5] Run Database Migration / Reset (schema, seed, advanced_db)\n"
            " [0] Exit Application",
            border_style="red"
        ))

        choice = Prompt.ask("[bold red]Enter Selection[/]", choices=["0", "1", "2", "3", "4", "5"])

        if choice == "1":
            admin_menu()
        elif choice == "2":
            coordinator_menu()
        elif choice == "3":
            analytics_menu()
        elif choice == "4":
            system_diagnostics_screen()
        elif choice == "5":
            if Confirm.ask("[bold red]Re-initialize database? (This will drop existing tables and re-seed)[/]", default=False):
                try:
                    run_init()
                except Exception as ex:
                    handle_db_error(ex, "Database Migration")
                pause_prompt()
        elif choice == "0":
            console.print("\n[bold cyan]Thank you for using the Smart Blood Bank System. Stay safe![/bold cyan]\n")
            sys.exit(0)


if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        console.print("\n\n[dim]Process terminated by user. Goodbye![/dim]")
        sys.exit(0)
