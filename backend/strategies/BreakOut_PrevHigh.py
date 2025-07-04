def generate_signals(data):
    N = 20  # 전고점(최고가) 탐색 구간

    # 1. 전고점(rolling max, 오늘 제외) 구하기
    prev_high = data['High'].shift(1).rolling(window=N, min_periods=N).max()

    # 2. 신호 시리즈를 'hold'로 초기화
    signals = pd.Series('hold', index=data.index)

    # 3. 돌파: 종가가 직전 N일 최고가(전고점)보다 크면 'buy'
    buy_cond = data['Close'] > prev_high

    # 4. 매수 이후, 종가가 전고점 밑으로 다시 내려오면 'sell'
    # buy 발생 이후의 포지션을 추적하기 위해 포지션 플래그 벡터 생성
    position = buy_cond.cumsum() - buy_cond.cumsum().where(~buy_cond).ffill().fillna(0)
    in_position = position > 0

    # 매수한 시점의 전고점(돌파한 값) 기록
    entry_high = prev_high.where(buy_cond).ffill()

    # 'sell' 조건: in_position 상태에서 종가가 entry_high보다 작을 때
    sell_cond = in_position & (data['Close'] < entry_high) & (~buy_cond)

    # 5. 신호 할당
    signals[buy_cond] = 'buy'
    signals[sell_cond] = 'sell'

    # 6. 초기 신호(N일 전까지)는 반드시 'hold'
    signals[:N] = 'hold'

    return signals
