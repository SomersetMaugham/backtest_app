def generate_signals(data):
    """
    Wyckoff 이론의 단순화된 매집(Accumulation) 패턴을 기반으로 매수/매도 신호를 생성합니다.

    매수 신호:
    1. N일간의 매집 범위(저점, 고점)가 형성된 후,
    2. 가격이 범위 저점 아래로 일시적으로 하락했다가(Spring) 다시 범위 안으로 회복하고,
    3. 이후 가격이 범위 고점을 돌파(Sign of Strength - SOS)한 뒤,
    4. SOS 발생 시점의 범위 고점 부근으로 되돌림을 줄 때 매수합니다.

    매도 신호 (청산):
    - 매수 신호를 유발했던 매집 패턴의 Spring 발생 시점의 범위 저점 아래로 종가가 형성될 때.
    """
    signals = pd.Series('hold', index=data.index)

    # 파라미터 설정
    n_range_period = 20  # 매집/분산 범위를 정의하기 위한 기간
    n_spring_lookback = 5 # SOS 발생 전 Spring을 찾기 위한 이전 기간
    n_pullback_window = 5 # SOS 발생 후 되돌림을 기다리는 기간
    pullback_tolerance_factor = 0.005 # 되돌림 목표 수준에 대한 허용 오차 (예: 고점의 0.5%)

    # 1. 매집/분산 범위 정의 (lookahead bias 피하기 위해 shift(1) 사용)
    data['range_low'] = data['Low'].rolling(window=n_range_period, min_periods=n_range_period // 2).min().shift(1)
    data['range_high'] = data['High'].rolling(window=n_range_period, min_periods=n_range_period // 2).max().shift(1)

    # 2. Spring (매집 범위 저점 하향 이탈 후 회복)
    #    - 현재 봉 저가가 이전 봉 기준 range_low보다 낮아야 함
    #    - 현재 봉 종가가 이전 봉 기준 range_low보다 높아야 함
    is_spring = (data['Low'] < data['range_low']) & \
                (data['Close'] > data['range_low'])

    # 3. Sign of Strength (SOS) (매집 범위 고점 상향 돌파)
    #    - 현재 봉 종가가 이전 봉 기준 range_high보다 높아야 함
    is_sos = (data['Close'] > data['range_high'])

    # Spring 이후 SOS가 발생했는지 확인하여 "셋업 형성" 상태를 정의
    # is_spring.shift(1)은 SOS 발생일 *이전*에 spring이 있었는지 확인하기 위함
    # min_periods=1은 lookback 기간 내 한 번이라도 spring이 있었으면 True
    had_recent_spring = is_spring.shift(1).rolling(window=n_spring_lookback, min_periods=1).sum() > 0
    is_setup_forming = is_sos & had_recent_spring

    # "셋업 형성" 상태 및 되돌림 목표가 유효한 기간을 설정 (n_pullback_window 기간 동안 유효)
    setup_active = is_setup_forming.rolling(window=n_pullback_window, min_periods=1).sum() > 0
    
    # 되돌림 매수 목표 수준 (SOS 발생 시점의 range_high)
    # is_setup_forming이 True일 때만 pullback_target_level 값을 설정하고, 이후 n_pullback_window-1 일 동안 ffill
    pullback_target_level = pd.Series(np.nan, index=data.index)
    pullback_target_level[is_setup_forming] = data['range_high'][is_setup_forming]
    pullback_target_level = pullback_target_level.ffill(limit=n_pullback_window -1) # SOS 발생 후 n일간 목표 유지

    # 4. Pullback to BUY (되돌림 시 매수)
    #    - setup_active 상태이고, 현재 봉 저가가 pullback_target_level 근처까지 하락 후 종가가 회복될 때
    tolerance = pullback_target_level * pullback_tolerance_factor
    is_pullback_buy_point = (data['Low'] <= (pullback_target_level + tolerance)) & \
                             (data['Close'] > (pullback_target_level - tolerance)) # 종가가 목표가 근처 또는 위에서 마감

    buy_conditions = setup_active & is_pullback_buy_point
    
    # 매수 신호가 발생했을 때의 Spring 시점의 range_low를 손절 라인으로 설정
    # 이 부분은 실제 백테스터에서 상태를 관리해야 더 정확하지만, 여기서는 근사치로 구현
    # is_setup_forming이 True일 때의 range_low를 기록
    stop_loss_basis_level = pd.Series(np.nan, index=data.index)
    stop_loss_basis_level[is_setup_forming] = data['range_low'][is_setup_forming]
    # 이 stop_loss_basis_level은 매수 신호가 발생했을 때 확정되어야 함.
    # generate_signals 함수는 상태를 저장하지 않으므로, buy_conditions가 True인 시점의
    # ffill된 stop_loss_basis_level을 사용.
    
    final_stop_loss_level = pd.Series(np.nan, index=data.index)
    if buy_conditions.any(): # 매수 조건이 하나라도 참이면
        # 매수 조건 만족시 그날의 ffill된 stop_loss_basis_level을 가져옴
        final_stop_loss_level[buy_conditions] = stop_loss_basis_level[buy_conditions] 
    final_stop_loss_level = final_stop_loss_level.ffill()


    # 5. 매도 신호 (청산)
    #    - 종가가 확정된 final_stop_loss_level 아래로 마감될 때
    sell_conditions = (data['Close'] < final_stop_loss_level)

    # 신호 적용 (매수가 매도보다 우선)
    # 순차적 적용: 먼저 매도, 그 다음 매수 (같은 날 발생 시 매수가 최종 신호)
    # 또는 상태를 가정: 직전이 'buy'나 'hold'(매수 후) 일때만 매도 가능
    
    # 임시로 상태를 추적하는 변수 (실제 백테스팅에서는 포지션 상태를 직접 사용)
    position = 0 # 0: 없음, 1: 매수 포지션
    for i in range(len(data)):
        if position == 0: # 포지션이 없을 때
            if buy_conditions.iloc[i]:
                signals.iloc[i] = 'buy'
                position = 1
        elif position == 1: # 매수 포지션을 보유 중일 때
            if sell_conditions.iloc[i]:
                signals.iloc[i] = 'sell'
                position = 0
            # 만약 새로운 매수 신호가 더 좋은 조건이라면? (여기선 단순화)
            # elif buy_conditions.iloc[i]: # 연속 매수 방지 또는 재진입 로직 필요
            #    signals.iloc[i] = 'buy' # 여기서는 단순화를 위해 재진입은 고려 안 함
            else:
                signals.iloc[i] = 'hold' # 계속 보유

    # 롤링 윈도우로 인해 초기에 NaN 값이 발생할 수 있는 기간은 'hold'로 명시적 처리
    # 가장 긴 lookback은 n_range_period + n_spring_lookback (shift(1) 때문에)
    # 또는 n_range_period + n_pullback_window
    # 안전하게 가장 긴 값으로 설정
    initial_hold_period = n_range_period + max(n_spring_lookback, n_pullback_window)
    signals.iloc[:initial_hold_period] = 'hold'

    return signals