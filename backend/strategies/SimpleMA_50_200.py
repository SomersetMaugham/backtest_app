# 1. Simple Moving Average Crossover (50/200 days)
def generate_signals_sma_crossover(data: pd.DataFrame) -> pd.Series:
    signals = pd.Series('hold', index=data.index)
    data['SMA_50'] = data['Close'].rolling(window=50, min_periods=1).mean()
    data['SMA_200'] = data['Close'].rolling(window=200, min_periods=1).mean()
    buy = (data['SMA_50'] > data['SMA_200']) & (data['SMA_50'].shift(1) <= data['SMA_200'].shift(1))
    sell = (data['SMA_50'] < data['SMA_200']) & (data['SMA_50'].shift(1) >= data['SMA_200'].shift(1))
    signals.loc[buy] = 'buy'
    signals.loc[sell] = 'sell'
    return signals