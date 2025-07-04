def generate_signals(data):
    # 신호 시리즈 초기화 ('hold'로 채움)
    signals = pd.Series('hold', index=data.index)

    # 이동평균선 계산
    ma5 = data['Close'].rolling(window=5, min_periods=1).mean()
    ma20 = data['Close'].rolling(window=20, min_periods=1).mean()
    ma60 = data['Close'].rolling(window=60, min_periods=1).mean()

    # 1. 상승 추세 조건: MA20 > MA60
    uptrend = ma20 > ma60

    # 2. 눌림목: 이전 봉에서 종가가 MA5 아래(조정), 이번 봉에서 다시 MA5 상향돌파(반등)
    close_prev = data['Close'].shift(1)
    ma5_prev = ma5.shift(1)
    pullback_condition = (close_prev < ma5_prev) & (data['Close'] > ma5) & uptrend

    # 3. 매도 조건: 매수 후, 다시 MA5 하향 이탈(손절/청산)
    # - 이전 신호가 'buy'였고, 이번 봉에서 종가가 MA5 아래로 내려갈 때 'sell'
    buy_signal = pullback_condition.shift(1).fillna(False)
    sell_condition = (buy_signal) & (data['Close'] < ma5)

    # 신호 할당
    signals[pullback_condition] = 'buy'
    signals[sell_condition] = 'sell'

    # NaN이 있는 인덱스(rolling 초기 구간)는 'hold'로 처리
    signals[:max(5, 20, 60)-1] = 'hold'

    return signals
