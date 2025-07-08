import plotly.graph_objects as go
import pandas as pd

def create_candlestick_chart(data: pd.DataFrame, ticker: str, trades: list = None):
    """Creates an interactive Plotly candlestick chart with MA lines."""
    fig = go.Figure()

    # 1. Candlestick
    fig.add_trace(go.Candlestick(
        x=data.index,
        open=data["Open"],
        high=data["High"],
        low=data["Low"],
        close=data["Close"],
        increasing_line_color='#fc0303',
        decreasing_line_color='#0703fc',
        increasing_fillcolor='#fc0303',
        decreasing_fillcolor='#0703fc',        
        name="가격"
    ))

    # 2. 이동평균선 추가 (20, 60, 120)
    data = data.copy()
    data["MA20"] = data["Close"].rolling(window=20, min_periods=1).mean()
    data["MA60"] = data["Close"].rolling(window=60, min_periods=1).mean()
    data["MA120"] = data["Close"].rolling(window=120, min_periods=1).mean()

    fig.add_trace(go.Scatter(
        x=data.index, y=data["MA20"], mode='lines', name="MA20",
        line=dict(width=1.5, color='royalblue', dash='dot')
    ))
    fig.add_trace(go.Scatter(
        x=data.index, y=data["MA60"], mode='lines', name="MA60",
        line=dict(width=2.0, color='orange', dash='dash')
    ))
    fig.add_trace(go.Scatter(
        x=data.index, y=data["MA120"], mode='lines', name="MA120",
        line=dict(width=2.5, color='green', dash='solid')
    ))

    # 3. Buy/Sell Markers (기존과 동일)
    if trades:
        buy_dates = []
        buy_prices = []
        sell_dates_normal = []
        sell_prices_normal = []
        sell_dates_stoploss = []
        sell_prices_stoploss = []

        for trade in trades:
            if trade["buy_date"] in data.index:
                buy_dates.append(trade["buy_date"])
                buy_prices.append(data.loc[trade["buy_date"], "Low"] * 0.99)
            if trade["sell_date"] in data.index:
                if trade.get("stop_loss"):
                    sell_dates_stoploss.append(trade["sell_date"])
                    sell_prices_stoploss.append(data.loc[trade["sell_date"], "High"] * 1.01)
                else:
                    sell_dates_normal.append(trade["sell_date"])
                    sell_prices_normal.append(data.loc[trade["sell_date"], "High"] * 1.01)

        if buy_dates:
            fig.add_trace(go.Scatter(x=buy_dates, y=buy_prices, mode='markers',
                                     marker_symbol='triangle-up', marker_color='blue', marker_size=10,
                                     name='매수 신호', hoverinfo='x+name'))
        if sell_dates_normal:
            fig.add_trace(go.Scatter(x=sell_dates_normal, y=sell_prices_normal, mode='markers',
                                     marker_symbol='triangle-down', marker_color='black', marker_size=12,
                                     name='일반 매도', hoverinfo='x+name'))
        if sell_dates_stoploss:
            fig.add_trace(go.Scatter(x=sell_dates_stoploss, y=sell_prices_stoploss, mode='markers',
                                     marker_symbol='x', marker_color='red', marker_size=14,
                                     name='손절 매도', hoverinfo='x+name'))

    # 누락된 날짜(공휴일) 계산
    all_days   = pd.date_range(data.index.min(), data.index.max(), freq="D")
    missing    = all_days.difference(data.index)          # data에 없는 모든 날짜
    holidays   = [d for d in missing if d.weekday() < 5]   # 평일(월~금)만 추려 공휴일 목록

    # 4. Layout
    fig.update_layout(
        xaxis_title="날짜",
        yaxis_title="가격",
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
        height=700
    )

    # 여기 ↓ 추가 -------------------------------------------------
    fig.update_xaxes(
        rangebreaks=[
            dict(bounds=["sat", "mon"]),      # 주말 제거
            dict(values=holidays),            # 평일 공휴일 제거
        ],
        matches="x"                           # 두 x-축 동기화
    )
    # ------------------------------------------------------------

    fig.update_xaxes(rangeslider_visible=False)

    return fig
