def generate_signals(data, bt_start_idx=None, lookback=120):
    # ---------------- 워밍업(룩백) 영역 ----------------
    if bt_start_idx is not None:
        warmup_mask = data.index < bt_start_idx            # 시작 시각 이전
    else:
        warmup_mask = pd.Series(False, index=data.index)
        warmup_mask.iloc[:lookback] = True                 # 앞쪽 lookback 봉

    # 1) 기본값은 모두 'hold'
    signals = pd.Series('hold', index=data.index)
    
    # 2) MACD, Signal, 120SMA 계산
    macd_fast = data['Close'].ewm(span=12, adjust=False).mean()
    macd_slow = data['Close'].ewm(span=26, adjust=False).mean()
    macd = macd_fast - macd_slow
    signal_ln = macd.ewm(span=9, adjust=False).mean()
    ma120 = data['Close'].rolling(window=120).mean()
    
    # 3) 조건식
    buy_cond = (
        (macd > signal_ln) &
        (macd.shift(1) <= signal_ln.shift(1)) &
        (data['Close'] > ma120)
    )
    sell_cond = (
        (macd < signal_ln) &
        (macd.shift(1) >= signal_ln.shift(1))
    )
    
    # ---- 워밍업 구간에서는 어떤 조건도 TRUE가 되지 않도록 차단 ----
    buy_cond[warmup_mask] = False
    sell_cond[warmup_mask] = False

    # 4) 신호 반영
    signals.loc[buy_cond] = 'buy'
    signals.loc[sell_cond] = 'sell'
    
    return signals