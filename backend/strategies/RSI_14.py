# 4. RSI Overbought/Oversold (14-day)
def generate_signals(data: pd.DataFrame, period: int = 14,
                         lower: float = 30, upper: float = 70) -> pd.Series:
    signals = pd.Series('hold', index=data.index)
    delta = data['Close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    buy = rsi < lower
    sell = rsi > upper
    signals.loc[buy] = 'buy'
    signals.loc[sell] = 'sell'
    return signals