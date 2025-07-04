# 기본 전략: 첫날 매수 후 보유
def generate_signals(data):
    signals = pd.Series('hold', index=data.index)
    if not data.empty:
        signals.iloc[0] = 'buy'
    return signals
