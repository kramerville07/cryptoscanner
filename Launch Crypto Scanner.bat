@echo off
cd /d "%~dp0"
start "" python -m streamlit run dashboard.py
exit
