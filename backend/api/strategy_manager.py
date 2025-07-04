# /home/ubuntu/backtest_app/backend/api/strategy_manager.py

import os
import re
from flask import Blueprint, request, jsonify
import  unicodedata

# Assuming backtesting_service exists, adjust import if needed
# from backend.services.backtesting_service import run_backtest

strategy_bp = Blueprint("strategy", __name__)

# Define the directory where strategies will be saved
# STRATEGY_DIR = "/home/ubuntu/backtest_app/backend/data/strategies"
# Define the directory to store strategy files relative to this file's location
# Get the directory where this script (strategy_manager.py) is located
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# Define STRATEGY_DIR relative to CURRENT_DIR
STRATEGY_DIR = os.path.join(CURRENT_DIR, '..', 'strategies') # Go up one level and into 'strategies'
# Ensure the directory exists
os.makedirs(STRATEGY_DIR, exist_ok=True)

def is_safe_filename(filename):
    """Check if the filename is safe (alphanumeric, underscores, hyphens)."""
    """
    영문, 숫자, 밑줄(_), 하이픈(-) + 완성형 한글(가-힣)만 허용.
    경로 탐색 문자(/, \, ..)는 여전히 차단합니다.
    """
    filename = unicodedata.normalize("NFC", filename)  # Normalize to avoid 조합형 깨짐
    return re.match(r"^[\uAC00-\uD7A3a-zA-Z0-9_-]+$", filename) is not None

@strategy_bp.route("/strategies", methods=["GET"])
def list_or_load_strategies():
    """Lists saved strategies or loads a specific strategy code.
    Query Parameters:
        name (str, optional): If provided, loads the code for the specific strategy.
                              Otherwise, lists all saved strategy names.
    Returns:
        JSON: List of strategy names or strategy code string, or error message.
    """
    strategy_name = request.args.get("name")
    # print(f"받은 name 파라미터: {strategy_name}", flush=True)
    if strategy_name:
        # Load specific strategy
        # print(f"1. file_path 파라미터: {strategy_name}", flush=True)
        if not is_safe_filename(strategy_name):
            # print(f"Invalid strategy name format: {strategy_name}", flush=True)
            return jsonify({"error": "Invalid strategy name format."}), 400
        
        file_path = os.path.join(STRATEGY_DIR, f"{strategy_name}.py")
        # print(f"2. file_path 파라미터: {file_path}", flush=True)

        if os.path.isfile(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    strategy_code = f.read()
                    # print(f"strategy code: {strategy_code}", flush=True)

                return jsonify({"name": strategy_name, "code": strategy_code}), 200
            except Exception as e:
                # print(f"Error reading strategy file {file_path}: {e}")
                return jsonify({"error": f"Failed to read strategy file: {e}"}), 500
        else:
            print(f"else Strategy file {file_path} not found.")
            return jsonify({"error": "Strategy not found."}), 404
    else:
        # List all strategies
        # print(f"Listing all strategies in {strategy_name}", flush=True)
        try:
            PLACEHOLDER = "직접 코드 입력/생성"

            strategy_files = [
                f[:-3] for f in os.listdir(STRATEGY_DIR)
                if f.endswith(".py")
                and os.path.isfile(os.path.join(STRATEGY_DIR, f))
                and f[:-3] != PLACEHOLDER        # ⬅️ 필터
            ]
            # strategy_files = [f[:-3] for f in os.listdir(STRATEGY_DIR) if f.endswith(".py") and os.path.isfile(os.path.join(STRATEGY_DIR, f))]
            return jsonify({"strategies": strategy_files}), 200
        except Exception as e:
            print(f"Error listing strategies in {STRATEGY_DIR}: {e}")
            return jsonify({"error": f"Failed to list strategies: {e}"}), 500

@strategy_bp.route("/strategies", methods=["POST"])
def save_strategy():
    """Saves a new strategy or overwrites an existing one.
    Request Body (JSON):
        name (str): The name for the strategy.
        code (str): The Python code for the strategy.
    Returns:
        JSON: Success message or error message.
    """
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    req_data = request.get_json()
    strategy_name = req_data.get("name")
    strategy_code = req_data.get("code")

    if not strategy_name or not strategy_code:
        return jsonify({"error": "Missing strategy name or code in request body"}), 400

    if not is_safe_filename(strategy_name):
        return jsonify({"error": "Invalid strategy name format. Use only letters, numbers, underscores, hyphens."}), 400

    file_path = os.path.join(STRATEGY_DIR, f"{strategy_name}.py")

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(strategy_code)
        return jsonify({"message": f"Strategy 	\"{strategy_name}\" saved successfully."}), 201 # 201 Created (or 200 OK if overwriting)
    except Exception as e:
        print(f"Error writing strategy file {file_path}: {e}")
        return jsonify({"error": f"Failed to save strategy: {e}"}), 500

@strategy_bp.route("/strategies/<string:name>", methods=["DELETE"])
def delete_strategy(name):
    """Deletes a specific strategy.
    Path Parameter:
        name (str): The name of the strategy to delete.
    Returns:
        JSON: Success message or error message.
    """
    if not is_safe_filename(name):
        return jsonify({"error": "Invalid strategy name format."}), 400

    file_path = os.path.join(STRATEGY_DIR, f"{name}.py")

    if os.path.isfile(file_path):
        try:
            os.remove(file_path)
            return jsonify({"message": f"Strategy 	\"{name}\" deleted successfully."}), 200
        except Exception as e:
            print(f"Error deleting strategy file {file_path}: {e}")
            return jsonify({"error": f"Failed to delete strategy: {e}"}), 500
    else:
        return jsonify({"error": "Strategy not found."}), 404

