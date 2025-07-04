def generate_signals(data: pd.DataFrame) -> pd.Series:
    """
    Donchian Channel Breakout (20-day) 전략에 따라 매수/매도 신호를 생성합니다.
    - 매수: 종가가 이전 기간의 Donchian Channel 상단 돌파 시
    - 매도: 종가가 이전 기간의 Donchian Channel 하단 돌파 시
    """
    # --- 파라미터 설정 ---
    period = 20 # Donchian Channel 기간

    # --- 신호 시리즈 초기화 (규칙 7) ---
    signals = pd.Series('hold', index=data.index)

    # --- Donchian Channel 계산 (벡터화, 규칙 6) ---
    # min_periods=period로 설정하여, period만큼의 데이터가 쌓이기 전까지는 NaN 반환
    upper_band = data['High'].rolling(window=period, min_periods=period).max()
    lower_band = data['Low'].rolling(window=period, min_periods=period).min()

    # shift(1)을 사용하여 현재 봉이 아닌 이전 봉의 채널 값을 기준으로 판단 (미래 데이터 참조 방지)
    prev_upper_band = upper_band.shift(1)
    prev_lower_band = lower_band.shift(1)

    # --- 매수 및 매도 조건 생성 (벡터화, 규칙 6) ---
    buy_condition = data['Close'] > prev_upper_band
    sell_condition = data['Close'] < prev_lower_band

    # --- 신호 적용 (규칙 14: 매수 우선) ---
    # 매도 조건을 먼저 적용하고, 그 위에 매수 조건을 덮어쓰면
    # 같은 날 둘 다 발생 시 매수가 최종 신호가 됨.
    signals.loc[sell_condition] = 'sell'
    signals.loc[buy_condition] = 'buy'

    # --- 초기 NaN 기간 처리 (규칙 8) ---
    # Donchian Channel 계산 및 shift(1)로 인해 period 만큼의 초기 데이터는 유효한 신호 생성 불가
    # (period-1) from rolling + 1 from shift = period
    if len(signals) >= period:
        signals.iloc[:period] = 'hold'
    else: # 데이터가 period보다 짧은 경우 전체를 'hold'
        signals[:] = 'hold'
        
    return signals