# Oracle Database MCP Server 🗄️

[English](README.md) | [Tiếng Việt](README.vi.md)

A comprehensive **Model Context Protocol (MCP)** server for Oracle Database operations. This server enables AI assistants to interact with Oracle databases through a secure, well-defined interface.

## 🌟 Features

### Core Features

- **Multi-Database Support** - Connect to multiple databases (Dev, Prod, Test) simultaneously
- **Smart Discovery** - Tools like `locate_table` help AI find data without guessing
- **Connection Pooling** - Efficient database connections with automatic pooling
- **Security Validation** - Input validation, SQL injection prevention, protected tables
- **Query Logging** - Automatic logging with performance tracking
- **Markdown Output** - Beautiful formatted results for AI consumption

### Available Tools (22+)

#### 🌐 Discovery & Connection (New!)

| Tool               | Description                                              |
| ------------------ | -------------------------------------------------------- |
| `list_databases`   | Lists all configured database connections & status       |
| `locate_table`     | **Global Search**: Finds which database contains a table |
| `get_session_info` | View detailed session info for all active pools          |

#### 📋 Basic Database Operations

_(All tools now support optional `database_name` argument)_

| Tool                        | Description                                           |
| --------------------------- | ----------------------------------------------------- |
| `list_tables`               | Lists all tables available to the current user        |
| `describe_table`            | Gets the schema/structure of a specific table         |
| `run_read_only_query`       | Executes SELECT queries safely                        |
| `run_query_with_pagination` | SELECT with pagination support                        |
| `run_modification_query`    | INSERT, UPDATE, DELETE, CREATE, DROP with auto-commit |

#### 🔍 DDL & Inspection (Deep Dive)

| Tool               | Description                                    |
| ------------------ | ---------------------------------------------- |
| `get_object_ddl`   | Gets DDL/Source for tables, views, packages... |
| `list_constraints` | Lists Primary Keys, Foreign Keys, Checks       |
| `list_indexes`     | Lists all indexes and their columns            |

#### 🔎 Search Tools

| Tool              | Description                              |
| ----------------- | ---------------------------------------- |
| `search_in_table` | Full-text search across all text columns |

#### 📊 Performance & Management (Admin)

| Tool                 | Description                             |
| -------------------- | --------------------------------------- |
| `explain_query_plan` | Get execution plan to debug performance |
| `inspect_locks`      | View blocking sessions and locks        |
| `kill_session`       | Kill a stuck session (Use with caution) |

#### 📤 Import/Export

| Tool                  | Description                      |
| --------------------- | -------------------------------- |
| `export_query_to_csv` | Export query results to CSV file |

## 🚀 Installation & Setup Guide

### Step 1: Install the Server (`install.bat`)

We have simplified the installation process into a single script.

1.  **Download/Clone** this repository to your local machine.
2.  **Run `install.bat`**:
    - Double-click the file `install.bat` in the project folder.
    - _Or_ run it via terminal:
      ```cmd
      cd path\to\mcp-oracle-server
      install.bat
      ```
    - This script will automatically install Python dependencies and register the `mcp-oracle-server` package.

### Step 2: Configure Database Connections (`oracle_config.json`)

This file tells the server how to connect to your Oracle databases.

1.  Find the file `oracle_config.example.json` in the project folder.
2.  Rename it to `oracle_config.json`.
3.  Open it and update with your actual database details.

**Example `oracle_config.json`:**

```json
{
  "databases": [
    {
      "name": "dev",
      "user": "your_username",
      "password": "your_password",
      "host": "localhost",
      "port": "1521",
      "service_name": "ORCLPDB"
    },
    {
      "name": "prod",
      "user": "admin",
      "password": "secure_password",
      "dsn": "production.server.com:1521/finance_service",
      "mode": "SYSDBA"
    }
  ],
  "global_settings": {
    "oracle_client_path": "C:\\path\\to\\instantclient_23_0",
    "default_database": "dev",
    "pool_min": 2,
    "pool_max": 10
  }
}
```

> **Note:** `oracle_client_path` must point to the folder containing `oci.dll`. We have included a valid client in `instantclient_23_0` inside the project for your convenience (e.g., `D:\Projects\mcp-oracle-server\instantclient_23_0`).

