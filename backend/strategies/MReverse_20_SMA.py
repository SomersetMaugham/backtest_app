# 10. Mean Reversion (Price vs 20-day SMA)
def generate_signals_mean_reversion(data: pd.DataFrame, period: int = 20,
                                     threshold: float = 0.05) -> pd.Series:
    signals = pd.Series('hold', index=data.index)
    sma = data['Close'].rolling(window=period, min_periods=period).mean()
    deviation = (data['Close'] - sma) / sma
    buy = deviation < -threshold
    sell = deviation > threshold
    signals.loc[buy] = 'buy'
    signals.loc[sell] = 'sell'
    return signals