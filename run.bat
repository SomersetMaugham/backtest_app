@echo off
REM Start both backend and frontend servers in separate windows

echo Starting backend and frontend servers...

start "" cmd /k "C:\Users\mally\project\stock\backtest_app\runback.bat"

start "" cmd /k "C:\Users\mally\project\stock\backtest_app\runfront.bat"

echo Both servers are starting in separate windows.