### Step 3: Configure AI Client (`mcp_config.json`)

To let your AI (Google Gemini, Antigravity, VS Code) know about this server, you need to add it to your MCP configuration file.

**File Location:**

- **Windows**: `c:\Users\<YourUser>\.gemini\antigravity\mcp_config.json` (or similar depending on your client)

**Configuration to Add:**

```json
{
  "mcpServers": {
    "oracle-server": {
      "command": "python",
      "args": ["-m", "mcp_oracle_server"],
      "env": {
        "PYTHONIOENCODING": "utf-8",
        "PYTHONPATH": "D:\\Projects\\mcp-oracle-server\\src",
        "ORACLE_CONFIG_DIR": "D:\\Projects\\mcp-oracle-server"
      }
    }
  }
}
```

**Key Parameters Explain:**

- `command`: Uses `python` explicitly to ensure the correct environment.
- `args`: Runs the server module.
- `pythonpath`: **Crucial**. Point this to the `src` folder so Python can find the code.
- `ORACLE_CONFIG_DIR`: Point this to where you saved `oracle_config.json`.

---

## 📁 Project Structure

```
mcp-oracle-server/
├── server.py          # Main MCP server with Multi-DB support
├── config.py          # Configuration loader (JSON + Env)
├── oracle_config.json # Database Connection Profiles
├── logger.py          # Logging and query tracking
├── .env               # Legacy single-db config
├── instantclient_23_0/ # Oracle Instant Client
└── README.md          # This file
```

## 🔧 Configuration Options

### `oracle_config.json`

| Key        | Description                                              |
| ---------- | -------------------------------------------------------- |
| `name`     | Unique identifier for the database (e.g., `dev`, `prod`) |
| `dsn`      | Copy connection string (e.g. `host:port/service`)        |
| `mode`     | Optional. Set to `SYSDBA` for admin connections          |
| `encoding` | Optional. Default `UTF-8`                                |

### Environment Variables (Legacy / Global Override)

| Variable             | Description                   |
| -------------------- | ----------------------------- |
| `ORACLE_CLIENT_PATH` | Path to Oracle Instant Client |
| `LOG_LEVEL`          | Logging level (INFO, DEBUG)   |

### Protected Tables

Edit `config.py` to add tables that should not be modified:

```python
PROTECTED_TABLES = [
    "SYS",
    "SYSTEM",
    "AUDIT_TRAIL",
    # Add your sensitive tables here
]
```

## 🔒 Security Features

1. **SQL Injection Prevention**
   - All table names validated against safe identifier patterns
   - Parameterized queries used throughout

2. **Query Restrictions**
   - SELECT queries blocked from containing DML keywords
   - Dangerous commands (DROP DATABASE, etc.) blocked

3. **Protected Tables**
   - Configurable list of tables that cannot be modified

4. **Connection Pooling**
   - Connections properly managed and released
   - No credential exposure

## 📊 Usage Examples

### 1. Discovery (Where is my data?)

```python
# Find which database has the 'EMPLOYEES' table
locate_table("EMPLOYEES")
# Output: Found in database 'HR_PROD'

# List all connected environments
list_databases()
```

### 2. Multi-Database Queries

```python
# Query a specific database
run_read_only_query("SELECT * FROM employees", database_name="HR_PROD")

# List tables in Finance DB
list_tables(database_name="finance_prod")
```

### 3. Basic Queries (Default DB)

```python
# Uses the default_database defined in json
describe_table("PRODUCTS")
```

### 4. Advanced Operations

```python
# Get table statistics
get_table_statistics("EMPLOYEES", database_name="HR_PROD")

# Compare two table schemas
compare_table_schemas("EMPLOYEES", "EMPLOYEES_BACKUP")
```

### 5. Monitoring

```python
# View execution plan
explain_plan("SELECT * FROM large_table WHERE status = 'ACTIVE'")

# Check system health across all pools
get_session_info()
```

## 📜 License

MIT License - Feel free to use and modify!

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

---

**Built with ❤️ for AI-powered Enterprise Database Management**
