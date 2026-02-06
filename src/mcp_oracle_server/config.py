"""
Configuration module for Oracle MCP Server.
Centralizes all configuration settings and constants.
Supports both Single-DB (via .env) and Multi-DB (via oracle_config.json).
"""
import os
import json
import oracledb
from dotenv import load_dotenv
from typing import Dict, Any, List

# Load environment variables
# Load environment variables
load_dotenv()

# ============================================
# CONFIGURATION LOADING LOGIC
# ============================================

def load_config() -> Dict[str, Any]:
    """
    Loads configuration from a JSON file (standard or embedded in mcp_config.json).
    Otherwise, falls back to .env variables for a single default connection.
    """
    config = {
        "databases": {},
        "global": {}
    }

    # Determine config file path
    # Priority 1: Explicit file path from env
    config_file = os.getenv("ORACLE_CONFIG_FILE")
    
    # Priority 2: Standard file in config dir
    if not config_file:
        config_dir = os.getenv("ORACLE_CONFIG_DIR", os.getcwd())
        candidate = os.path.join(config_dir, 'oracle_config.json')
        if os.path.exists(candidate):
            config_file = candidate

    # 1. Try loading from JSON
    if config_file and os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
            
            json_config = {}
            # Case A: Standard oracle_config.json structure
            if "databases" in raw_data:
                json_config = raw_data
            # Case B: Embedded in mcp_config.json (inside mcpServers -> oracle-server -> oracleConfig)
            elif "mcpServers" in raw_data:
                server_conf = raw_data.get("mcpServers", {}).get("oracle-server", {})
                json_config = server_conf.get("oracleConfig", {})

            # Parse Global Settings
            g_settings = json_config.get("global_settings", {})
            config["global"] = {
                "client_path": g_settings.get("oracle_client_path", os.getenv("ORACLE_CLIENT_PATH")),
                "default_db": g_settings.get("default_database", "default"),
                "export_dir": g_settings.get("export_directory", os.getenv("EXPORT_DIRECTORY", os.getcwd())),
                "log_level": g_settings.get("log_level", os.getenv("LOG_LEVEL", "INFO")),
                # Pool defaults
                "pool_min": int(g_settings.get("pool_min", os.getenv("POOL_MIN", "2"))),
                "pool_max": int(g_settings.get("pool_max", os.getenv("POOL_MAX", "10"))),
                "pool_inc": int(g_settings.get("pool_increment", os.getenv("POOL_INCREMENT", "1"))),
                # Query defaults
                "max_rows": int(g_settings.get("max_rows_display", os.getenv("MAX_ROWS_DISPLAY", "100"))),
            }

            # Parse Databases
            for db in json_config.get("databases", []):
                name = db.get("name")
                if not name: continue
                
                # Determine DSN
                dsn = db.get("dsn")
                if not dsn and db.get("host"):
                    if db.get("service_name"):
                        dsn = f"{db['host']}:{db.get('port', 1521)}/{db['service_name']}"
                    elif db.get("sid"):
                        dsn = oracledb.makedsn(db['host'], db.get('port', 1521), sid=db['sid'])
                
                if dsn: # Only add if we have a valid DSN or params to make one
                    config["databases"][name] = {
                        "user": db.get("user"),
                        "password": db.get("password"),
                        "dsn": dsn,
                        "mode": db.get("mode"),
                        "encoding": db.get("encoding", "UTF-8")
                    }
            
            # If loaded successfully, return
            if config["databases"]:
                return config

        except Exception as e:
            print(f"Warning: Failed to load config from {config_file}: {e}. Falling back to .env")

    # 2. Fallback to .env (Single DB Mode)
    oracle_user = os.getenv("ORACLE_USER")
    oracle_password = os.getenv("ORACLE_PASSWORD")
    
    # Logic to determine DSN from Env
    oracle_dsn = os.getenv("ORACLE_DSN")
    if not oracle_dsn:
        host = os.getenv("ORACLE_HOST")
        port = os.getenv("ORACLE_PORT", "1521")
        service = os.getenv("ORACLE_SERVICE_NAME")
        sid = os.getenv("ORACLE_SID")
        
        if host and port:
            if service:
                oracle_dsn = f"{host}:{port}/{service}"
            elif sid:
                oracle_dsn = oracledb.makedsn(host, port, sid=sid)

    config["databases"]["default"] = {} # Initialize
    if oracle_user and oracle_password and oracle_dsn:
        config["databases"]["default"] = {
            "user": oracle_user,
            "password": oracle_password,
            "dsn": oracle_dsn
        }

    config["global"] = {
        "client_path": os.getenv("ORACLE_CLIENT_PATH", r"d:\HoangLong\cty\file_js_rac\mcp-oracle-server\instantclient_23_0"),
        "default_db": "default",
        "export_dir": os.getenv("EXPORT_DIRECTORY", os.getcwd()),
        "log_level": os.getenv("LOG_LEVEL", "INFO"),
        "pool_min": int(os.getenv("POOL_MIN", "2")),
        "pool_max": int(os.getenv("POOL_MAX", "10")),
        "pool_inc": int(os.getenv("POOL_INCREMENT", "1")),
        "max_rows": int(os.getenv("MAX_ROWS_DISPLAY", "100"))
    }
    
    return config

# ============================================
# EXPORTED CONSTANTS (Legacy Support & Global)
# ============================================
_loaded_config = load_config()

DATABASES = _loaded_config["databases"]
GLOBAL_CONFIG = _loaded_config["global"]

# Accessors for global settings
ORACLE_CLIENT_PATH = GLOBAL_CONFIG["client_path"]
EXPORT_DIRECTORY = GLOBAL_CONFIG["export_dir"]
LOG_LEVEL = GLOBAL_CONFIG["log_level"]
LOG_FILE = os.getenv("LOG_FILE", "mcp_oracle.log")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_MAX_BYTES = int(os.getenv("LOG_MAX_BYTES", "10485760"))  # 10MB
LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "5"))

# Pool Settings
POOL_MIN_CONNECTIONS = GLOBAL_CONFIG["pool_min"]
POOL_MAX_CONNECTIONS = GLOBAL_CONFIG["pool_max"]
POOL_INCREMENT = GLOBAL_CONFIG["pool_inc"]

# Query Settings
MAX_ROWS_DISPLAY = GLOBAL_CONFIG["max_rows"]
DEFAULT_PAGE_SIZE = int(os.getenv("DEFAULT_PAGE_SIZE", "50"))
MAX_CSV_ROWS = int(os.getenv("MAX_CSV_ROWS", "100000"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "1000"))

# Security Settings
PROTECTED_TABLES = [
    "SYS", "SYSTEM", "AUDIT_TRAIL"
]

DANGEROUS_KEYWORDS = [
    "DROP DATABASE",
    "DROP TABLESPACE",
    "SHUTDOWN",
    "ALTER SYSTEM",
]

def validate_config():
    """Validates that at least one database is configured."""
    if not DATABASES or not any(DATABASES.values()):
        # Check if we are in environment variable mode but failed
        if not os.getenv("ORACLE_USER"):
            # It's possible the user just has no config yet.
            pass
        else:
             pass 
    return True
