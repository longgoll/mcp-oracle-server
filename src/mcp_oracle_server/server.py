"""
Oracle Database MCP Server - Enhanced Version (Multi-Database Support)
A comprehensive Model Context Protocol server for Oracle Database operations.
Supports multiple database connections and intelligent object discovery.
"""
import os
import oracledb
import csv
import time
import re
from contextlib import contextmanager
from typing import Optional, List, Tuple, Dict, Any, Union
import json
import pandas as pd
from faker import Faker

from mcp.server.fastmcp import FastMCP
from .config import (
    DATABASES, GLOBAL_CONFIG, ORACLE_CLIENT_PATH,
    POOL_MIN_CONNECTIONS, POOL_MAX_CONNECTIONS, POOL_INCREMENT,
    MAX_ROWS_DISPLAY, DEFAULT_PAGE_SIZE, MAX_CSV_ROWS, BATCH_SIZE,
    PROTECTED_TABLES, DANGEROUS_KEYWORDS, EXPORT_DIRECTORY, validate_config
)
from .logger import logger, query_logger

# Initialize MCP Server
mcp = FastMCP("Oracle Database Manager")
_pools: Dict[str, oracledb.ConnectionPool] = {}
_oracle_client_initialized = False

# ============================================
# CONNECTION MANAGEMENT
# ============================================

def init_oracle_client():
    """Initializes Oracle Client in Thick Mode (Global, once)."""
    global _oracle_client_initialized
    if not _oracle_client_initialized:
        try:
            oracledb.init_oracle_client(lib_dir=ORACLE_CLIENT_PATH)
            logger.info("Oracle Client initialized successfully")
            _oracle_client_initialized = True
        except oracledb.DatabaseError as e:
            if "DPY-1001" not in str(e): # Already initialized
                logger.warning(f"Oracle Client init warning: {e}")
            _oracle_client_initialized = True

def get_pool(db_name: Optional[str] = None) -> oracledb.ConnectionPool:
    """Gets or creates the connection pool for a specific database."""
    global _pools
    
    # Resolve Database Name
    if not db_name:
        db_name = GLOBAL_CONFIG["default_db"]
    
    if db_name not in DATABASES:
        # Fallback: if only one DB exists, use it? No, strict is better, or prompt AI.
        # But if 'default' is not in DATABASES (e.g. config.json used different names), pick first.
        if "default" not in DATABASES and len(DATABASES) > 0:
             # If user didn't specify and default is invalid, pick the first one available
             db_name = list(DATABASES.keys())[0]
        else:
             raise ValueError(f"Database '{db_name}' not defined in configuration. Available: {list(DATABASES.keys())}")

    if db_name not in _pools:
        validate_config()
        init_oracle_client()
        
        db_conf = DATABASES[db_name]
        try:
            # For SYSDBA mode, we cannot use pool - must use direct connection
            if db_conf.get("mode", "").upper() == "SYSDBA":
                _pools[db_name] = None  # Signal to use direct connection
                logger.info(f"SYSDBA mode configured for '{db_name}' - will use direct connections")
            else:
                pool = oracledb.create_pool(
                    user=db_conf["user"],
                    password=db_conf["password"],
                    dsn=db_conf["dsn"],
                    min=POOL_MIN_CONNECTIONS,
                    max=POOL_MAX_CONNECTIONS,
                    increment=POOL_INCREMENT
                )
                _pools[db_name] = pool
                logger.info(f"Connection pool created for '{db_name}'")
        except Exception as e:
             logger.error(f"Failed to create pool for '{db_name}': {e}")
             raise

    return _pools.get(db_name)

@contextmanager
def get_connection(db_name: Optional[str] = None):
    """Context manager for getting a connection from pool or direct for SYSDBA."""
    try:
        # Resolve Database Name
        if not db_name:
            db_name = GLOBAL_CONFIG["default_db"]
        
        if db_name not in DATABASES:
            if "default" not in DATABASES and len(DATABASES) > 0:
                db_name = list(DATABASES.keys())[0]
            else:
                raise ValueError(f"Database '{db_name}' not defined.")
        
        # Ensure pool/config is initialized
        get_pool(db_name)
        
        db_conf = DATABASES[db_name]
        
        # Check if SYSDBA mode - use direct connection
        if db_conf.get("mode", "").upper() == "SYSDBA":
            conn = oracledb.connect(
                user=db_conf["user"],
                password=db_conf["password"],
                dsn=db_conf["dsn"],
                mode=oracledb.SYSDBA
            )
            try:
                yield conn
            finally:
                conn.close()
        else:
            # Use pool
            pool = _pools[db_name]
            conn = pool.acquire()
            try:
                yield conn
            finally:
                pool.release(conn)
    except Exception as e:
        logger.error(f"Connection error (DB: {db_name}): {e}")
        raise

# ============================================
# SECURITY & VALIDATION UTILITIES
# ============================================

