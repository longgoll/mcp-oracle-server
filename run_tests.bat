@echo off
pip install -r requirements.txt
echo Running Tests...
pytest tests/test_server.py
pause
