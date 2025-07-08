@echo off
REM Start the frontend server

echo Starting frontend server...
cd C:\Users\mally\project\stock\backtest_app\frontend

REM Activate virtual environment and run Streamlit application in the same command window
call conda activate stock

REM Run the Streamlit application
streamlit run app.py