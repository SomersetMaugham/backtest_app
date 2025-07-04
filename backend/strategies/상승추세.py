def generate_signals(data):
    # 이평선 계산
    ma120 = data['Close'].rolling(window=120).mean()
    ma60 = data['Close'].rolling(window=60).mean()
    ma20 = data['Close'].rolling(window=20).mean()
    
    # 이평선 기울기 계산
    slope_ma120 = ma120.diff()
    slope_ma60 = ma60.diff()
    
    # 골든크로스 조건
    golden_cross = (ma60 > ma120) & (ma60.shift(1) <= ma120.shift(1))
    
    # 상승 추세 조건
    uptrend = (slope_ma60 > 0) & golden_cross
    
    # 매도 조건
    bearish_candle = (data['Close'] < data['Open']) & (data['Close'] < ma20) & (data['Close'].shift(1) >= ma20.shift(1))
    
    # 초기 신호 생성
    signals = pd.Series('hold', index=data.index)
    
    # 매수 신호 적용
    signals[uptrend] = 'buy'
    
    # 매도 신호 적용
    signals[bearish_candle] = 'sell'
    
    # 초기 NaN 기간 'hold' 유지
    signals.iloc[:120] = 'hold'
    
    return signals