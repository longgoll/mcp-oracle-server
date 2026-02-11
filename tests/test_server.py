
import pytest
from unittest.mock import MagicMock, patch
import sys
import os
from contextlib import contextmanager

# Add src to path so we can import the server
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from mcp_oracle_server.server import (
    list_invalid_objects, compile_object, 
    check_tablespace_usage, generate_mock_data,
    validate_identifier
)

# Mock oracledb
sys.modules["oracledb"] = MagicMock()
import oracledb

@pytest.fixture
def mock_db_context():
    """Mocks the get_connection context manager"""
    with patch("mcp_oracle_server.server.get_connection") as mock_get_conn:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        
        # Setup context manager behavior
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        mock_get_conn.return_value.__exit__.return_value = None
        
        yield mock_conn, mock_cursor

def test_validate_identifier():
    assert validate_identifier("MY_TABLE") == True
    assert validate_identifier("hr.employee") == True
    assert validate_identifier("INVALID-NAME") == False
    assert validate_identifier("; DROP TABLE") == False

def test_list_invalid_objects_none(mock_db_context):
    conn, cursor = mock_db_context
    cursor.fetchall.return_value = [] # No invalid objects
    
    result = list_invalid_objects()
    assert "✅ All objects are VALID" in result

def test_list_invalid_objects_found(mock_db_context):
    conn, cursor = mock_db_context
    cursor.fetchall.return_value = [
        ("MY_PROC", "PROCEDURE", "2023-01-01")
    ]
    
    result = list_invalid_objects()
    assert "MY_PROC" in result
    assert "PROCEDURE" in result

def test_compile_object_success(mock_db_context):
    conn, cursor = mock_db_context
    
    result = compile_object("MY_PROC", "PROCEDURE")
    
    cursor.execute.assert_called_with("ALTER PROCEDURE MY_PROC COMPILE")
    assert "✅ Successfully compiled" in result

def test_compile_object_failure(mock_db_context):
    conn, cursor = mock_db_context
    # Mock DatabaseError
    error_mock = MagicMock()
    error_mock.message = "Syntax Error"
    cursor.execute.side_effect = oracledb.DatabaseError(error_mock)
    
    result = compile_object("BROKEN_PROC", "PROCEDURE")
    
    assert "❌ Compilation Failed" in result
    assert "Syntax Error" in result

def test_check_tablespace_usage_success(mock_db_context):
    conn, cursor = mock_db_context
    cursor.fetchall.return_value = [
        ("USERS", 100, 80, 20, 20.0),
        ("SYSTEM", 500, 400, 100, 20.0)
    ]
    
    result = check_tablespace_usage()
    assert "USERS" in result
    assert "20.0%" in result
    assert "💾 Tablespace Usage" in result

def test_generate_mock_data(mock_db_context):
    conn, cursor = mock_db_context
    # 1. Mock Schema Return
    cursor.fetchall.side_effect = [
        [("ID", "NUMBER", 22), ("NAME", "VARCHAR2", 50)], # Schema
    ]
    
    result = generate_mock_data("TEST_TABLE", 5)
    
    assert "✅ Successfully generated" in result
    # Verify INSERT was called
    cursor.executemany.assert_called()
    call_args = cursor.executemany.call_args
    sql = call_args[0][0]
    data = call_args[0][1]
    
    assert "INSERT INTO TEST_TABLE" in sql
    assert len(data) == 5 # 5 rows generated
