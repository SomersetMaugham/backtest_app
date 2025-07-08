import pandas as pd
import numpy as np
import traceback # For detailed error logging
import logging

def calculate_metrics(trades: list, equity_curve: pd.Series, initial_capital: float = 10000.0, risk_free_rate: float = 0.02) -> dict:
    """Calculates performance metrics from a list of trades.

    Args:
        trades (list): List of trade dictionaries, e.g., 
                       [{\"buy_date\": \"YYYY-MM-DD\", \"buy_price\": float, 
                        \"sell_date\": \"YYYY-MM-DD\", \"sell_price\": float, 
                        \"profit_loss\": float, \"return_pct\": float}].
        initial_capital (float): The starting capital for calculating total return.

    Returns:
        dict: Dictionary containing total_return (%), win_rate (%), profit_loss_ratio.
    """
    # if not trades:
    #     return {"total_return": 0.0, "win_rate": 0.0, "profit_loss_ratio": 0.0, "num_trades": 0}

    # Basic stats even if no trades
    try:
        metrics = {"num_trades": len(trades)}
        if not trades:
            # compute drawdown on flat equity curve
            drawdown = (equity_curve / equity_curve.cummax() - 1).min() * 100
            metrics.update({
                "total_return": round((equity_curve.iloc[-1] / initial_capital - 1) * 100, 2),
                "win_rate": 0.0,
                "profit_loss_ratio": 0.0,
                "max_drawdown_pct": 0.0,
                "final_asset": float(equity_curve.iloc[-1]),
                "sqn": None,
                "sharpe_ratio": None
            })
            return metrics

        # Calculate total profit/loss based on individual trade profit_loss
        total_profit_loss = sum(trade["profit_loss"
                                    ] for trade in trades)
        # Calculate total return based on initial capital
        # Note: This assumes profit_loss is absolute value. If it's per share, calculation needs adjustment.
        # Let's assume profit_loss is the total profit for that trade based on initial capital allocation per trade (or fixed shares)
        # A more accurate total return would track portfolio value over time.
        # For simplicity, let's calculate return based on sum of trade returns if available, or use profit/loss.
        # If using profit_loss sum:
        
        # total_return_pct = (total_profit_loss / initial_capital) * 100 
        total_return_pct = (equity_curve.iloc[-1] / initial_capital - 1) * 100

        
        # If using average return_pct (less accurate for portfolio):
        # avg_return = np.mean([trade["return_pct"] for trade in trades])

        num_trades = len(trades)
        winning_trades = [trade for trade in trades if trade["profit_loss"] > 0]
        losing_trades = [trade for trade in trades if trade["profit_loss"] < 0]

        num_winning_trades = len(winning_trades)
        num_losing_trades = len(losing_trades)

        win_rate = (num_winning_trades / num_trades) * 100 if num_trades > 0 else 0.0

        avg_profit = sum(trade["profit_loss"] for trade in winning_trades) / num_winning_trades if num_winning_trades > 0 else 0
        # Use absolute value for average loss
        avg_loss = abs(sum(trade["profit_loss"] for trade in losing_trades) / num_losing_trades) if num_losing_trades > 0 else 0

        profit_loss_ratio = avg_profit / avg_loss if avg_loss > 0 else np.inf # Handle division by zero
        if profit_loss_ratio == np.inf and num_winning_trades > 0:
            profit_loss_ratio = 100.0 # Assign a large number if no losses but profits exist
        elif num_winning_trades == 0:
            profit_loss_ratio = 0.0 # Assign 0 if no profits
        elif profit_loss_ratio == np.inf: # Case where avg_loss is 0 and avg_profit is 0
            profit_loss_ratio = 0.0

        dd_series = (equity_curve / equity_curve.cummax()) - 1
        max_drawdown = dd_series.min() * 100  # will be negative or zero

        returns = [trade["return_pct"] for trade in trades]

        if num_trades > 1 and np.std(returns) != 0:
            sqn = (np.mean(returns) / np.std(returns)) * np.sqrt(num_trades)
            sqn = round(sqn, 2)
        else:
            sqn = None  # 또는 0

        # Sharpe Ratio 계산
        returns = equity_curve.pct_change().dropna()  # 1일 단순 수익률
        excess_returns = returns - risk_free_rate / 252  # 일별 무위험수익률(예: 연 1% → 일 1/252)
        mean_excess_return = excess_returns.mean()
        std_excess_return = excess_returns.std()
        sharpe_ratio = np.nan
        if std_excess_return != 0:
            sharpe_ratio = mean_excess_return / std_excess_return
            # 연율화: 일간 수익률이면 × sqrt(252)
            sharpe_ratio = sharpe_ratio * np.sqrt(252)

        return {
            "total_return": round(total_return_pct, 2),
            "win_rate": round(win_rate, 2),
            "profit_loss_ratio": (
                round(profit_loss_ratio, 2)
                if profit_loss_ratio not in (np.inf, float("inf")) else "inf"
            ),
            "max_drawdown_pct": round(abs(max_drawdown), 2),
            "num_trades": num_trades,
            "final_asset": float(equity_curve.iloc[-1]),
            "sqn": sqn,
            "sharpe_ratio": round(sharpe_ratio, 3) if not np.isnan(sharpe_ratio) else None
        }
    except Exception as e:
        # print("===== run_backtest에서 예외 발생 =====")
        # traceback.print_exc()
        return {"error": f"run_backtest error: {type(e).__name__}: {e}"}
    
