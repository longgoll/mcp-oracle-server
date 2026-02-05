@echo off
echo ==========================================
echo   Oracle MCP Server - Installation Script
echo ==========================================
echo.

:: Check Python version
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    exit /b 1
)

echo [1/3] Installing package in development mode...
pip install -e .

if errorlevel 1 (
    echo [ERROR] Installation failed!
    exit /b 1
)

echo.
echo [2/3] Verifying installation...
python -c "from mcp_oracle_server import main; print('Package imported successfully!')"

if errorlevel 1 (
    echo [ERROR] Package verification failed!
    exit /b 1
)

echo.
echo [3/3] Testing configuration...
python -c "from mcp_oracle_server.config import validate_config; validate_config(); print('Configuration valid!')" 2>nul
if errorlevel 1 (
    echo [WARNING] Configuration not set. Please edit .env file with your Oracle credentials.
)

echo.
echo ==========================================
echo   Installation Complete!
echo ==========================================
echo.
echo Next steps:
echo   1. Copy env.example to .env and fill in your Oracle credentials
echo   2. Run the server with: mcp-oracle-server
echo   3. Or run directly with: python -m mcp_oracle_server
echo.
echo For Google Antigravity/VS Code MCP config, add this to mcp_config.json:
echo.
echo {
echo   "mcpServers": {
echo     "oracle-server": {
echo       "command": "mcp-oracle-server",
echo       "env": {
echo         "ORACLE_USER": "your_user",
echo         "ORACLE_PASSWORD": "your_password",
echo         "ORACLE_DSN": "host:port/service"
echo       }
echo     }
echo   }
echo }
echo.
pause
