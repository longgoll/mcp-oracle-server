"""
Oracle Database MCP Server Package
A comprehensive Model Context Protocol server for Oracle Database operations.
"""

__version__ = "1.0.0"
__author__ = "HoangLong"

from .server import mcp
from .config import validate_config

def main():
    """Main entry point for the MCP server."""
    from .logger import logger
    logger.info("Starting Oracle MCP Server...")
    try:
        validate_config()
        mcp.run()
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        raise

__all__ = ["mcp", "main", "validate_config"]
