# 한국어 요약 및 로직 설명:

# MACD와 Signal Line을 기반으로 한 매수/매도 전략: 기본적으로 MACD가 Signal Line을 상향 돌파할 때 'buy', 하향 돌파할 때 'sell' 신호를 생성합니다.
# 120일 이동평균 조건 추가: 매수 신호 발생 시 종가(Close)가 120일 이동평균(ma120)보다 큰 경우에만 'buy' 신호를 발생시킵니다.
# 벡터화 연산 사용: 모든 계산(ewm, rolling)의 결과는 Pandas 벡터 연산을 사용하여 효율적으로 수행됩니다.
# 초기 120일에는 신호 미발생: 120일 데이터가 쌓이기 전의 구간에서는 자연스럽게 신호를 'hold'로 유지합니다.

def generate_signals(data):
    # 모든 신호를 'hold'로 초기화
    signals = pd.Series('hold', index=data.index)

    # MACD와 Signal Line 계산
    macd = data['Close'].ewm(span=12, adjust=False).mean() - data['Close'].ewm(span=26, adjust=False).mean()
    signal_line = macd.ewm(span=9, adjust=False).mean()

    # 120일 이동평균 계산
    ma120 = data['Close'].rolling(window=120).mean()

    # 매수 조건: MACD가 Signal Line을 상향 돌파하고, 종가가 120일 이동평균보다 큰 경우
    buy_signal = (macd > signal_line) & (macd.shift(1) <= signal_line.shift(1)) & (data['Close'] > ma120)

    # 매도 조건: MACD가 Signal Line을 하향 돌파하는 경우
    sell_signal = (macd < signal_line) & (macd.shift(1) >= signal_line.shift(1))

    # 신호 업데이트
    signals.loc[buy_signal] = 'buy'
    signals.loc[sell_signal] = 'sell'

    return signals

