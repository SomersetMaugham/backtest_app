# 2. Exponential Moving Average Crossover (12/26 days)
def generate_signals(data):
    signals = pd.Series('hold', index=data.index)
    data['EMA_12'] = data['Close'].ewm(span=12, adjust=False).mean()
    data['EMA_26'] = data['Close'].ewm(span=26, adjust=False).mean()
    buy = (data['EMA_12'] > data['EMA_26']) & (data['EMA_12'].shift(1) <= data['EMA_26'].shift(1))
    sell = (data['EMA_12'] < data['EMA_26']) & (data['EMA_12'].shift(1) >= data['EMA_26'].shift(1))
    signals.loc[buy] = 'buy'
    signals.loc[sell] = 'sell'
    return signals