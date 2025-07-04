# 3. MACD Signal Line Crossover
def generate_signals(data: pd.DataFrame) -> pd.Series:
    signals = pd.Series('hold', index=data.index)
    macd = data['Close'].ewm(span=12, adjust=False).mean() - data['Close'].ewm(span=26, adjust=False).mean()
    signal_line = macd.ewm(span=9, adjust=False).mean()
    buy = (macd > signal_line) & (macd.shift(1) <= signal_line.shift(1))
    sell = (macd < signal_line) & (macd.shift(1) >= signal_line.shift(1))
    signals.loc[buy] = 'buy'
    signals.loc[sell] = 'sell'
    return signals