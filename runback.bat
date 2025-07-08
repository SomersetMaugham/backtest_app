@echo off
REM Start the backend server

echo Starting backend server...
cd "C:\Users\mally\project\stock\backtest_app\backend"

REM Activate virtual environment and run Streamlit application in the same command window
call conda activate stock

REM Run the application
flask run --host=127.0.0.1 --port=5001