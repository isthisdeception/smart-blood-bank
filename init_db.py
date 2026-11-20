"""
Database Initialization & Migration Utility
Smart Blood Bank & Emergency Donor Matching System

Executes schema.sql, seed.sql, and advanced_db.sql sequentially,
properly handling MySQL procedural blocks and DELIMITER statements.
"""

import os
import sys
import re
from typing import List
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

from db_config import DB_CONFIG, get_db_connection

console = Console()


def parse_sql_file(file_path: str) -> List[str]:
    """
    Parses a MySQL script file into individual executable statements.
    Correctly recognizes client-side DELIMITER statements for triggers
    and stored procedures.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"SQL file not found at: {file_path}")

    statements = []
    current_delimiter = ";"
    statement_buffer = []

    with open(file_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            stripped = line.strip()

            # Ignore pure comment lines and blank lines
            if not stripped or stripped.startswith("--") or stripped.startswith("#"):
                continue

            # Check for DELIMITER command
            delim_match = re.match(r"^DELIMITER\s+(\S+)", stripped, re.IGNORECASE)
            if delim_match:
                # Flush existing buffer if any
                buf_content = "\n".join(statement_buffer).strip()
                if buf_content:
                    statements.append(buf_content)
                    statement_buffer = []
                current_delimiter = delim_match.group(1)
                continue

            statement_buffer.append(line)

            # Check if current buffer ends with current delimiter
            accumulated = "".join(statement_buffer).strip()
            if accumulated.endswith(current_delimiter):
                # Remove delimiter from end
                stmt = accumulated[:-len(current_delimiter)].strip()
                if stmt:
                    statements.append(stmt)
                statement_buffer = []

    # Final flush
    accumulated = "".join(statement_buffer).strip()
    if accumulated:
        if current_delimiter != ";" and accumulated.endswith(current_delimiter):
            accumulated = accumulated[:-len(current_delimiter)].strip()
        if accumulated:
            statements.append(accumulated)

    return statements


def execute_sql_file(conn, file_path: str, file_label: str) -> int:
    """
    Executes all statements in an SQL script file using the active connection.
    """
    statements = parse_sql_file(file_path)
    cursor = conn.cursor()
    executed_count = 0

    with Progress(
        SpinnerColumn(),
        TextColumn(f"[bold cyan]{file_label}[/] [dim]({{task.completed}}/{{task.total}})[/]"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console,
        transient=True
    ) as progress:
        task = progress.add_task("Executing", total=len(statements))

        for stmt in statements:
            # Skip empty or no-op statements
            if not stmt.strip():
                progress.advance(task)
                continue
            try:
                cursor.execute(stmt)
                executed_count += 1
            except Exception as ex:
                console.print(f"[bold red]Error in {file_label}:[/] {ex}")
                console.print(f"[dim]Failed statement snippet:\n{stmt[:250]}...[/]")
                raise
            finally:
                progress.advance(task)

    cursor.close()
    conn.commit()
    return executed_count


def print_database_summary(conn):
    """
    Prints a rich summary table displaying all tables, row counts, and views.
    """
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT table_name, table_rows, table_type
        FROM information_schema.tables
        WHERE table_schema = %s
        ORDER BY table_type DESC, table_name ASC;
    """, (DB_CONFIG["database"],))
    tables = cursor.fetchall()

    summary_table = Table(
        title="[bold green]Database Catalog & Row Counts[/]",
        show_header=True,
        header_style="bold magenta",
        expand=True
    )
    summary_table.add_column("Entity Name", style="cyan")
    summary_table.add_column("Type", style="yellow")
    summary_table.add_column("Estimated Rows", justify="right", style="green")

    for t in tables:
        # Fetch exact row count for base tables
        row_count = t["table_rows"]
        if t["table_type"] == "BASE TABLE":
            try:
                c2 = conn.cursor()
                c2.execute(f"SELECT COUNT(*) FROM `{t['table_name']}`")
                row_count = c2.fetchone()[0]
                c2.close()
            except Exception:
                pass
        else:
            row_count = "[dim]View[/dim]"

        summary_table.add_row(
            t["table_name"],
            t["table_type"],
            str(row_count)
        )

    console.print(summary_table)
    cursor.close()


def run_init():
    """
    Main migration runner.
    """
    console.print(Panel(
        f"[bold white]Smart Blood Bank - Automated Database Migrator[/]\n"
        f"[dim]Target: {DB_CONFIG['user']}@{DB_CONFIG['host']}:{DB_CONFIG['port']} -> {DB_CONFIG['database']}[/]",
        border_style="cyan"
    ))

    # Step 1: Connect to server without database to create target DB if not present
    try:
        conn_server = get_db_connection(use_database=False)
        server_cursor = conn_server.cursor()
        server_cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_CONFIG['database']}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        conn_server.commit()
        server_cursor.close()
        conn_server.close()
        console.print(f"[bold green]✓[/] Database [cyan]`{DB_CONFIG['database']}`[/] verified/created.")
    except Exception as ex:
        console.print(f"[bold red]Failed to connect to MySQL server:[/] {ex}")
        sys.exit(1)

    # Step 2: Connect to target database and execute scripts
    base_dir = os.path.dirname(os.path.abspath(__file__))
    files_to_run = [
        ("schema.sql", "DDL Schema & Constraints"),
        ("seed.sql", "DML Seed Data & Matrices"),
        ("advanced_db.sql", "Triggers, Procedures & Views")
    ]

    try:
        conn = get_db_connection(use_database=True)
        total_executed = 0

        for filename, label in files_to_run:
            file_path = os.path.join(base_dir, filename)
            count = execute_sql_file(conn, file_path, label)
            total_executed += count
            console.print(f"[bold green]✓[/] {label}: [green]{count} statements executed successfully.[/]")

        console.print("\n[bold green]All database objects created and seeded successfully![/]\n")
        print_database_summary(conn)
        conn.close()

    except Exception as ex:
        console.print(f"\n[bold red]Database migration aborted due to error:[/] {ex}")
        sys.exit(1)


if __name__ == "__main__":
    run_init()
