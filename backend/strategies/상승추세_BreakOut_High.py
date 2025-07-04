# 이 코드는 120일 이동평균을 포함한 전고점 돌파 전략을 구현합니다. 주요 로직은 다음과 같습니다:

# 이동평균을 계산하여 현재 가격이 120일 이동평균 위에 있을 때만 매수 신호를 생성합니다.
# 여전히 매수 조건은 종가가 전고점(직전 N일 최고가)을 돌파해야 합니다.
# 매수 후 종가가 전고점 아래로 내려오면 청산 신호('sell')를 생성합니다.
# 구매와 판매 신호는 처음 N일 동안 'hold'로 설정되어 있어 충분한 데이터로 첫 신호를 생성할 수 있습니다.
# 데이터의 영향을 받지 않도록 shift(1)을 사용하여 데이터 누수를 방지합니다.

def generate_signals(data):
    N = 20  # 전고점(최고가) 탐색 구간

    # 1. 전고점(rolling max, 오늘 제외) 구하기
    prev_high = data['High'].shift(1).rolling(window=N, min_periods=N).max()

    # 2. 120일 이동평균(오늘 제외) 구하기
    ma_120 = data['Close'].shift(1).rolling(window=120, min_periods=120).mean()

    # 3. 신호 시리즈를 'hold'로 초기화
    signals = pd.Series('hold', index=data.index)

    # 4. 이동평균 위에 있는지 확인
    above_ma_120 = data['Close'] > ma_120

    # 5. 돌파: 종가가 직전 N일 최고가(전고점)보다 크고, 120일 이동평균 위에 있을 때 'buy'
    buy_cond = (data['Close'] > prev_high) & above_ma_120

    # 6. 매수 이후, 종가가 전고점 밑으로 다시 내려오면 'sell'
    position = buy_cond.cumsum() - buy_cond.cumsum().where(~buy_cond).ffill().fillna(0)
    in_position = position > 0
    entry_high = prev_high.where(buy_cond).ffill()
    sell_cond = in_position & (data['Close'] < entry_high) & (~buy_cond)

    # 7. 신호 할당
    signals[buy_cond] = 'buy'
    signals[sell_cond] = 'sell'

    # 8. 초기 신호(N일 전까지)는 반드시 'hold'
    signals[:N] = 'hold'

    return signals