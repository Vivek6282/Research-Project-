@echo off
cd /d "%~dp0"
start "" "..\frontend\public\demo\track_visualization.html"
py virtual_lap_simulator.py --continuous
pause
