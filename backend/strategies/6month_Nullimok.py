def generate_signals(data):
    signals = pd.Series('hold', index=data.index)
    
    # 6개월(약 126일) 기간 동안의 최고가 계산
    rolling_high = data['Close'].rolling(window=126, min_periods=1).max()
    
    # 6개월 최고가 돌파 확인
    breakout = data['Close'] > rolling_high.shift(1)
    
    # 눌림목 확인: 현재 가격이 20일 이동평균선 아래에 있을 때
    ma_short = data['Close'].rolling(window=5, min_periods=1).mean()
    pullback = data['Close'] < ma_short
    
    # 매수 신호 발생 조건: 6개월 최고가 돌파 후 눌림목
    signals[breakout & pullback] = 'buy'
    
    return signals