def validate_identifier(name: str) -> bool:
    """Validates that a name is a safe SQL identifier."""
    if not name:
        return False
    # Allow . for schema.table notation
    pattern = r'^[A-Za-z][A-Za-z0-9_$#\.]*$' 
    return bool(re.match(pattern, name)) and len(name) <= 128

def check_table_exists(cursor, table_name: str) -> bool:
    """Checks if a table exists."""
    # Handle Schema.Table format
    owner = None
    if "." in table_name:
        parts = table_name.split(".")
        owner = parts[0].upper()
        name = parts[1].upper()
    else:
        name = table_name.upper()

    if owner:
         cursor.execute("SELECT COUNT(*) FROM all_tables WHERE owner = :o AND table_name = :tn", o=owner, tn=name)
    else:
         cursor.execute("SELECT COUNT(*) FROM user_tables WHERE table_name = :tn", tn=name)
         
    return cursor.fetchone()[0] > 0

def check_dangerous_query(query: str) -> Optional[str]:
    """Checks for dangerous keywords."""
    upper_query = query.upper()
    for keyword in DANGEROUS_KEYWORDS:
        if keyword in upper_query:
            return keyword
    return None

def get_object_type(cursor, object_name: str) -> Optional[str]:
    """Helper to detect object type."""
    try:
        cursor.execute("SELECT object_type FROM user_objects WHERE object_name = :n", n=object_name.upper())
        row = cursor.fetchone()
        return row[0] if row else None
    except:
        return None

def format_as_markdown_table(columns: List[str], rows: List[Tuple], max_rows: int = None) -> str:
    """Formats results as Markdown table."""
    if not rows:
        return "No results."
    display_rows = rows[:max_rows] if max_rows else rows
    header = " | ".join(str(c) for c in columns)
    separator = " | ".join(["---"] * len(columns))
    lines = [header, separator]
    for row in display_rows:
        lines.append(" | ".join(str(item) if item is not None else "NULL" for item in row))
    if max_rows and len(rows) > max_rows:
        lines.append(f"\n*... and {len(rows) - max_rows} more rows*")
    return "\n".join(lines)

