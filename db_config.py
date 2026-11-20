"""
Database Configuration and Connection Manager
Smart Blood Bank & Emergency Donor Matching System
"""

import os
from contextlib import contextmanager
from typing import Generator, Tuple, Optional, Any
import mysql.connector
from mysql.connector import errorcode, MySQLConnection
from mysql.connector.cursor import MySQLCursorDict, MySQLCursor

# Load environment variables from .env file if available
def _load_env_file():
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, val = line.split("=", 1)
                        key = key.strip()
                        val = val.strip().strip("\"'")
                        if key not in os.environ:
                            os.environ[key] = val
        except Exception:
            pass

_load_env_file()

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": int(os.environ.get("DB_PORT", 3306)),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", ""),
    "database": os.environ.get("DB_NAME", "smart_blood_bank"),
    "charset": "utf8mb4",
    "use_unicode": True,
    "autocommit": False
}


def get_db_connection(use_database: bool = True) -> MySQLConnection:
    """
    Establishes and returns an active MySQL connection.
    
    Args:
        use_database (bool): If True, connects directly to DB_CONFIG['database'].
                             If False, connects without selecting a database
                             (used for database creation / initialization).
    
    Returns:
        MySQLConnection: Active connection instance.
        
    Raises:
        mysql.connector.Error: Formatted error with actionable troubleshooting advice.
    """
    config = DB_CONFIG.copy()
    if not use_database:
        config.pop("database", None)
        
    try:
        conn = mysql.connector.connect(**config)
        return conn
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            raise ConnectionError(
                f"[Authentication Failed] Invalid username or password for MySQL user '{config['user']}'."
                f"\nPlease verify your DB_PASSWORD in .env or environment variables."
            ) from err
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            raise ConnectionError(
                f"[Database Not Found] Database '{config.get('database')}' does not exist yet."
                f"\nPlease run 'python init_db.py' or import schema.sql to initialize it."
            ) from err
        elif err.errno == 2003:  # CR_CONN_HOST_ERROR
            raise ConnectionError(
                f"[Host Unreachable] Cannot connect to MySQL server at {config['host']}:{config['port']}."
                f"\nPlease ensure MySQL service is running and accessible."
            ) from err
        else:
            raise ConnectionError(f"[MySQL Connection Error {err.errno}]: {err.msg}") from err


@contextmanager
def get_db_cursor(dictionary: bool = True, commit: bool = False) -> Generator[Tuple[MySQLConnection, Any], None, None]:
    """
    Context manager yielding a (connection, cursor) tuple.
    Guarantees clean cursor and connection cleanup, and enforces transaction control.
    
    Args:
        dictionary (bool): If True, rows are returned as dictionaries.
        commit (bool): If True, auto-commits changes on successful exit.
    
    Yields:
        Tuple[MySQLConnection, MySQLCursorDict | MySQLCursor]: Active connection and cursor.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection(use_database=True)
        cursor = conn.cursor(dictionary=dictionary)
        yield conn, cursor
        if commit:
            conn.commit()
    except Exception:
        if conn and conn.is_connected():
            conn.rollback()
        raise
    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass
        if conn is not None and conn.is_connected():
            try:
                conn.close()
            except Exception:
                pass


def test_connection() -> Tuple[bool, str, dict]:
    """
    Runs diagnostic connectivity check against MySQL.
    
    Returns:
        Tuple[bool, str, dict]: (success, status_message, server_info_dict)
    """
    try:
        conn = get_db_connection(use_database=False)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT VERSION() AS version, CURRENT_USER() AS user, @@hostname AS host")
        info = cursor.fetchone() or {}
        
        # Check if target database exists
        cursor.execute("SHOW DATABASES LIKE %s", (DB_CONFIG["database"],))
        db_exists = cursor.fetchone() is not None
        info["database_exists"] = db_exists
        info["target_database"] = DB_CONFIG["database"]
        
        cursor.close()
        conn.close()
        return True, "Successfully connected to MySQL Server.", info
    except Exception as ex:
        return False, str(ex), {}
