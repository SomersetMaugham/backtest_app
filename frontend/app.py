# -*- coding: utf-8 -*-
"""
주식 트레이딩 백테스트 웹 애플리케이션

이 애플리케이션은 Streamlit을 사용하여 주식 백테스트를 수행하는 웹 인터페이스를 제공합니다.
사용자는 종목을 선택하고, 트레이딩 전략을 설정하여 백테스트를 실행할 수 있습니다.
"""

import streamlit as st
import pandas as pd
import datetime
import requests
import base64
import time
import pymysql
from dotenv import load_dotenv
import os
import re
import concurrent.futures
from utils.charting import create_candlestick_chart
from datetime import timedelta
from urllib.parse import quote

# 환경 변수 로드
load_dotenv()

# 데이터베이스 설정
db_pw = os.getenv("MARIA_DB_PASSWORD")
db_name = os.getenv("MARIA_DB_NAME")

# 백엔드 API URL
BACKEND_URL = "http://127.0.0.1:5001"


def load_css():
    """외부 CSS 파일을 로드하여 스타일을 적용합니다."""
    try:
        with open('style.css', 'r', encoding='utf-8') as f:
            css_content = f.read()
        st.markdown(f'<style>{css_content}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning("style.css 파일을 찾을 수 없습니다. 기본 스타일이 적용됩니다.")


def initialize_session_state():
    """세션 상태를 초기화합니다."""
    default_values = {
        'company_name_buffer': "",
        'ticker': "",
        'start_date': datetime.date.today() - datetime.timedelta(days=365),
        'end_date': datetime.date.today(),
        'stock_data': None,
        'backtest_results': None,
        'strategy_code': """# 여기에 전략 코드를 입력하세요.""",
        'llm_chat_history': [],
        'saved_strategy_names': ["직접 코드 입력/생성"],
        'show_chat': False,
        'uploaded_image': None,
        'chat_image_uploader_key': 0,
        'strategy_selector': "직접 코드 입력/생성",
        'selected_stocks': [],
        'multi_backtest_results': {},
        'multi_stock_data': {},
        'is_multi_mode': False,
        'ticker_found': False,
    }

    for key, default_value in default_values.items():
        if key not in st.session_state:
            st.session_state[key] = default_value


# === 페이지 설정 ===
st.set_page_config(
    page_title="주식 트레이딩 백테스트",
    page_icon="�",
    layout="wide"
)

# CSS 로드 및 세션 상태 초기화
load_css()
initialize_session_state()

db_config = {
    'host': 'localhost',
    'user': 'stockuser',
    'password': db_pw,
    'database': db_name,
    'port': 3307,
    'charset': 'utf8mb4'
}

# === 데이터베이스 관련 함수 ===
def get_company_code(company_name):
    """회사명으로 주식 코드를 조회합니다."""
  
    conn = None
    try:
        conn = pymysql.connect(**db_config)
        cursor = conn.cursor()
        
        query = "SELECT code FROM company_info WHERE company = %s"
        cursor.execute(query, (company_name,))
        result = cursor.fetchone()
        
        return result[0] if result else None
        
    except Exception as e:
        print(f"Database error: {e}")
        return None
    finally:
        if conn:
            conn.close()

# ① 모든 회사·티커 불러오기 (캐싱!)
@st.cache_data
def load_company_options():
    conn = pymysql.connect(**db_config)
    df  = pd.read_sql("SELECT company, code FROM company_info", conn)
    conn.close()
    # [(회사명, 코드), ...] 형태로 반환
    return list(df.itertuples(index=False, name=None))      # ex) [("한화오션", "042660"), ...]

def company_select_on_change():
    """
    selectbox 가 변경될 때 호출.
    '회사명 (티커)' 문자열을 분리해 세션 상태에 저장합니다.
    """
    # choice = st.session_state.company_select_widget          # ex) '삼성전자 (005930)'
    # if not choice:
    #     return

    # import re
    # m = re.match(r"(.+)\s\((\d+)\)", choice)
    # if not m:    # 예외 처리
    #     st.session_state.ticker_found = False
    #     return

    # name, code = m.groups()
    name, code = st.session_state.company_select_widget
    st.session_state.company_name_buffer = name
    st.session_state.ticker               = code
    st.session_state.ticker_found         = True

# === 종목 관리 함수 ===
def add_stock_to_list():
    """현재 입력된 종목을 선택된 종목 목록에 추가합니다."""
    company_name = st.session_state.company_name_buffer.strip()
    ticker = st.session_state.ticker.strip()
    
    if not company_name or not ticker:
        st.error("유효한 회사명과 티커가 필요합니다.")
        return
    
    # 중복 확인
    for stock in st.session_state.selected_stocks:
        if stock['ticker'] == ticker:
            st.warning(f"{company_name}({ticker})는 이미 선택된 종목입니다.")
            return
    
    # 종목 추가
    new_stock = {'name': company_name, 'ticker': ticker}
    st.session_state.selected_stocks.append(new_stock)
    
    # 다중 모드 활성화
    if len(st.session_state.selected_stocks) > 1:
        st.session_state.is_multi_mode = True
    
    # 입력 필드 초기화
    st.session_state.company_name_buffer = ""
    st.session_state.ticker = ""
    st.session_state.ticker_found = False


# def remove_stock_from_list(index):
#     """선택된 종목 목록에서 종목을 제거합니다."""
#     if 0 <= index < len(st.session_state.selected_stocks):
#         removed_stock = st.session_state.selected_stocks.pop(index)
        
#         # 단일 모드로 전환 확인
#         if len(st.session_state.selected_stocks) <= 1:
#             st.session_state.is_multi_mode = False
        
#         st.success(f"{removed_stock['name']}({removed_stock['ticker']})가 제거되었습니다.")
    
#     # 마지막 종목까지 모두 삭제된 경우, 결과 초기화
#     if not st.session_state.selected_stocks:
#         st.session_state.stock_data = None
#         st.session_state.backtest_results = None
def remove_stock_from_list(ticker: str):
    stocks = st.session_state.selected_stocks
    st.session_state.selected_stocks = [s for s in stocks if s["ticker"] != ticker]

    if len(st.session_state.selected_stocks) <= 1:
        st.session_state.is_multi_mode = False

    if not st.session_state.selected_stocks:
        st.session_state.stock_data        = None
        st.session_state.backtest_results  = None
        st.session_state.candlestick_fig   = None

def clear_all_stocks():
    """모든 선택된 종목을 제거합니다."""
    st.session_state.selected_stocks = []
    st.session_state.is_multi_mode = False
    st.session_state.multi_backtest_results = {}
    st.session_state.multi_stock_data = {}
    st.session_state.stock_data = None
    st.session_state.backtest_results = None


# === API 호출 함수 ===
@st.cache_data(ttl=3600)
def fetch_data_cached(ticker, start_date, end_date):
    # # ----------------- 날짜 버퍼 로직 (수정 부분) -----------------
    # lookback_days = max_window * 2                     # 여유분 포함
    # api_start_date  = start_date - timedelta(days=lookback_days)
    # api_end_date    = end_date
    # # -----------------------------------------------------------
    """캐시된 주식 데이터를 조회합니다."""
    return fetch_data(ticker, start_date, end_date)


def fetch_data(ticker, start_date, end_date):

    """백엔드 API에서 주식 데이터를 조회합니다."""
    api_endpoint = f"{BACKEND_URL}/api/stock_data"
    params = {
        "ticker": ticker,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d")
    }
    
    try:
        response = requests.get(api_endpoint, params=params, timeout=20)
        response.raise_for_status()
        data_dict = response.json()
        
        if not data_dict or "error" in data_dict:
            st.error(f"백엔드에서 데이터를 가져오지 못했습니다: {data_dict.get('error', '알 수 없는 이유')}")
            return None
            
        df = pd.DataFrame.from_dict(data_dict, orient="index")
        df.index = pd.to_datetime(df.index)
        
        # 수치 데이터 변환
        for col in ["Open", "High", "Low", "Close", "Volume"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        df.sort_index(inplace=True)
        print(df)
        return df
        
    except requests.exceptions.Timeout:
        st.error("데이터 요청 시간 초과 (Timeout > 20초).")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"데이터 요청 실패: {e}")
        return None
    except Exception as e:
        st.error(f"데이터 처리 중 오류 발생: {e}")
        return None


def call_llm_api(history, message, image_bytes=None):
    """LLM API를 호출하여 AI 응답을 받습니다."""
    api_endpoint = f"{BACKEND_URL}/api/llm_chat"
    payload = {"history": history, "message": message}
    
    if image_bytes:
        payload["image"] = base64.b64encode(image_bytes).decode("utf-8")
    
    try:
        response = requests.post(api_endpoint, json=payload, timeout=120)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        st.error("AI 챗봇 요청 시간 초과 (Timeout > 120초).")
        return {"error": "AI 챗봇 요청 시간 초과"}
    except requests.exceptions.RequestException as e:
        st.error(f"AI 챗봇 요청 실패: {e}")
        return {"error": f"AI 챗봇 요청 실패: {e}"}
    except Exception as e:
        st.error(f"AI 챗봇 응답 처리 중 오류 발생: {e}")
        return {"error": f"AI 챗봇 응답 처리 중 오류 발생: {e}"}


def run_backend_backtest(stock_df, strategy_code_str, initial_capital, stop_loss_pct, trade_fee_pct, sell_tax_pct):
    """백엔드에서 백테스트를 실행합니다."""
    api_endpoint = f"{BACKEND_URL}/api/backtest"
    data_dict = {str(idx): row.to_dict() for idx, row in stock_df.iterrows()}
    payload = {
        "data": data_dict,
        "strategy_code": strategy_code_str,
        "initial_capital": initial_capital,
        "stop_loss_pct": stop_loss_pct,
        "trade_fee_pct": trade_fee_pct,
        "sell_tax_pct": sell_tax_pct
    }
    
    try:
        response = requests.post(api_endpoint, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        st.error("백테스트 실행 요청 시간 초과 (Timeout > 60초).")
        return {"error": "백테스트 실행 요청 시간 초과"}
    except requests.exceptions.RequestException as e:
        st.error(f"백테스트 실행 요청 실패: {e}")
        return {"error": f"백테스트 실행 요청 실패: {e}"}
    except Exception as e:
        st.error(f"백테스트 결과 처리 중 오류 발생: {e}")
        return {"error": f"백테스트 결과 처리 중 오류 발생: {e}"}


# === 백테스트 실행 함수 ===
def run_single_backtest(stock, settings):
    """단일 종목 백테스트를 실행합니다."""
    try:
        # 데이터 조회
        data = fetch_data_cached(
            stock['ticker'],
            settings['start_date'],
            settings['end_date']
        )

        if data is None:
            return {'error': f"{stock['name']} 데이터 조회 실패"}

        # 백테스트 실행
        result = run_backend_backtest(
            data,
            settings['strategy_code'],
            settings['initial_capital'],
            settings['stop_loss_pct'],
            settings['trade_fee_pct'],
            settings['sell_tax_pct']
        )

        if 'error' in result:
            return {'error': f"{stock['name']} 백테스트 실패: {result['error']}"}

        return {
            'stock_data': data,
            'backtest_results': result,
            'stock_info': stock
        }

    except Exception as e:
        return {'error': f"{stock['name']} 처리 중 오류: {str(e)}"}


def run_multi_backtest_parallel(stocks, settings, max_workers=3):
    """병렬로 다중 종목 백테스트를 실행합니다."""
    results = {}

    # 진행 상황 표시
    progress_bar = st.progress(0)
    status_text = st.empty()

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 모든 종목에 대해 작업 제출
        future_to_stock = {
            executor.submit(run_single_backtest, stock, settings): stock
            for stock in stocks
        }

        completed = 0
        total = len(stocks)

        for future in concurrent.futures.as_completed(future_to_stock):
            stock = future_to_stock[future]
            completed += 1

            # 진행 상황 업데이트
            progress_bar.progress(completed / total)
            status_text.text(f"처리 완료: {stock['name']} ({completed}/{total})")

            try:
                result = future.result()
                results[stock['ticker']] = result
            except Exception as e:
                results[stock['ticker']] = {'error': f"예외 발생: {str(e)}"}

    progress_bar.empty()
    status_text.empty()

    return results


# === 전략 관리 함수 ===
def fetch_strategies(name=None):
    """저장된 전략 목록을 조회하거나 특정 전략의 코드를 가져옵니다."""
    api_endpoint = f"{BACKEND_URL}/api/strategies"
    params = {"name": name} if name else {}
    
    try:
        response = requests.get(api_endpoint, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"전략 정보 요청 실패: {e}")
        return None


def save_strategy_code(name, code):
    """전략 코드를 백엔드에 저장합니다."""
    api_endpoint = f"{BACKEND_URL}/api/strategies"
    payload = {"name": name, "code": code}
    
    try:
        response = requests.post(api_endpoint, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"전략 저장 요청 실패: {e}")
        return {"error": f"전략 저장 실패: {e}"}


def delete_strategy_code(name):
    """백엔드에서 전략을 삭제합니다."""
    api_endpoint = f"{BACKEND_URL}/api/strategies/{name}"
    
    try:
        response = requests.delete(api_endpoint, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"전략 삭제 요청 실패: {e}")
        return {"error": f"전략 삭제 실패: {e}"}


# === 콜백 함수 ===
def load_strategy_list():
    """전략 목록을 로드합니다."""
    result = fetch_strategies()
    placeholder = "직접 코드 입력/생성"

    if result and "strategies" in result:
        strategy_names = [s for s in result["strategies"] if s != placeholder]
        st.session_state.saved_strategy_names = [placeholder] + sorted(strategy_names)
    else:
        st.session_state.saved_strategy_names = [placeholder]


def handle_strategy_selection():
    """전략 선택 시 호출되는 콜백 함수입니다."""
    selected_name = st.session_state.strategy_selector

    if selected_name == "직접 코드 입력/생성":
        st.session_state.strategy_code = """# 여기에 직접 전략 코드를 입력하세요."""
    else:
        with st.spinner(f"'{selected_name}' 전략 코드 로딩 중..."):
            result = fetch_strategies(name=selected_name)
            if result and "code" in result:
                st.session_state.strategy_code = result["code"]
                st.toast(f"'{selected_name}' 전략 로드 완료.", icon="✅")
            else:
                st.error(f"'{selected_name}' 전략 코드를 불러오지 못했습니다.")


def update_ticker():
    """회사명 입력 변경에 따라 티커를 업데이트합니다."""
    name = st.session_state.company_name_buffer.strip()
    ticker = get_company_code(name)

    st.session_state.ticker = ticker or ""
    st.session_state.ticker_found = bool(ticker)


def company_name_input_on_change():
    """회사명 입력 위젯의 변경 콜백 함수입니다."""
    st.session_state.company_name_buffer = st.session_state.company_name_input_widget
    update_ticker()


# === 유틸리티 함수 ===
def format_won(n):
    """숫자를 원화 형식으로 포맷팅합니다."""
    try:
        return f"{int(n):,}"
    except:
        return ""


# === 결과 표시 함수 ===
def display_candlestick_chart(stock_data, ticker, trades, title_suffix=""):
    """캔들스틱 차트를 표시합니다."""
    if stock_data is not None and not stock_data.empty:
        try:
            fig = create_candlestick_chart(stock_data, ticker, trades)
            if fig:
                st.plotly_chart(fig, use_container_width=True, key=f"chart_{ticker}")
            else:
                st.error("차트 생성에 실패했습니다.")
        except Exception as e:
            st.error(f"차트 생성 중 오류 발생: {e}")
    else:
        st.info("차트를 표시할 데이터가 없습니다.")


def colored_metric(label, value, delta="", color="#f5f5f5", help_text=None):
    """컬러 메트릭을 표시합니다."""
    help_icon_html = ""
    if help_text:
        help_icon_html = f'<span title="{help_text}" style="cursor: help; margin-left: 0.3em; font-size: 0.9em; opacity: 0.7;">ℹ️</span>'
    
    st.markdown(f"""
    <div style="background-color: {color}; padding: 1rem; border-radius: 8px; text-align: center; border: 1px solid #ddd;">
        <h3 style="margin: 0; font-size: 0.9rem; color: #666;">{label}{help_icon_html}</h3>
        <p style="margin: 0.5rem 0 0 0; font-size: 1.5rem; font-weight: bold; color: #333;">{value}</p>
        {f'<p style="margin: 0; font-size: 0.8rem; color: #888;">{delta}</p>' if delta else ''}
    </div>
    """, unsafe_allow_html=True)


def display_performance_metrics(metrics, title_suffix=""):
    """성과 지표를 표시합니다."""
    if metrics:
        # 첫 번째 행 (4개)
        pl_ratio = metrics.get('profit_loss_ratio', 0)
        pl_display = "N/A" if pl_ratio in (None, "inf") else f"{pl_ratio:.2f}"

        row1 = st.columns(4, gap="small")

        with row1[0]:
            colored_metric(
                "전체 수익률 (%)",
                f"{metrics.get('total_return', 0):.2f}",
                color="#E8F2FC",
                help_text="(최종 자산 / 초기 자본 - 1) × 100"
            )
        with row1[1]:
            colored_metric(
                "승률 (%)",
                f"{metrics.get('win_rate', 0):.2f}",
                color="#E8F2FC",
                help_text="(이익 거래수 / 전체 거래수) × 100"
            )
        with row1[2]:
            colored_metric(
                "손익비",
                pl_display,
                color="#E8F2FC",
                help_text="평균 이익금 / 평균 손실금"
            )
        with row1[3]:
            colored_metric(
                "총 거래 수",
                f"{metrics.get('num_trades', 0)}",
                color="#E8F2FC",
                help_text="전체 매수-매도 완료된 거래 횟수"
            )

        st.markdown("<br>", unsafe_allow_html=True)

        # 두 번째 행 (4개)
        row2 = st.columns(4, gap="small")

        mdd = metrics.get("max_drawdown_pct")
        with row2[0]:
            colored_metric(
                "최대 낙폭 MDD (%)",
                f"{mdd:.2f}" if mdd is not None else "N/A",
                color="#E8F2FC",
                help_text="투자 중 자산이 최고점 대비 최대 하락 비율"
            )

        sharpe = metrics.get("sharpe_ratio")
        with row2[1]:
            colored_metric(
                "Sharpe Ratio",
                f"{sharpe:.2f}" if sharpe is not None else "N/A",
                color="#E8F2FC",
                help_text="변동성 대비 초과수익의 척도"
            )

        sqn = metrics.get("sqn")
        with row2[2]:
            colored_metric(
                "SQN",
                f"{sqn:.2f}" if sqn is not None else "N/A",
                color="#E8F2FC",
                help_text="System Quality Number (시스템 품질지수)"
            )

        final_asset = metrics.get("final_asset")
        with row2[3]:
            colored_metric(
                "최종 자산",
                f"{final_asset:,.0f}" if final_asset is not None else "N/A",
                color="#E8F2FC",
                help_text="모든 거래 종료 후 최종 남은 자산"
            )
    else:
        st.warning("성과 지표를 계산할 수 없습니다.")


def display_trade_history(trades, title_suffix=""):
    """거래 내역을 표시합니다."""
    if trades:
        trades_df = pd.DataFrame(trades)
        if not trades_df.empty:
            # 통계 계산
            profit_mask = trades_df["return_pct"] > 0
            count_profit = int(profit_mask.sum())
            count_loss = int((~profit_mask).sum())
            total_trades = count_profit + count_loss

            profit_pct = (count_profit / total_trades * 100) if total_trades else 0.0
            loss_pct = (count_loss / total_trades * 100) if total_trades else 0.0

            if "holding_period" in trades_df.columns:
                avg_holding_days = trades_df["holding_period"].mean()
                avg_holding_txt = f"{avg_holding_days:.1f}일"
            else:
                avg_holding_txt = "—"

            # 데이터 정렬 및 포맷팅
            trades_df['buy_date'] = pd.to_datetime(trades_df['buy_date'])
            trades_df['sell_date'] = pd.to_datetime(trades_df['sell_date'])
            trades_df = trades_df.sort_values(by='sell_date', ignore_index=True)
            trades_df.index = pd.RangeIndex(start=1, stop=len(trades_df)+1)
            trades_df.index.name = "거래 순서"

            # 컬럼명 변경
            trades_display_df = trades_df.rename(columns={
                "buy_date": "매수일 (Buy Date)",
                "buy_price": "매수 가격 (Buy Price)",
                "sell_date": "매도일 (Sell Date)",
                "sell_price": "매도 가격 (Sell Price)",
                "profit_loss": "손익 (Profit/Loss)",
                "return_pct": "수익률 (Return %)",
                "buy_qty": "매수 수량 (Quantity)",
                "buy_fee": "매수 수수료 (Buy Fee)",
                "total_buy_amount": "매수 총액 (수수료 포함)",
                "sell_fee": "매도 수수료 (Sell Fee)",
                "sell_tax": "매도 세금 (Sell Tax)",
                "total_sell_amount": "매도 총액 (수수료, 세금 포함)",
                "exit_type": "매도 형태 (Sell Type)",
                "holding_period": "보유 기간 (Holding Days)"
            })

            # 날짜 포맷팅
            trades_display_df["매수일 (Buy Date)"] = trades_display_df["매수일 (Buy Date)"].dt.strftime("%Y-%m-%d")
            trades_display_df["매도일 (Sell Date)"] = trades_display_df["매도일 (Sell Date)"].dt.strftime("%Y-%m-%d")

            # 수치 포맷팅
            numeric_columns = [
                "매수 가격 (Buy Price)", "매도 가격 (Sell Price)", "손익 (Profit/Loss)",
                "매수 수수료 (Buy Fee)", "매수 총액 (수수료 포함)", "매도 수수료 (Sell Fee)",
                "매도 세금 (Sell Tax)", "매도 총액 (수수료, 세금 포함)", "보유 기간 (Holding Days)"
            ]
            
            for col in numeric_columns:
                if col in trades_display_df.columns:
                    trades_display_df[col] = trades_display_df[col].map("{:,.0f}".format)
            
            trades_display_df["수익률 (Return %)"] = trades_display_df["수익률 (Return %)"].map("{:.2f}%".format)
            trades_display_df["매도 형태 (Sell Type)"] = trades_display_df["매도 형태 (Sell Type)"].map({
                "signal": "일반",
                "stop_loss": "손절",
                "final_close": "종료"
            }).fillna("일반")

            # 컬럼 순서 정렬
            ordered_columns = [
                "매수일 (Buy Date)", "매수 가격 (Buy Price)", "매수 수량 (Quantity)",
                "매수 수수료 (Buy Fee)", "매수 총액 (수수료 포함)", "매도일 (Sell Date)",
                "매도 가격 (Sell Price)", "매도 수수료 (Sell Fee)", "매도 세금 (Sell Tax)",
                "매도 총액 (수수료, 세금 포함)", "매도 형태 (Sell Type)", "손익 (Profit/Loss)",
                "수익률 (Return %)", "보유 기간 (Holding Days)"
            ]

            trades_display_df = trades_display_df[ordered_columns]
            trades_display_df = trades_display_df.dropna(how='all')

            # 데이터프레임 표시
            column_configs = {
                col: st.column_config.TextColumn(label=col, width="medium", default="")
                for col in trades_display_df.columns
            }

            st.dataframe(
                trades_display_df,
                use_container_width=True,
                hide_index=False,
                column_config=column_configs
            )

            # 통계 요약
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(
                f"""
                <div style="background-color: #F8F9FA; border-radius: 10px; padding: 1rem; border: 1px solid #E0E6ED;">
                    <h3 style="margin: 0 0 0.8rem 0; font-size: 1.1rem; color: #2C3E50;">거래 통계 요약</h3>
                    <div style="display: flex; justify-content: space-between;">
                        <div>
                            <span class="status-badge status-profit">이익 거래</span>
                            {count_profit}건 ({profit_pct:.1f}%)
                        </div>
                        <div>
                            <span class="status-badge status-loss">손실 거래</span>
                            {count_loss}건 ({loss_pct:.1f}%)
                        </div>
                        <div>
                            <span class="status-badge status-neutral">평균 보유 기간</span>
                            {avg_holding_txt}
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.warning("백테스트 기간 동안 거래가 없습니다.")
    else:
        st.info("거래 내역이 없습니다.")


# === 초기 전략 목록 로드 ===
if 'saved_strategy_names' not in st.session_state or st.session_state.saved_strategy_names == ["직접 코드 입력/생성"]:
    load_strategy_list()


# === 메인 UI 레이아웃 ===

# 사이드바 - 설정 패널
with st.sidebar:
    st.header("⚙️ 설정")

    # 1. 종목 선택 섹션
    st.subheader("종목 선택")

    # 회사명 입력과 종목 추가 버튼을 같은 행에 배치
    col_input, col_add = st.columns([3, 1])

    with col_input:
        # st.text_input(
        #     "회사 이름 (예: 삼성전자, Apple)",
        #     value=st.session_state.company_name_buffer,
        #     on_change=company_name_input_on_change,
        #     key="company_name_input_widget",
        #     label_visibility="collapsed",
        #     placeholder="회사 이름을 입력하세요",
        # )
        st.selectbox(
            "회사 이름 (예: 삼성전자, Apple)",
            options      = load_company_options(),        # 캐싱된 리스트
            key          = "company_select_widget",        # 새 위젯 키
            on_change    = company_select_on_change,       # 선택 시 상태 갱신
            placeholder  = "회사 이름을 입력하세요",          # Streamlit ≥ 1.28
            label_visibility = "collapsed",
            format_func   = lambda item: item[0],   # � 화면엔 회사명만!
        )

    with col_add:
        if st.button("➕", key="add_stock_btn", help="종목 추가", use_container_width=True):
            add_stock_to_list()

    # 조회 결과 표시
    if "ticker_found" in st.session_state:
        if st.session_state.ticker_found:
            st.success(f"✅ 조회된 티커: {st.session_state.ticker}")
        elif st.session_state.company_name_buffer.strip():
            st.warning("⚠️ 해당 회사명의 티커를 찾을 수 없습니다.")

    # 선택된 종목 목록 표시
    if st.session_state.selected_stocks:
        st.markdown("**선택된 종목:**")

        for i, stock in enumerate(st.session_state.selected_stocks):
            col_stock, col_remove = st.columns([4, 1])

            with col_stock:
                st.markdown(f"""
                <div class="selected-stock-item">
                    <span class="stock-info">{stock['name']}</span>
                    <span class="stock-ticker">({stock['ticker']})</span>
                </div>
                """, unsafe_allow_html=True)

            # with col_remove:
            #     if st.button("❌", key=f"remove_stock_{i}", help=f"{stock['name']} 제거"):
            #         remove_stock_from_list(i)
            #         st.rerun()
            with col_remove:
                if st.button(
                    "❌",
                    key=f"remove_stock_{stock['ticker']}",    # � 고정 key!
                    help=f"{stock['name']} 제거"
                ):
                    remove_stock_from_list(stock["ticker"])
                    st.rerun()
        # 전체 삭제 버튼
        if len(st.session_state.selected_stocks) > 1:
            if st.button("전체 삭제", key="clear_all_stocks"):
                clear_all_stocks()
                st.rerun()

        # 다중 모드 표시
        if st.session_state.is_multi_mode:
            st.info(f"다중 종목 모드 ({len(st.session_state.selected_stocks)}개 종목)")

    st.divider()

    # 2. 기간 설정
    st.subheader("기간 설정")
    col_date1, col_date2 = st.columns(2)

    with col_date1:
        st.session_state["start_date"] = st.date_input(
            "시작일",
            value=st.session_state["start_date"],
            key="start_date_input",
        )
    with col_date2:
        st.session_state["end_date"] = st.date_input(
            "종료일",
            value=st.session_state["end_date"],
            key="end_date_input",
        )

    # 날짜 범위 검증
    if st.session_state.start_date >= st.session_state.end_date:
        st.error("오류: 시작일은 종료일보다 이전이어야 합니다.")
        start_button_disabled = True
    else:
        start_button_disabled = False

    st.divider()

    # 3. 백테스트 설정
    st.subheader("백테스트 설정")

    # 초기 자본금 입력창
    input_str = st.text_input(
        "초기 자본금",
        value=format_won(st.session_state.get("initial_capital", 10000000)),
        help="금액을 입력하세요 (예: 1,000,000)"
    )

    # 입력값에서 콤마 제거 후 숫자로 변환
    parsed_capital = int(re.sub(r'[^\d]', '', input_str)) if re.sub(r'[^\d]', '', input_str) else 10000
    st.session_state.initial_capital = parsed_capital
    st.caption(f"입력한 금액: {parsed_capital:,}원")

    # 손절(손실 제한 매도, Stop Loss)
    stop_loss = st.number_input(
        "손실 제한 매도 (Stop Loss, %)",
        min_value=0.0, max_value=50.0, value=5.0, step=0.1,
        help="매수 후 몇 % 하락 시 자동으로 손실 제한 매도(손절)합니다."
    )
    st.session_state.stop_loss_pct = stop_loss

    # 매매 수수료
    trade_fee_str = st.text_input(
        "매매 수수료 (%)", value="0.015", help="키움증권 영웅문 기준, 0.015%입니다."
    )
    try:
        trade_fee_pct = float(trade_fee_str)
    except ValueError:
        trade_fee_pct = 0.0

    # 매도세
    sell_tax = st.number_input(
        "증권 거래세 (Trade Tax, %)",
        min_value=0.0, max_value=100.0, value=0.2, step=0.1,
        help="매도 거래에만 발생합니다."
    )

    st.divider()

    # 4. 전략 설정
    st.subheader("📊 전략 설정")

    # LLM Chat Expander
    chat_expander = st.expander("🤖 AI와 전략 대화하기", expanded=st.session_state.show_chat)
    with chat_expander:
        st.session_state.show_chat = True
        for message in st.session_state.llm_chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        uploaded_file = st.file_uploader(
            "차트 이미지 첨부 (선택 사항)",
            type=["png", "jpg", "jpeg"],
            key=f"chat_image_uploader_{st.session_state.chat_image_uploader_key}"
        )
        if uploaded_file is not None:
            st.session_state.uploaded_image = uploaded_file
            st.image(uploaded_file, width=100, caption="첨부될 이미지")

        if prompt := st.chat_input("전략 아이디어를 입력하거나 질문하세요..."):
            user_message_content = prompt
            user_message_payload = {"role": "user", "content": user_message_content}
            st.session_state.llm_chat_history.append(user_message_payload)

            image_bytes_to_send = None
            current_uploaded_image = st.session_state.uploaded_image
            if current_uploaded_image:
                image_bytes_to_send = current_uploaded_image.getvalue()

            with st.chat_message("user"):
                if current_uploaded_image:
                    st.image(current_uploaded_image, width=100)
                st.markdown(user_message_content)

            st.session_state.uploaded_image = None
            st.session_state.chat_image_uploader_key += 1

            with st.spinner("AI 응답 생성 중..."):
                llm_result = call_llm_api(st.session_state.llm_chat_history, user_message_content, image_bytes_to_send)

            if llm_result and "response" in llm_result:
                response_content = llm_result["response"]
                assistant_message_payload = {"role": "assistant", "content": response_content}
                st.session_state.llm_chat_history.append(assistant_message_payload)

                code_blocks = [block.strip("python\n ") for block in response_content.split("```") if block.startswith("python")]
                if code_blocks:
                    st.session_state.strategy_code = code_blocks[-1]
                    st.toast("✅ AI가 제안한 전략 코드로 업데이트되었습니다.")
                    st.session_state.strategy_selector = "직접 코드 입력/생성"

                st.rerun()

            elif llm_result:
                st.error(f"AI 응답 오류: {llm_result.get('error', '알 수 없는 오류')}")
            else:
                st.error("AI 챗봇으로부터 유효한 응답을 받지 못했습니다.")

    # 저장된 전략 선택
    st.selectbox(
        "저장된 전략 선택 또는 직접 입력",
        options=st.session_state.saved_strategy_names,
        key="strategy_selector",
        on_change=handle_strategy_selection
    )

    # 선택된 전략 삭제 버튼
    if st.session_state.strategy_selector != "직접 코드 입력/생성":
        if st.button(f"'{st.session_state.strategy_selector}' 전략 삭제", key="delete_strategy_button"):
            strategy_to_delete = st.session_state.strategy_selector
            with st.spinner(f"'{strategy_to_delete}' 삭제 중..."):
                delete_result = delete_strategy_code(strategy_to_delete)
                if delete_result and "error" not in delete_result:
                    st.toast(f"'{strategy_to_delete}' 삭제 완료.", icon="✅")
                    st.session_state.strategy_selector = "직접 코드 입력/생성"
                    st.session_state.strategy_code = """# 여기에 직접 전략 코드를 입력하세요."""
                    load_strategy_list()
                    time.sleep(0.5)
                    st.rerun()

    # 전략 코드 영역
    st.text_area(
        "전략 코드 (Python)",
        value=st.session_state.strategy_code,
        height=250,
        key="strategy_code_area_widget"
    )
    st.session_state.strategy_code = st.session_state.strategy_code_area_widget

    # 전략 저장 섹션
    save_strategy_expander = st.expander("현재 전략 저장하기")
    with save_strategy_expander:
        strategy_name_to_save = st.text_input("저장할 전략 이름:", key="save_strategy_name_input").strip()
        code_to_save = st.session_state.strategy_code

        if st.button("전략 저장", key="save_strategy_button"):
            if not strategy_name_to_save:
                st.error("전략 이름을 입력해주세요.")
            elif strategy_name_to_save == "직접 코드 입력/생성":
                st.error("'직접 코드 입력/생성'은 전략 이름으로 사용할 수 없습니다. 다른 이름을 입력하세요.")
            elif not code_to_save.strip():
                st.error("저장할 전략 코드가 없습니다.")
            else:
                with st.spinner(f"'{strategy_name_to_save}' 저장 중..."):
                    save_result = save_strategy_code(strategy_name_to_save, code_to_save)
                    if save_result and "error" not in save_result:
                        st.toast(f"'{strategy_name_to_save}' 저장 완료.", icon="✅")
                        load_strategy_list()
                        time.sleep(0.5)
                        st.rerun()

    st.divider()

    # 5. 백테스트 시작 버튼
    # 백테스트 실행 조건 확인
    can_run_backtest = False
    backtest_error_msg = ""

    if st.session_state.is_multi_mode:
        # 다중 종목 모드
        if len(st.session_state.selected_stocks) > 0:
            can_run_backtest = True
        else:
            backtest_error_msg = "선택된 종목이 없습니다."
    else:
        # 단일 종목 모드
        if st.session_state.company_name_buffer.strip() and st.session_state.ticker_found:
            can_run_backtest = True
        elif not st.session_state.company_name_buffer.strip():
            backtest_error_msg = "회사명을 입력해주세요."
        else:
            backtest_error_msg = "유효한 티커를 찾을 수 없습니다."

    if start_button_disabled:
        can_run_backtest = False
        backtest_error_msg = "날짜 범위를 확인해주세요."

    if can_run_backtest:
        if st.button("백테스트 시작", key="start_backtest_button", use_container_width=True, disabled=start_button_disabled, type="primary"):
            # 백테스트 설정 준비
            backtest_settings = {
                'start_date': st.session_state.start_date,
                'end_date': st.session_state.end_date,
                'strategy_code': st.session_state.strategy_code,
                'initial_capital': st.session_state.initial_capital,
                'stop_loss_pct': st.session_state.stop_loss_pct,
                'trade_fee_pct': trade_fee_pct,
                'sell_tax_pct': sell_tax
            }

            if st.session_state.is_multi_mode:
                # 다중 종목 백테스트 실행
                st.info("다중 종목 백테스트를 시작합니다...")

                with st.spinner("백테스트 실행 중..."):
                    results = run_multi_backtest_parallel(
                        st.session_state.selected_stocks,
                        backtest_settings
                    )

                # 결과 저장
                st.session_state.multi_backtest_results = results

                # 성공/실패 종목 분류
                success_count = 0
                error_count = 0

                for ticker, result in results.items():
                    if 'error' in result:
                        error_count += 1
                    else:
                        success_count += 1
                        # 개별 종목 데이터도 저장
                        st.session_state.multi_stock_data[ticker] = result.get('stock_data')

                # 결과 요약 표시
                if success_count > 0:
                    st.success(f"✅ {success_count}개 종목 백테스트 완료!")
                if error_count > 0:
                    st.warning(f"⚠️ {error_count}개 종목에서 오류 발생")

                # 첫 번째 성공한 종목을 현재 표시용으로 설정
                for ticker, result in results.items():
                    if 'error' not in result:
                        st.session_state.stock_data = result.get('stock_data')
                        st.session_state.backtest_results = result.get('backtest_results')
                        break

            else:
                # 단일 종목 백테스트 실행 (기존 로직)
                st.info("백테스트를 시작합니다...")

                # 현재 입력된 종목으로 단일 백테스트
                current_stock = {
                    'name': st.session_state.company_name_buffer,
                    'ticker': st.session_state.ticker
                }

                with st.spinner("백테스트 실행 중..."):
                    result = run_single_backtest(current_stock, backtest_settings)

                if 'error' in result:
                    st.error(f"백테스트 실행 실패: {result['error']}")
                else:
                    st.session_state.stock_data = result.get('stock_data')
                    st.session_state.backtest_results = result.get('backtest_results')
                    st.success("✅ 백테스트 완료!")

            # 페이지 새로고침하여 결과 표시
            st.rerun()
    else:
        st.button("백테스트 시작", key="start_backtest_button_disabled", use_container_width=True, disabled=True, type="primary")
        if backtest_error_msg:
            st.error(backtest_error_msg)


# === 메인 콘텐츠 영역 ===

# 메인 결과 표시 로직
if st.session_state.is_multi_mode and st.session_state.multi_backtest_results:
    # 다중 종목 모드 - 탭으로 표시
    st.info(f"다중 종목 백테스트 결과 ({len(st.session_state.selected_stocks)}개 종목)")

    # 성공한 종목들만 탭으로 표시
    successful_stocks = []
    for stock in st.session_state.selected_stocks:
        ticker = stock['ticker']
        if ticker in st.session_state.multi_backtest_results:
            result = st.session_state.multi_backtest_results[ticker]
            if 'error' not in result:
                successful_stocks.append(stock)

    if successful_stocks:
        # 탭 생성
        tab_names = [f"{stock['name']} ({stock['ticker']})" for stock in successful_stocks]
        tabs = st.tabs(tab_names)

        for i, (tab, stock) in enumerate(zip(tabs, successful_stocks)):
            with tab:
                ticker = stock['ticker']
                result = st.session_state.multi_backtest_results[ticker]
                stock_data = result.get('stock_data')
                backtest_results = result.get('backtest_results')

                # 각 탭에서 개별 결과 표시
                st.subheader(f"{stock['name']} ({ticker}) 백테스트 결과")

                # 캔들차트
                st.markdown("#### 캔들차트 및 매매 시점")
                if stock_data is not None and backtest_results:
                    display_candlestick_chart(
                        stock_data,
                        ticker,
                        backtest_results.get("trades", [])
                    )
                else:
                    st.error("차트 데이터가 없습니다.")

                st.markdown("<br>", unsafe_allow_html=True)

                # 성과 지표
                st.markdown("#### 성과 지표")
                if backtest_results and "metrics" in backtest_results:
                    display_performance_metrics(backtest_results["metrics"])
                else:
                    st.warning("성과 지표가 없습니다.")

                st.markdown("<br>", unsafe_allow_html=True)

                # 거래 내역
                st.markdown("#### 거래 내역")
                if backtest_results and "trades" in backtest_results:
                    display_trade_history(backtest_results["trades"])
                else:
                    st.info("거래 내역이 없습니다.")

    # 오류가 발생한 종목들 표시
    error_stocks = []
    for stock in st.session_state.selected_stocks:
        ticker = stock['ticker']
        if ticker in st.session_state.multi_backtest_results:
            result = st.session_state.multi_backtest_results[ticker]
            if 'error' in result:
                error_stocks.append((stock, result['error']))

    if error_stocks:
        st.markdown("---")
        st.error("⚠️ 다음 종목들에서 오류가 발생했습니다:")
        for stock, error in error_stocks:
            st.markdown(f"- **{stock['name']} ({stock['ticker']})**: {error}")

elif st.session_state.stock_data is not None and st.session_state.backtest_results:
    # 단일 종목 모드 또는 기본 결과 표시
    st.markdown("### 백테스트 결과")
    
    # 캔들차트 및 매매 시점
    st.markdown("#### 캔들차트 및 매매 시점")
    trades = st.session_state.backtest_results.get('trades', [])
    ticker = st.session_state.ticker or "UNKNOWN"
    display_candlestick_chart(st.session_state.stock_data, ticker, trades)
    
    # 성과 지표
    st.markdown("#### 성과 지표")
    metrics = st.session_state.backtest_results.get('metrics', {})
    display_performance_metrics(metrics)

    st.markdown("<br>", unsafe_allow_html=True)    
    # 거래 내역
    st.markdown("#### 거래 내역")
    display_trade_history(trades)

else:
    # 기본 안내 메시지
    if st.session_state.is_multi_mode and st.session_state.selected_stocks:
        st.info(f"다중 종목 모드: {len(st.session_state.selected_stocks)}개 종목이 선택되었습니다.")

        # 선택된 종목 목록 표시
        cols = st.columns(min(len(st.session_state.selected_stocks), 4))
        for i, stock in enumerate(st.session_state.selected_stocks):
            with cols[i % 4]:
                st.metric(
                    label=stock['name'],
                    value=stock['ticker'],
                    help=f"선택된 종목: {stock['name']} ({stock['ticker']})"
                )

        st.markdown("---")
        st.info("⬅️ 왼쪽 사이드바에서 '백테스트 시작' 버튼을 클릭하여 다중 종목 백테스트를 실행하세요.")
    else:
        # 기본 안내 메시지
        st.markdown("""
        ### 백테스트 결과

        #### 캔들차트 및 매매 시점
        백테스트를 시작하면 여기에 차트가 표시됩니다.

        #### 성과 지표
        상세 지표를 표시하려면 백테스트를 시작하세요.

                    
        #### 거래 내역
        백테스트를 시작하면 여기에 거래 내역이 표시됩니다.
        """)
        st.info("⬅️ 왼쪽 사이드바에서 종목을 선택하고 설정을 조정한 후 백테스트를 시작하세요.")

# Footer
st.markdown("---")
st.caption("본 사이트는 교육 및 데모 목적으로 제작되었습니다. 실제 투자 결정에 사용하지 마십시오.")