def format_bytes(size_bytes: int) -> str:
    """Formats bytes into human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"

# ============================================
# DISCOVERY & MULTI-DB TOOLS
# ============================================

@mcp.tool()
def list_databases() -> str:
    """
    Lists all configured database connections. 
    Use this to see available environments (e.g. dev, prod).
    """
    if not DATABASES:
        return "No databases configured."
    
    result = "## Configured Databases\n\n"
    result += "| Name | User | DSN | Status |\n|---|---|---|---|\n"
    
    for name, conf in DATABASES.items():
        status = "Active" if name in _pools else "Idle"
        result += f"| **{name}** | {conf['user']} | {conf['dsn']} | {status} |\n"
        
    result += f"\n**Default Database**: `{GLOBAL_CONFIG['default_db']}`"
    return result

@mcp.tool()
def locate_table(table_name: str) -> str:
    """
    Global Search: Finds which database(s) contain a specific table.
    CRITICAL: ALWAYS run this first if you are unsure which database to query.
    """
    if not validate_identifier(table_name):
        return "Error: Invalid table name."
        
    matches = []
    
    # Iterate through all configured databases
    for db_name in DATABASES.keys():
        try:
            with get_connection(db_name) as conn:
                cursor = conn.cursor()
                if check_table_exists(cursor, table_name):
                    matches.append(db_name)
                cursor.close()
        except Exception:
            # Ignore connection errors during discovery
            pass
            
    if not matches:
        return f"❌ Table `{table_name}` NOT found in any connected databases."
    
    if len(matches) == 1:
        return f"✅ **FOUND**: Table `{table_name}` is unique to database **`{matches[0]}`**.\nYou should proceed using `database_name='{matches[0]}'`."
    
    return f"⚠️ **AMBIGUOUS**: Table `{table_name}` found in **MULTIPLE** databases: `{', '.join(matches)}`.\n\n**PROTOCOL**: You MUST ask the user which database they want to use."

# ============================================
# BASIC DATABASE TOOLS
# ============================================

@mcp.tool()
def list_tables(database_name: str = None) -> str:
    """Lists all tables in the specified database (or default)."""
    start_time = time.time()
    try:
        with get_connection(database_name) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT table_name FROM user_tables ORDER BY table_name")
                tables = [row[0] for row in cursor.fetchall()]
                duration = (time.time() - start_time) * 1000
                
                db_label = f"[{database_name or 'Default'}]"
                if not tables:
                    return f"{db_label} No tables found."
                return f"{db_label} Found {len(tables)} tables:\n" + "\n".join(f"- {t}" for t in tables)
            finally:
                cursor.close()
    except Exception as e:
        return f"Error listing tables: {str(e)}"

@mcp.tool()
def describe_table(table_name: str, database_name: str = None) -> str:
    """Gets the schema/structure of a table. Optional: specify database."""
    if not validate_identifier(table_name):
        return "Error: Invalid table name format."
    try:
        with get_connection(database_name) as conn:
            cursor = conn.cursor()
            try:
                if not check_table_exists(cursor, table_name):
                    return f"Table '{table_name}' not found in database '{database_name or 'Default'}'."
                
                # Check column metadata
                query = """
                    SELECT column_name, data_type, data_length, data_precision, data_scale, nullable, data_default
                    FROM user_tab_columns WHERE table_name = :tn ORDER BY column_id
                """
                # Handle schema prefix if present for query execution? 
                # user_tab_columns only shows current schema. If table_name has schema prefix (HR.EMP), we need all_tab_columns
                if "." in table_name:
                    query = query.replace("user_tab_columns", "all_tab_columns")
                    # We also need to owner filter, but keeping it simple for now or rely on synonym/grants
                    # For robust fix:
                    parts = table_name.split(".")
                    # Ideally we filter by owner. But let's stick to standard usage first.
                
                cursor.execute(query, tn=table_name.split(".")[-1].upper())
                columns = cursor.fetchall()
                
                result = f"## Schema for `{table_name.upper()}` (DB: {database_name or 'Default'})\n\n"
                result += f"| {'Column':<30} | {'Type':<20} | {'Nullable':<8} |\n"
                result += f"|{'-'*31}|{'-'*21}|{'-'*9}|\n"
                for col in columns:
                    col_name, data_type, length, precision, scale, nullable, default = col
                    if data_type in ('VARCHAR2', 'CHAR', 'NVARCHAR2', 'NCHAR'):
                        type_str = f"{data_type}({length})"
                    elif data_type == 'NUMBER' and precision:
                        type_str = f"NUMBER({precision},{scale or 0})"
                    else:
                        type_str = data_type
                    result += f"| {col_name:<30} | {type_str:<20} | {nullable:<8} |\n"
                return result
            finally:
                cursor.close()
    except Exception as e:
        return f"Error describing table: {str(e)}"

# ============================================
# ADVANCED INSPECTION TOOLS
# ============================================

@mcp.tool()
def list_constraints(table_name: str, database_name: str = None) -> str:
    """Lists constraints (Primary Key, Foreign Key, Check, Unique) for a table."""
    with get_connection(database_name) as conn:
        cursor = conn.cursor()
        try:
            sql = """
                SELECT c.constraint_name, c.constraint_type, c.search_condition, 
                       cc.column_name, c.r_constraint_name
                FROM user_constraints c
                JOIN user_cons_columns cc ON c.constraint_name = cc.constraint_name
                WHERE c.table_name = :tn
                ORDER BY c.constraint_type, c.constraint_name, cc.position
            """
            cursor.execute(sql, tn=table_name.upper())
            rows = cursor.fetchall()
            
            if not rows: return f"No constraints found for `{table_name}`."
            
            result = f"## Constraints for `{table_name}`\n\n"
            result += "| Name | Type | Column | Details |\n|---|---|---|---|\n"
            
            type_map = {'P': 'Primary Key', 'R': 'Foreign Key', 'U': 'Unique', 'C': 'Check'}
            
            for row in rows:
                c_name, c_type, cond, col, r_name = row
                details = str(cond) if cond else (f"Ref: {r_name}" if r_name else "")
                t_str = type_map.get(c_type, c_type)
                result += f"| {c_name} | {t_str} | {col} | {details} |\n"
            return result
        except Exception as e:
            return f"Error: {e}"
        finally:
            cursor.close()

@mcp.tool()
def list_indexes(table_name: str, database_name: str = None) -> str:
    """Lists indexes on a specific table."""
    with get_connection(database_name) as conn:
        cursor = conn.cursor()
        try:
            sql = """
                SELECT i.index_name, i.index_type, i.uniqueness,
                       LISTAGG(ic.column_name, ', ') WITHIN GROUP (ORDER BY ic.column_position) as columns
                FROM user_indexes i
                JOIN user_ind_columns ic ON i.index_name = ic.index_name
                WHERE i.table_name = :tn
                GROUP BY i.index_name, i.index_type, i.uniqueness
            """
            cursor.execute(sql, tn=table_name.upper())
            rows = cursor.fetchall()
            
            if not rows: return f"No indexes found for `{table_name}`."
            
            result = f"## Indexes for `{table_name}`\n\n"
            result += "| Index Name | Type | Unique | Columns |\n|---|---|---|---|\n"
            for row in rows:
                result += f"| {row[0]} | {row[1]} | {row[2]} | {row[3]} |\n"
            return result
        except Exception as e:
            return f"Error: {e}"
        finally:
            cursor.close()

@mcp.tool()
def get_object_ddl(object_name: str, object_type: str = "TABLE", database_name: str = None) -> str:
    """
    Gets the detailed DDL or source code for an object.
    Supported types: TABLE, VIEW, PROCEDURE, FUNCTION, PACKAGE, TRIGGER, INDEX.
    """
    with get_connection(database_name) as conn:
        cursor = conn.cursor()
        try:
            # Normalize type
            obj_type = object_type.upper().strip()
            
            # Use DBMS_METADATA
            # Note: For PACKAGE BODY, use type 'PACKAGE_BODY'
            query = "SELECT DBMS_METADATA.GET_DDL(:type, :name) FROM DUAL"
            cursor.execute(query, type=obj_type, name=object_name.upper())
            
            lob = cursor.fetchone()
            if not lob or not lob[0]: return f"No DDL found for {object_name} ({obj_type})."
            ddl = lob[0].read()
            return f"## DDL for `{object_name}` ({obj_type})\n```sql\n{ddl}\n```"
        except Exception as e:
            # Fallback for View Source specifically if DDL fails (sometimes simpler)
            return f"Error getting DDL: {e}\n(Ensure object exists and type '{obj_type}' is correct)"
        finally:
            cursor.close()

@mcp.tool()
def run_read_only_query(sql_query: str, database_name: str = None) -> str:
    """Executes a READ-ONLY SQL query (SELECT only)."""
    normalized = sql_query.strip().upper()
    if not normalized.startswith("SELECT") and not normalized.startswith("WITH"):
        return "Error: Only SELECT queries are allowed."
        
    danger = check_dangerous_query(sql_query)
    if danger: return f"Error: Query contains blocked keyword: {danger}"
    
    dml_keywords = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "CREATE"]
    for kw in dml_keywords:
        if kw in normalized.split(): # Basic token check
            # Be careful with subqueries/comments, but strict safe for now
             pass # Regex is better, but this is a quick safety net
    
    start_time = time.time()
    try:
        with get_connection(database_name) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(sql_query)
                if not cursor.description:
                     return "Query executed but returned no results (no cursor description)."
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchmany(MAX_ROWS_DISPLAY + 1)
                duration = (time.time() - start_time) * 1000
                
                query_logger.log_query(sql_query[:200], duration, len(rows))
                
                if not rows:
                    return f"[DB: {database_name or 'Default'}] Query returned no results."
                
                has_more = len(rows) > MAX_ROWS_DISPLAY
                display_rows = rows[:MAX_ROWS_DISPLAY]
                
                result = f"## Results (DB: {database_name or 'Default'})\n"
                result += format_as_markdown_table(columns, display_rows)
                if has_more:
                    result += f"\n\n*Showing first {MAX_ROWS_DISPLAY} rows.*"
                result += f"\n\n*Query executed in {duration:.2f}ms*"
                return result
            finally:
                cursor.close()
    except Exception as e:
        return f"Database Error ({database_name or 'Default'}): {str(e)}"

@mcp.tool()
def explain_query_plan(sql_query: str, database_name: str = None) -> str:
    """
    Gets the Execution Plan for a query to analyze performance.
    Useful for optimizing slow queries.
    """
    with get_connection(database_name) as conn:
        cursor = conn.cursor()
        try:
            # Generate a unique statement ID
            stmt_id = f"MCP_{int(time.time())}"
            
            # 1. Explain
            explain_sql = f"EXPLAIN PLAN SET STATEMENT_ID = '{stmt_id}' FOR {sql_query}"
            cursor.execute(explain_sql)
            
            # 2. Retrieve Plan
            cursor.execute(f"SELECT * FROM TABLE(DBMS_XPLAN.DISPLAY(NULL, '{stmt_id}'))")
            rows = cursor.fetchall()
            
            output = "\n".join([r[0] for r in rows if r[0]])
            return f"## Execution Plan\n```text\n{output}\n```"
        except Exception as e:
            return f"Error explaining plan: {e}"
        finally:
             cursor.close()

@mcp.tool()
def export_query_to_csv(sql_query: str, filename: str, output_path: str = None, database_name: str = None) -> str:
    """
    Exports query results to a CSV file.
    output_path: Optional absolute path to save the file (e.g. 'D:/Data/report.csv').
    If output_path is provided, 'filename' is ignored (or used as fallback if path is a dir).
    If output_path is NOT provided, saves to configured EXPORT_DIRECTORY with 'filename'.
    """
    # Determine full path
    if output_path:
        # Check if user made a directory or file path
        if os.path.isdir(output_path):
            full_path = os.path.join(output_path, filename)
        else:
             full_path = output_path
    else:
        full_path = os.path.join(EXPORT_DIRECTORY, filename)

    if not full_path.lower().endswith('.csv'):
        full_path += '.csv'
        
    try:
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
    except Exception as e:
        return f"Error creating directory for {full_path}: {e}"
    
    with get_connection(database_name) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(sql_query)
            if not cursor.description:
                return "Query returned no results."
                
            headers = [col[0] for col in cursor.description]
            
            with open(full_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                
                rows_written = 0
                while True:
                    rows = cursor.fetchmany(BATCH_SIZE)
                    if not rows: break
                    writer.writerows(rows)
                    rows_written += len(rows)
                    if rows_written >= MAX_CSV_ROWS:
                        break
                        
            return f"✅ Exported {rows_written} rows to: `{full_path}`"
        except Exception as e:
            return f"Export failed: {e}"
        finally:
            cursor.close()

@mcp.tool()
def run_query_with_pagination(sql_query: str, page: int = 1, page_size: int = 50, database_name: str = None) -> str:
    """Executes a SELECT query with pagination. Returns a specific page of results."""
    if page < 1: return "Error: Page number must be >= 1"
    
    offset = (page - 1) * page_size
    paginated_query = f"SELECT * FROM ({sql_query}) OFFSET {offset} ROWS FETCH NEXT {page_size} ROWS ONLY"
    count_query = f"SELECT COUNT(*) FROM ({sql_query})"
    
    start_time = time.time()
    try:
        with get_connection(database_name) as conn:
            cursor = conn.cursor()
            try:
                # Get Count
                cursor.execute(count_query)
                total_rows = cursor.fetchone()[0]
                total_pages = (total_rows + page_size - 1) // page_size
                
                # Get Data
                cursor.execute(paginated_query)
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                duration = (time.time() - start_time) * 1000
                
                result = f"## Page {page} of {total_pages} (Total: {total_rows:,} | DB: {database_name or 'Default'})\n\n"
                if not rows:
                    result += "No results on this page."
                else:
                    result += format_as_markdown_table(columns, rows)
                return result
            finally:
                cursor.close()
    except Exception as e:
        return f"Pagination Error: {str(e)}"

@mcp.tool()
def run_modification_query(sql_query: str, database_name: str = None) -> str:
    """Executes DML/DDL commands. Auto-commits. CAUTION: Ensure correct database_name!"""
    normalized = sql_query.strip().upper()
    if normalized.startswith("SELECT"):
        return "For SELECT queries, use 'run_read_only_query' instead."
        
    # Validation logic (simplified)
    if "DROP" in normalized: return "Error: DROP operations are blocked."
    
    start_time = time.time()
    try:
        with get_connection(database_name) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(sql_query)
                rows_affected = cursor.rowcount
                conn.commit()
                duration = (time.time() - start_time) * 1000
                
                query_logger.log_query(sql_query[:200], duration, rows_affected)
                return f"✅ [DB: {database_name or 'Default'}] Query executed successfully.\n- Rows affected: {rows_affected}\n- Duration: {duration:.2f}ms"
            except Exception as e:
                conn.rollback()
                return f"❌ Execution failed (Rolled back): {str(e)}"
            finally:
                cursor.close()
    except Exception as e:
        return f"Connection Error: {str(e)}"

# ============================================
# DDL & METADATA TOOLS (Updated with db_name)
# ============================================

# Note: get_table_ddl is deprecated in favor of get_object_ddl, but kept for compatibility if needed.
# We will alias it or let the user use get_object_ddl. 
# actually let's remove it to avoid clutter since get_object_ddl covers it.
# Or keep existing function for simpler prompt matching.
@mcp.tool()
def get_table_ddl(table_name: str, database_name: str = None) -> str:
    """(Deprecated) Gets the detailed DDL for a table. Use get_object_ddl instead."""
    return get_object_ddl(table_name, "TABLE", database_name)

# ============================================
# ADVANCED MANAGEMENT TOOLS
# ============================================

@mcp.tool()
def inspect_locks(database_name: str = None) -> str:
    """
    Checks for blocking sessions and locked objects.
    Useful when the database seems 'stuck'.
    """
    with get_connection(database_name) as conn:
        cursor = conn.cursor()
        try:
            # Simple wrapper for common lock view
            sql = """
                SELECT 
                    s.sid, s.serial#, s.username, s.program,
                    l.type, l.lmode,
                    o.object_name, o.object_type,
                    CASE WHEN l.block > 0 THEN 'BLOCKING' ELSE 'WAITING' END as state
                FROM v$session s
                JOIN v$lock l ON s.sid = l.sid
                LEFT JOIN dba_objects o ON l.id1 = o.object_id
                WHERE s.type != 'BACKGROUND'
                AND (l.block > 0 OR l.request > 0)
            """
            cursor.execute(sql)
            rows = cursor.fetchall()
            if not rows: return "✅ No significant locks or blocking sessions found."
            
            result = "## Locks & Blocking Sessions\n\n"
            result += "| SID | Serial | User | Object | State |\n|---|---|---|---|---|\n"
            for r in rows:
                result += f"| {r[0]} | {r[1]} | {r[2]} | {r[6] or 'N/A'} | {r[8]} |\n"
            return result
        except Exception as e:
            return f"Error inspecting locks (Permissions?): {e}"
        finally:
            cursor.close()

@mcp.tool()
def kill_session(sid: int, serial: int, database_name: str = None) -> str:
    """
    Kills a specific database session.
    WARNING: Use with caution. Only use if `inspect_locks` shows a problem.
    """
    with get_connection(database_name) as conn:
        cursor = conn.cursor()
        try:
            sql = f"ALTER SYSTEM KILL SESSION '{sid},{serial}' IMMEDIATE"
            cursor.execute(sql)
            return f"✅ Session {sid},{serial} killed successfully."
        except Exception as e:
            return f"❌ Failed to kill session: {e}"
        finally:
            cursor.close()

@mcp.tool()
def search_in_table(table_name: str, search_term: str, database_name: str = None) -> str:
    """Searches for text in a table."""
    try:
        with get_connection(database_name) as conn:
            cursor = conn.cursor()
            try:
                # (Simplified logic - getting text columns)
                cursor.execute("""
                    SELECT column_name FROM user_tab_columns
                    WHERE table_name = :tn AND data_type IN ('CHAR','VARCHAR2')
                """, tn=table_name.upper())
                cols = [r[0] for r in cursor.fetchall()]
                if not cols: return "No text columns found."
                
                where = " OR ".join([f"UPPER({c}) LIKE UPPER(:t)" for c in cols])
                sql = f"SELECT * FROM {table_name.upper()} WHERE {where} FETCH FIRST 20 ROWS ONLY"
                cursor.execute(sql, t=f"%{search_term}%")
                rows = cursor.fetchall()
                cols_desc = [c[0] for c in cursor.description]
                return f"## Search Results ({database_name or 'Default'})\n" + format_as_markdown_table(cols_desc, rows)
            finally:
                cursor.close()
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def get_session_info() -> str:
    """Returns detailed information about ALL current database sessions/pools."""
    global _pools
    if not _pools:
        return "No active connection pools."
        
    result = "## System Session Info\n\n"
    
    for name, pool in _pools.items():
        result += f"### Database: {name}\n"
        result += f"- **Pool Status**: Open={pool.opened}, Busy={pool.busy}\n"
        try:
            with pool.acquire() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT SYS_CONTEXT('USERENV','DB_NAME'), SYS_CONTEXT('USERENV','SESSION_USER') FROM DUAL")
                row = cursor.fetchone()
                result += f"- **Connected as**: {row[1]} @ {row[0]}\n"
                result += f"- **Version**: {conn.version}\n"
                cursor.close()
        except Exception as e:
            result += f"- **Check**: Failed to acquire test connection ({e})\n"
        result += "\n"
        
    return result


# ============================================
# IMPORT TOOLS (Human-in-the-loop)
# ============================================

@mcp.tool()
def analyze_import_file(file_path: str, table_name: str, database_name: str = None) -> str:
    """
    Step 1 of Import: Analyzes a file (CSV/Excel) against a target table schema.
    Returns a 'mapping proposal' and report.
    Does NOT modify the database.
    """
    if not os.path.exists(file_path):
        return f"Error: File not found at {file_path}"
    
    # 1. Read File Header
    try:
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path, nrows=5)
        elif file_path.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(file_path, nrows=5)
        else:
            return "Error: Unsupported file type. Use .csv or .xlsx"
    except Exception as e:
        return f"Error reading file: {e}"
        
    file_cols = [c.strip() for c in df.columns]
    
    # 2. Get Database Schema
    with get_connection(database_name) as conn:
        cursor = conn.cursor()
        try:
            if not check_table_exists(cursor, table_name):
                return f"Error: Table '{table_name}' does not exist in DB '{database_name or 'Default'}'."
                
            # standardized column fetching
            owner = None
            t_name = table_name.upper()
            if "." in t_name:
                owner, t_name = t_name.split(".")
                
            if owner:
                sql_cols = "SELECT column_name, data_type, nullable FROM all_tab_columns WHERE owner=:o AND table_name=:t"
                cursor.execute(sql_cols, o=owner, t=t_name)
            else:
                sql_cols = "SELECT column_name, data_type, nullable FROM user_tab_columns WHERE table_name=:t"
                cursor.execute(sql_cols, t=t_name)
                
            db_cols_info = cursor.fetchall() # [(COL, TYPE, NULL), ...]
            db_cols = {row[0]: {'type': row[1], 'null': row[2]} for row in db_cols_info}
            
        finally:
            cursor.close()
            
    # 3. Fuzzy Matching Logic
    mapping_proposal = {}
    missing_in_file = []
    extra_in_file = []
    
    used_db_cols = set()
    
    # Normalize for matching (remove _, space, uppercase)
    def normalize(s): return str(s).upper().replace("_", "").replace(" ", "")
    
    # Map File -> DB
    db_col_map = {normalize(k): k for k in db_cols.keys()}
    
    for f_col in file_cols:
        norm_f = normalize(f_col)
        if norm_f in db_col_map:
            db_target = db_col_map[norm_f]
            mapping_proposal[f_col] = db_target
            used_db_cols.add(db_target)
        else:
            extra_in_file.append(f_col)
            
    # Check what's missing in DB (that is required)
    for col, info in db_cols.items():
        if col not in used_db_cols:
            if info['null'] == 'N': # Not Nullable -> Critical
                missing_in_file.append(f"{col} (Required)")
            else:
                missing_in_file.append(col)

    # 4. Generate Report
    report = f"## Import Analysis for `{table_name}`\n"
    report += f"**File**: `{os.path.basename(file_path)}`\n\n"
    
    report += "### 1. Column Mapping Status\n"
    report += f"- ✅ **Matched**: {len(mapping_proposal)} columns\n"
    report += f"- ⚠️ **Missing in File**: {len(missing_in_file)} columns ({', '.join(missing_in_file[:5])}...)\n"
    report += f"- ℹ️ **Extra in File**: {len(extra_in_file)} columns (will be ignored)\n\n"
    
    report += "### 2. Data Preview\n"
    report += format_as_markdown_table(df.columns.tolist(), df.values.tolist(), max_rows=3)
    
    # 5. Instructions for Agent
    json_proposal = json.dumps(mapping_proposal, indent=2)
    
    report += "\n### 3. Action Required\n"
    report += "**STOP! Do not proceed automatically.**\n"
    report += "Ask the user to confirm the mapping below. If they agree, use `import_data_from_file` with this JSON:\n"
    report += f"```json\n{json_proposal}\n```"
    
    return report

# ============================================
# MAINTENANCE & DEV TOOLS (New!)
# ============================================

@mcp.tool()
def list_invalid_objects(database_name: str = None) -> str:
    """
    Lists all Invalid objects in the current schema.
    Useful for developers to check broken procedures/packages.
    """
    with get_connection(database_name) as conn:
        cursor = conn.cursor()
        try:
            sql = """
                SELECT object_name, object_type, last_ddl_time 
                FROM user_objects 
                WHERE status = 'INVALID' 
                ORDER BY object_type, object_name
            """
            cursor.execute(sql)
            rows = cursor.fetchall()
            
            if not rows: return "✅ All objects are VALID."
            
            result = "## ⚠️ Invalid Objects Found\n\n"
            result += "| Object Name | Type | Last Modified |\n|---|---|---|\n"
            for row in rows:
                result += f"| {row[0]} | {row[1]} | {row[2]} |\n"
            
            result += "\nUse `compile_object` to attempt to fix these."
            return result
        except Exception as e:
            return f"Error: {e}"
        finally:
            cursor.close()

@mcp.tool()
def compile_object(object_name: str, object_type: str, database_name: str = None) -> str:
    """
    Attempts to recompile an Invalid object.
    object_type: PROCEDURE, FUNCTION, PACKAGE, VIEW, TRIGGER.
    """
    allowed_types = ["PROCEDURE", "FUNCTION", "PACKAGE", "VIEW", "TRIGGER", "PACKAGE BODY"]
    obj_type = object_type.upper().replace("_", " ") # Handle PACKAGE_BODY -> PACKAGE BODY
    
    if obj_type not in allowed_types:
        return f"Error: Unsupported object type '{object_type}'. Supported: {', '.join(allowed_types)}"
        
    with get_connection(database_name) as conn:
        cursor = conn.cursor()
        try:
            # Safe compilation
            sql = f"ALTER {obj_type} {object_name} COMPILE"
            if obj_type == "PACKAGE BODY":
                # Special syntax for package body sometimes needed or handled by standard 'ALTER PACKAGE name COMPILE BODY'
                # But standard SQL for body is: ALTER PACKAGE <name> COMPILE BODY
                sql = f"ALTER PACKAGE {object_name} COMPILE BODY"
                
            cursor.execute(sql)
            return f"✅ Successfully compiled {obj_type} `{object_name}`."
        except oracledb.DatabaseError as e:
            error, = e.args
            return f"❌ Compilation Failed for `{object_name}`:\n{error.message}"
        finally:
            cursor.close()

@mcp.tool()
def check_tablespace_usage(database_name: str = None) -> str:
    """
    Checks the usage of Tablespaces (Storage monitoring).
    Requires appropriate permissions (usually restricted to DB As usually).
    Will try to run best-effort query.
    """
    with get_connection(database_name) as conn:
        cursor = conn.cursor()
        try:
            # This query attempts to use DBA views. If it fails, we fall back or report error.
            # Calculates Total, Used, Free, % Free
            sql = """
            SELECT 
                df.tablespace_name,
                ROUND(df.bytes / (1024 * 1024), 2) AS total_mb,
                ROUND((df.bytes - fs.bytes) / (1024 * 1024), 2) AS used_mb,
                ROUND(fs.bytes / (1024 * 1024), 2) AS free_mb,
                ROUND((fs.bytes / df.bytes) * 100, 2) AS free_pct
            FROM 
                (SELECT tablespace_name, SUM(bytes) bytes FROM dba_data_files GROUP BY tablespace_name) df,
                (SELECT tablespace_name, SUM(bytes) bytes FROM dba_free_space GROUP BY tablespace_name) fs
            WHERE 
                df.tablespace_name = fs.tablespace_name
            ORDER BY 
                free_pct ASC
            """
            cursor.execute(sql)
            rows = cursor.fetchall()
            
            if not rows: return "No tablespace info found (Permissions?)."
            
            result = "## 💾 Tablespace Usage\n\n"
            result += "| Tablespace | Total (MB) | Used (MB) | Free (MB) | Free % |\n|---|---|---|---|---|\n"
            for r in rows:
                status_icon = "🟢" if r[4] > 20 else ("🟡" if r[4] > 5 else "🔴")
                result += f"| {r[0]} | {r[1]:,} | {r[2]:,} | {r[3]:,} | {status_icon} {r[4]}% |\n"
            return result
        except oracledb.DatabaseError as e:
            if "ORA-00942" in str(e):
                return "❌ Permission Error: Cannot access DBA_DATA_FILES/DBA_FREE_SPACE. This tool requires DBA privileges."
            return f"Error checking storage: {e}"
        finally:
            cursor.close()

@mcp.tool()
def generate_mock_data(table_name: str, row_count: int = 10, database_name: str = None) -> str:
    """
    Generates and inserts fake/mock data into a table for testing.
    Uses 'Faker' library to guess data types.
    """
    if row_count > 1000: return "Error: Max 1000 rows allowed per batch."
    faker = Faker()
    
    with get_connection(database_name) as conn:
        cursor = conn.cursor()
        try:
            # 1. Get Schema
            cursor.execute("SELECT column_name, data_type, data_length FROM user_tab_columns WHERE table_name = :tn ORDER BY column_id", tn=table_name.upper())
            cols_info = cursor.fetchall()
            if not cols_info: return f"Table `{table_name}` not found."
            
            columns = [c[0] for c in cols_info]
            types = {c[0]: c[1] for c in cols_info}
            lengths = {c[0]: c[2] for c in cols_info}
            
            # 2. Generate Data
            data_rows = []
            for _ in range(row_count):
                row_data = []
                for col in columns:
                    dtype = types[col]
                    dlen = lengths[col]
                    val = None
                    
                    # Heuristic for data generation
                    if "ID" in col and dtype == "NUMBER":
                        val = faker.unique.random_int(min=1, max=999999)
                    elif dtype in ("VARCHAR2", "CHAR", "NVARCHAR2"):
                        if "NAME" in col: val = faker.name()
                        elif "EMAIL" in col: val = faker.email()
                        elif "PHONE" in col: val = faker.phone_number()
                        elif "ADDRESS" in col: val = faker.address()
                        elif "CITY" in col: val = faker.city()
                        elif "COUNTRY" in col: val = faker.country()
                        else: val = faker.text(max_nb_chars=min(dlen, 100))
                        
                        # Truncate to fit column length
                        if val and len(val) > dlen:
                            val = val[:dlen]
                            
                    elif dtype == "NUMBER":
                        val = faker.random_int(min=0, max=1000)
                    elif dtype == "DATE":
                        val = faker.date_between(start_date="-1y", end_date="today")
                    elif dtype.startswith("TIMESTAMP"):
                        val = faker.date_time()
                        
                    row_data.append(val)
                data_rows.append(tuple(row_data))
                
            # 3. Insert
            placeholders = ",".join([f":{i+1}" for i in range(len(columns))])
            sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
            
            cursor.executemany(sql, data_rows)
            conn.commit()
            
            return f"✅ Successfully generated and inserted {row_count} rows into `{table_name}`."
            
        except Exception as e:
            conn.rollback()
            return f"Error generating data: {e}"
        finally:
            cursor.close()


@mcp.tool()
def import_data_from_file(file_path: str, table_name: str, column_mapping_json: str, database_name: str = None) -> str:
    """
    Step 2 of Import: Executes the import using a confirmed mapping.
    column_mapping_json: The JSON string returned by step 1 (key=FileCol, val=DBCol).
    """
    try:
        mapping = json.loads(column_mapping_json)
    except:
        return "Error: Invalid JSON format for column_mapping."
        
    start_time = time.time()
    
    # 1. Read Full Data
    try:
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
            
        # 2. Transform Data
        # Keep only mapped columns and rename them to DB columns
        df_mapped = df[list(mapping.keys())].rename(columns=mapping)
        
        # Ensure column order matches the INSERT statement
        final_cols = list(df_mapped.columns)
        
        # Replace NaN with None (NULL)
        df_mapped = df_mapped.where(pd.notnull(df_mapped), None)
        
        data_tuples = [tuple(x) for x in df_mapped.to_numpy()]
        
    except Exception as e:
        return f"Error preparing data: {e}"
        
    # 3. Execute Batch Insert
    with get_connection(database_name) as conn:
        cursor = conn.cursor()
        try:
            # Build SQL
            cols_str = ", ".join(final_cols)
            binds_str = ", ".join([f":{i+1}" for i in range(len(final_cols))])
            sql = f"INSERT INTO {table_name} ({cols_str}) VALUES ({binds_str})"
            
            cursor.executemany(sql, data_tuples)
            conn.commit()
            
            duration = time.time() - start_time
            return f"✅ Validated Import Successful!\n- Imported {len(data_tuples)} rows into `{table_name}`\n- Time: {duration:.2f}s"
            
        except Exception as e:
            conn.rollback()
            return f"❌ Import Failed (Rolled Back): {e}"
        finally:
            cursor.close()

# ============================================
# MAIN ENTRY POINT
# ============================================

if __name__ == "__main__":
    logger.info("Starting Oracle MCP Server (Multi-DB Enabled)...")
    try:
        validate_config()
        # Pre-initialize pools logic could go here, or lazy load
        mcp.run()
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        raise
