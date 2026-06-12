@echo off
cd /d D:\NPL전례\avm_project
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
