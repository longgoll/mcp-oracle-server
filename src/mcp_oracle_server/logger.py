"""
Logging module for Oracle MCP Server.
Provides centralized logging with file rotation and formatting.
"""
import logging
from logging.handlers import RotatingFileHandler
import os
from .config import LOG_LEVEL, LOG_FILE, LOG_FORMAT, LOG_MAX_BYTES, LOG_BACKUP_COUNT

def setup_logger(name: str = "oracle_mcp") -> logging.Logger:
    """
    Sets up and returns a configured logger instance.
    
    Args:
        name: Name of the logger
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger
    
    # Set log level
    level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(level)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(console_handler)
    
    # File handler with rotation
    try:
        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=LOG_MAX_BYTES,
            backupCount=LOG_BACKUP_COUNT,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logger.addHandler(file_handler)
    except Exception as e:
        logger.warning(f"Could not create file handler: {e}")
    
    return logger


class QueryLogger:
    """
    Helper class to log query executions with timing and results.
    """
    
    def __init__(self, logger: logging.Logger = None):
        self.logger = logger or setup_logger()
        self.query_history = []
        self.max_history = 100
    
    def log_query(self, query: str, duration_ms: float, rows_affected: int = 0, 
                  success: bool = True, error: str = None):
        """
        Logs a query execution.
        
        Args:
            query: The SQL query executed
            duration_ms: Execution time in milliseconds
            rows_affected: Number of rows affected
            success: Whether the query succeeded
            error: Error message if failed
        """
        # Truncate long queries for logging
        display_query = query[:200] + "..." if len(query) > 200 else query
        
        entry = {
            "query": display_query,
            "duration_ms": duration_ms,
            "rows_affected": rows_affected,
            "success": success,
            "error": error
        }
        
        # Add to history
        self.query_history.append(entry)
        if len(self.query_history) > self.max_history:
            self.query_history.pop(0)
        
        # Log
        if success:
            self.logger.info(
                f"Query executed in {duration_ms:.2f}ms | Rows: {rows_affected} | {display_query}"
            )
        else:
            self.logger.error(
                f"Query failed after {duration_ms:.2f}ms | Error: {error} | {display_query}"
            )
    
    def get_recent_queries(self, limit: int = 10) -> list:
        """Returns the most recent queries from history."""
        return self.query_history[-limit:]
    
    def get_slow_queries(self, threshold_ms: float = 1000) -> list:
        """Returns queries that took longer than the threshold."""
        return [q for q in self.query_history if q["duration_ms"] > threshold_ms]


# Global logger instance
logger = setup_logger()
query_logger = QueryLogger(logger)