def run_backtest(data: pd.DataFrame, strategy_code: str = None, initial_capital: float = 1000000.0, stop_loss_pct: float = 5.0, trade_fee_pct: float = 0.001, sell_tax_pct: float = 0.2) -> dict:
    """Runs a backtest simulation on the provided data using the given strategy.
    Args:
        data (pd.DataFrame): DataFrame with OHLCV data and DatetimeIndex.
        strategy_code (str, optional): Python code string defining the strategy.
                                       Must define a function `generate_signals(data)`.
                                       If None or empty, uses a default buy-and-hold strategy.
        initial_capital (float): Starting capital for the simulation.
        stop_loss_pct:
        trade_fee_pct:
        sell_tax_pct:

    Returns:
        dict: Contains \'trades\' list and \'metrics\' dictionary.
              Returns {\'error\': message} if an error occurs.
    """
    try:
        trades = []
        position_open = False
        buy_price = 0
        buy_date = None
        # For simplicity, assume we invest the full capital in the first trade
        # A more complex simulation would handle capital allocation per trade.
        shares_held = 0

        # print("===== run_backtest: pct verification =====", flush=True)
        # 퍼센트 단위 → 소수 단위 변환 (필수!!)
        # print(f"Before trade_fee_pct: {trade_fee_pct}, sell_tax_pct: {sell_tax_pct}", flush=True)
        trade_fee_pct = trade_fee_pct / 100
        sell_tax_pct = sell_tax_pct / 100
        # print(f"After trade_fee_pct: {trade_fee_pct}, sell_tax_pct: {sell_tax_pct}", flush=True)

        # --- Data Validation ---
        if data.empty:
            return {"error": "Input data is empty."}

        signals = pd.Series("hold", index=data.index) # Default to hold

        # --- Strategy Code Execution --- 
        if strategy_code:
            print(f"--- Executing Provided Strategy Code ---")
            try:
                # Define a restricted environment for exec()
                # Allow pandas, numpy, and the data itself
                # WARNING: exec() is inherently risky. A proper sandbox is needed for production.
                # For this context, we restrict builtins and available modules.
                safe_globals = {
                    "pd": pd,
                    "np": np,
                    "data": data.copy(), # Pass a copy to prevent modification
                    "__builtins__": {
                        "print": print, # Allow printing for debugging within strategy
                        "range": range,
                        "len": len,
                        "abs": abs,
                        "round": round,
                        "sum": sum,
                        "min": min,
                        "max": max,
                        "True": True,
                        "False": False,
                        "None": None,
                        # Add other safe builtins if necessary
                    }
                }
                exec_locals = {}
                
                # Execute the strategy code
                exec(strategy_code, safe_globals, exec_locals)
                
                # Check if the required function is defined
                if "generate_signals" not in exec_locals or not callable(exec_locals["generate_signals"]):
                    return {"error": "Strategy code must define a function named 'generate_signals(data)'."}
                
                # Call the user-defined function
                generated_signals = exec_locals["generate_signals"](data.copy()) # Pass data copy

                # Validate signals format (should be Series or list matching data length)
                if isinstance(generated_signals, (pd.Series, list)) and len(generated_signals) == len(data):
                    signals = pd.Series(generated_signals, index=data.index)
                    # Ensure signals are valid ("buy", "sell", "hold")
                    valid_signals = {"buy", "sell", "hold"}
                    if not all(s in valid_signals for s in signals.unique()):
                        return {"error": "Generated signals must be \'buy\', \'sell\', or \'hold\'."}
                else:
                    return {"error": "'generate_signals' function must return a pandas Series or list with the same length as the input data."}

            except Exception as e:
                # print(f"Error executing strategy code: {traceback.format_exc()}")
                return {"error": f"Error executing strategy code: {e}"} 
        else:
            # Default Strategy: Buy and Hold
            # print("--- Using Default Buy and Hold Strategy ---")
            signals.iloc[0] = "buy"
            # No explicit sell signal needed for buy & hold, handled at the end.

        # --- Simulate Trades based on signals --- 
        # Prepare to record equity over time
        equity_curve = pd.Series(index=data.index, dtype=float)
        cash = initial_capital
        shares_held = 0

        for i in range(len(data)):
            current_date = data.index[i]
            current_price = data["Close"].iloc[i]
            # current_price = data.loc[current_date, "Close"]
            signal = signals.iloc[i]
            # next_open = data["Open"].iloc[i + 1]
            # next_open = data.loc[current_date+1, "Open"] if i < len(data) - 1 else data, "Low"

            # Update equity before taking action
            if shares_held > 0:
                equity_curve.iloc[i] = shares_held * current_price
            else:
                equity_curve.iloc[i] = cash

            if pd.isna(current_price):
                equity_curve.iloc[i] = equity_curve.iloc[i - 1] if i > 0 else initial_capital            
                continue # Skip days with missing price data

            # ===== Stop Loss Check (추가) =====
            stop_loss_triggered = False
            if position_open and current_price <= buy_price * (1 - stop_loss_pct / 100):
                stop_loss_triggered = True
                # print("Stop Loss Trigger")

            # --- Buy Logic (Long Only) ---
            if signal == "buy" and not position_open:
                position_open = True
                buy_price = current_price
                buy_date = current_date

                # 계산: 매수에 드는 전체 금액 = 주식매수금액 + 매수수수료
                # 1) 수수료 포함해서 최대 매수 가능한 주식 수 계산
                max_shares = int(cash // (buy_price * (1 + trade_fee_pct)))
                if max_shares == 0:
                    continue # 살 수 없음

                shares_held = max_shares
                # 매수수수료
                buy_fee = buy_price * shares_held * trade_fee_pct

                # 매수금액(수수료포함)
                total_buy_amount = buy_price * shares_held + buy_fee

                # 매수시 현금 보유액 감소
                cash -= total_buy_amount

                # print(f"{buy_date.strftime('%Y-%m-%d')}: Buy at {buy_price:.2f}")

            # --- Sell Logic (Long Only) ---
            elif (signal == "sell" or stop_loss_triggered) and position_open:
                sell_price = current_price
                sell_date = current_date

                # 매도수수료
                sell_fee = sell_price * shares_held * trade_fee_pct

                # 매도세금
                sell_tax = sell_price * shares_held * sell_tax_pct

                # 매도금액(수수료·세금 차감)
                total_sell_amount = sell_price * shares_held - sell_fee - sell_tax

                # 매도시 실제 수령 금액 = (매도단가 × 수량) × (1 - trade_fee_pct - sell_tax_pct)
                profit_loss = total_sell_amount - total_buy_amount

                # 실수익률(%)
                return_pct = (profit_loss / total_buy_amount) * 100 if total_buy_amount > 0 else 0
                
                # 보유기간(총 일수 = 매도일 − 매수일)
                holding_period = (sell_date - buy_date).days

                if stop_loss_triggered:
                    exit_type = 'stop_loss' 
                else:
                    exit_type = 'signal'

                trades.append({
                    "buy_date": buy_date.strftime("%Y-%m-%d"),
                    "buy_price": round(buy_price, 2),
                    "sell_date": sell_date.strftime("%Y-%m-%d"),
                    "sell_price": round(sell_price, 2),
                    "profit_loss": round(profit_loss, 2),
                    "return_pct": round(return_pct, 2),
                    "stop_loss": stop_loss_triggered,
                    "buy_qty": shares_held,
                    "buy_fee": round(buy_fee, 2),
                    "total_buy_amount": round(total_buy_amount, 2),
                    "sell_fee": round(sell_fee, 2),
                    "sell_tax": round(sell_tax, 2),
                    "total_sell_amount": round(total_sell_amount, 2),
                    "exit_type": exit_type,
                    "holding_period": holding_period
                })

                # print("===== run_backtest에서 예외 발생 =====")
                # print("===== trades =====", trades, flush=True)
                # print("DEBUG sample trade keys:", trades[0].keys() if trades else "NO TRADES")

                # settle the trade
                # 매도(청산) 시, 현금 보유액 증가
                cash += total_sell_amount
                shares_held = 0
                position_open = False
                buy_price = 0
                buy_fee = 0
                total_buy_amount = 0
                sell_fee = 0
                sell_tax = 0
                buy_date = None
                # For simplicity, don't reinvest capital after selling in this basic model

        # --- Handle Open Position at the End (for Buy & Hold or if strategy leaves position open) ---
        if position_open:
            # Close position on the last day
            sell_price = data["Close"].iloc[-1]
            sell_date = data.index[-1]

            # 매도수수료
            sell_fee = sell_price * shares_held * trade_fee_pct

            # 매도세금
            sell_tax = sell_price * shares_held * sell_tax_pct

            # 매도금액(수수료·세금 차감)
            total_sell_amount = sell_price * shares_held - sell_fee - sell_tax

            profit_loss = total_sell_amount - total_buy_amount

            # 실수익률(%)
            return_pct = (profit_loss / total_buy_amount) * 100 if total_buy_amount > 0 else 0

            # 보유기간(총 일수 = 매도일 − 매수일)
            holding_period = (sell_date - buy_date).days
                        
            exit_type = 'final_close'

            trades.append({
                "buy_date": buy_date.strftime("%Y-%m-%d"),
                "buy_price": round(buy_price, 2),
                "sell_date": sell_date.strftime("%Y-%m-%d"),
                "sell_price": round(sell_price, 2),
                "profit_loss": round(profit_loss, 2),
                "return_pct": round(return_pct, 2),
                "stop_loss": False,
                "buy_qty": shares_held,
                "buy_fee": round(buy_fee, 2),
                "total_buy_amount": round(total_buy_amount, 2),
                "sell_fee": round(sell_fee, 2),
                "sell_tax": round(sell_tax, 2),
                "total_sell_amount": round(total_sell_amount, 2),
                "exit_type": exit_type,
                "holding_period": holding_period
            })
            
            # print("===== run_backtest에서 예외 발생 =====")
            # print("===== trades =====", trades, flush=True)
            # 매도(청산) 시, 현금 보유액 증가
            cash += total_sell_amount
            shares_held = 0
            # print(f"{sell_date.strftime('%Y-%m-%d')}: Force Sell (End of Period) at {sell_price:.2f}, Profit/Loss: {profit_loss:.2f}")

        # --- Calculate Metrics --- 
        # metrics = calculate_metrics(trades, initial_capital)
        # ensure equity_curve is filled forward for any trailing NaNs
        equity_curve.fillna(method="ffill", inplace=True)
        equity_curve.fillna(initial_capital, inplace=True)

        # --- Calculate Metrics (including MDD) --- 
        metrics = calculate_metrics(trades, equity_curve, initial_capital)

        print("DEBUG sample trade keys:", trades[0].keys() if trades else "NO TRADES")

        return {
            "trades": trades,
            "metrics": metrics
        }
    except Exception as e:
        # print("===== run_backtest에서 예외 발생 =====")
        # traceback.print_exc()
        return {"error": f"run_backtest error: {type(e).__name__}: {e}"}

# Example Usage (can be run standalone for testing)
if __name__ == "__main__":
    # Create dummy data
    dates = pd.date_range(start="2023-01-01", periods=10, freq="D")
    dummy_data = pd.DataFrame({
        "Open": [100, 102, 101, 103, 105, 106, 104, 107, 108, 110],
        "High": [103, 104, 103, 106, 106, 107, 106, 109, 110, 111],
        "Low": [99, 101, 100, 102, 104, 103, 103, 106, 107, 108],
        "Close": [102, 103, 102, 105, 105, 104, 105, 108, 109, 110],
        "Volume": [1000] * 10
    }, index=dates)

    print("\n--- Testing Default Strategy (Buy and Hold) ---")
    results_default = run_backtest(dummy_data.copy())
    print("Trades:", results_default.get("trades"))
    print("Metrics:", results_default.get("metrics"))

    print("\n--- Testing Custom Strategy Code (Simple MA Crossover) ---")
    custom_strategy = """
def generate_signals(data):
    signals = pd.Series('hold', index=data.index)
    # Calculate short and long moving averages
    short_window = 3
    long_window = 6
    data['SMA_short'] = data['Close'].rolling(window=short_window, min_periods=1).mean()
    data['SMA_long'] = data['Close'].rolling(window=long_window, min_periods=1).mean()
    
    # Generate signals
    # Buy when short MA crosses above long MA
    signals[data['SMA_short'] > data['SMA_long']] = 'buy' 
    # Sell when short MA crosses below long MA (or use a different condition)
    signals[data['SMA_short'] < data['SMA_long']] = 'sell'
    
    # Ensure first signal is buy if condition met early, handle initial state
    # Simple shift to compare previous day's state
    signals[(data['SMA_short'].shift(1) <= data['SMA_long'].shift(1)) & (data['SMA_short'] > data['SMA_long'])] = 'buy'
    signals[(data['SMA_short'].shift(1) >= data['SMA_long'].shift(1)) & (data['SMA_short'] < data['SMA_long'])] = 'sell'
    
    # Clean up initial signals where MA isn't stable
    signals.iloc[:long_window] = 'hold' # Hold during initial MA calculation period
    
    # Ensure we don't buy/sell consecutively without holding
    final_signals = pd.Series('hold', index=data.index)
    position = 'out'
    for i in range(len(signals)):
        if signals.iloc[i] == 'buy' and position == 'out':
            final_signals.iloc[i] = 'buy'
            position = 'in'
        elif signals.iloc[i] == 'sell' and position == 'in':
            final_signals.iloc[i] = 'sell'
            position = 'out'
            
    return final_signals
"""
    results_custom = run_backtest(dummy_data.copy(), strategy_code=custom_strategy)
    if "error" in results_custom:
        print(f"Error: {results_custom['error']}")
    else:
        print("Trades:", results_custom.get("trades"))
        print("Metrics:", results_custom.get("metrics"))

    print("\n--- Testing Invalid Strategy Code ---")
    invalid_strategy = "def generate_signals(data): return [1, 2, 3] # Wrong length"
    results_invalid = run_backtest(dummy_data.copy(), strategy_code=invalid_strategy)
    print(f"Result: {results_invalid}")

    syntax_error_strategy = "def generate_signals(data): print(data) x = "
    results_syntax = run_backtest(dummy_data.copy(), strategy_code=syntax_error_strategy)
    print(f"Result: {results_syntax}")

