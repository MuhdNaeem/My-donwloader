@echo off
cd /d "%~dp0"
echo Starting Vercel Serverless Video Downloader locally on http://localhost:5000 ...
python api\index.py
pause
