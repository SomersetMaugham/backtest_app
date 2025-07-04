from flask import Blueprint, request, jsonify
import pandas as pd
from pykrx import stock # Replaces yfinance for this function
import FinanceDataReader as fdr

stock_data_bp = Blueprint("stock_data", __name__)

@stock_data_bp.route("/stock_data", methods=["GET"])
def get_stock_data():
    """Fetches historical Korean stock data using pykrx.
    Query Parameters:
        ticker (str): The stock ticker symbol for a Korean stock (e.g., "005930").
        start_date (str): Start date in "YYYY-MM-DD" format.
        end_date (str): End date in "YYYY-MM-DD" format.
    Returns:
        JSON: OHLCV data as JSON string or error message.
    """
    ticker = request.args.get("ticker")
    start_date_str = request.args.get("start_date")
    end_date_str = request.args.get("end_date")

    if not all([ticker, start_date_str, end_date_str]):
        return jsonify({"error": "Missing required parameters: ticker, start_date, end_date"}), 400

    try:
        # Validate and parse dates
        start_date_dt = pd.to_datetime(start_date_str)
        end_date_dt = pd.to_datetime(end_date_str)
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD."}), 400

    # pykrx's end_date is inclusive.
    if start_date_dt > end_date_dt: # Changed from >= to > as pykrx todate is inclusive
        return jsonify({"error": "Start date must not be after end date."}), 400

    # Convert dates to YYYYMMDD format for pykrx
    pykrx_start_date = start_date_dt.strftime('%Y%m%d')
    pykrx_end_date = end_date_dt.strftime('%Y%m%d')

    try:
        # Fetch data using pykrx
        # data_df = stock.get_market_ohlcv_by_date(fromdate=pykrx_start_date, todate=pykrx_end_date, ticker=ticker)
        data_df = fdr.DataReader(ticker, pykrx_start_date, pykrx_end_date)
        if data_df.empty:
            return jsonify({"error": f"No data found for ticker {ticker} in the specified date range using pykrx."}), 404

        # pykrx columns are in Korean: '시가', '고가', '저가', '종가', '거래량'
        # Rename columns to standard English OHLCV for broader compatibility
        column_map = {
            '시가': 'Open',
            '고가': 'High',
            '저가': 'Low',
            '종가': 'Close',
            '거래량': 'Volume'
            # '등락률': 'ChangePercent' # Optional: if you want to include it
        }
        data_df = data_df.rename(columns=column_map)

        # Select only the standard OHLCV columns that are present after renaming
        desired_ohlcv_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        columns_to_include = [col for col in desired_ohlcv_columns if col in data_df.columns]
        
        if not columns_to_include:
            return jsonify({"error": f"Could not retrieve expected OHLCV columns for ticker {ticker}."}), 404
            
        data_df = data_df[columns_to_include]

        # Convert Timestamp index to string "YYYY-MM-DD" for JSON serialization
        data_df.index = data_df.index.strftime("%Y-%m-%d")

        return jsonify(data_df.to_dict(orient="index")), 200

    except ValueError as ve:
        # pykrx often raises ValueError for invalid tickers or date issues
        error_message = str(ve)
        print(f"ValueError for {ticker} using pykrx: {error_message}") # Log the error
        if "티커" in error_message and ("목록에 없습니다" in error_message or "올바르지 않습니다" in error_message):
            return jsonify({"error": f"Invalid ticker symbol or data not available with pykrx: {ticker}. Details: {error_message}"}), 404
        elif "날짜" in error_message:
             return jsonify({"error": f"Date related error with pykrx: {error_message}"}), 400
        return jsonify({"error": f"An error occurred while fetching data using pykrx: {error_message}"}), 500
    except Exception as e:
        # Catch other potential errors
        print(f"Error fetching data for {ticker} using pykrx: {e}") # Log the error
        return jsonify({"error": f"An unexpected error occurred while fetching data using pykrx: {str(e)}"}), 500

