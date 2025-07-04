# 8. Stochastic Oscillator (14,3)
def generate_signals_stochastic(data: pd.DataFrame,
                                k_period: int = 14,
                                d_period: int = 3) -> pd.Series:
    signals = pd.Series('hold', index=data.index)
    low_min = data['Low'].rolling(window=k_period, min_periods=k_period).min()
    high_max = data['High'].rolling(window=k_period, min_periods=k_period).max()
    data['%K'] = 100 * (data['Close'] - low_min) / (high_max - low_min)
    data['%D'] = data['%K'].rolling(window=d_period, min_periods=d_period).mean()
    buy = (data['%K'] > data['%D']) & (data['%K'].shift(1) <= data['%D'].shift(1))
    sell = (data['%K'] < data['%D']) & (data['%K'].shift(1) >= data['%D'].shift(1))
    signals.loc[buy] = 'buy'
    signals.loc[sell] = 'sell'
    return signals