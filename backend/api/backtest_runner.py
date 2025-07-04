# /home/ubuntu/backtest_app/backend/api/backtest_runner.py

from flask import Blueprint, request, jsonify
import pandas as pd
import io
import numpy as np
import logging

# Use absolute import based on the project structure
from backend.core.backtesting import run_backtest

backtest_bp = Blueprint("backtest", __name__)

@backtest_bp.route("/backtest", methods=["POST"])
def execute_backtest():
    """Executes a backtest based on provided data and strategy code.
    Request Body (JSON):
        data (dict): Stock data in JSON format (e.g., from df.to_dict(orient=\"index\")).
        strategy_code (str, optional): Python code string for the strategy.
        initial_capital (float, optional): Starting capital, defaults to 10000.0.
    Returns:
        JSON: Backtest results (trades, metrics) or error message.
    """
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    req_data = request.get_json()
    stock_data_dict = req_data.get("data")
    
    strategy_code = req_data.get("strategy_code") # Can be None
    print(f"받은 name 파라미터: {strategy_code}", flush=True)
    
    initial_capital = float(req_data.get("initial_capital", 1000000.0))
    stop_loss_pct = float(req_data.get("stop_loss_pct", 5.0))
    trade_fee_pct = float(req_data.get("trade_fee_pct", 0.001))
    sell_tax_pct = float(req_data.get("sell_tax_pct", 0.2))

    print("trade_fee_pct:", trade_fee_pct, flush=True)
    print("sell_tax_pct:", sell_tax_pct, flush=True)

    if not stock_data_dict:

        return jsonify({"error": "Missing stock data in request body"}), 400

    try:
        # Convert the dictionary back to DataFrame
        # Assuming the format is {date_str: {col: value, ...}}
        data_df = pd.DataFrame.from_dict(stock_data_dict, orient="index")
        data_df.index = pd.to_datetime(data_df.index)
        # Ensure columns are numeric where expected (e.g., Close)
        for col in ["Open", "High", "Low", "Close", "Volume"]:
             if col in data_df.columns:
                 data_df[col] = pd.to_numeric(data_df[col])
        data_df.sort_index(inplace=True) # Ensure data is sorted by date

    except Exception as e:
        return jsonify({"error": f"Failed to parse stock data: {e}"}), 400

    if data_df.empty:
        return jsonify({"error": "Provided stock data is empty"}), 400

    try:
        # Run the backtest using the core logic
        results = run_backtest(
            data_df,
            strategy_code,
            initial_capital,
            stop_loss_pct,
            trade_fee_pct,
            sell_tax_pct
        )
        
        results = convert_numpy_types(results)
        if "error" in results:
             return jsonify(results), 400 # Propagate error from backtest engine

        return jsonify(results), 200

    except Exception as e:
        print(f"Error during backtest execution: {e}") # Log the error
        return jsonify({"error": f"An unexpected error occurred during backtesting: {str(e)}"}), 500

def convert_numpy_types(obj):
    if isinstance(obj, dict):
        return {k: convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(i) for i in obj]
    elif isinstance(obj, (np.integer, np.int64)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64)):
        return float(obj)
    elif isinstance(obj, (pd.Timestamp, np.datetime64)):
        return str(obj)
    else:
        return obj