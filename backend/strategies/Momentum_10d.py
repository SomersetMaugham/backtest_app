# 6. Momentum (10-day Rate of Change)
def generate_signals_momentum(data: pd.DataFrame, period: int = 10) -> pd.Series:
    signals = pd.Series('hold', index=data.index)
    roc = data['Close'].pct_change(periods=period)
    buy = roc > 0
    sell = roc < 0
    signals.loc[buy] = 'buy'
    signals.loc[sell] = 'sell'
    return signals