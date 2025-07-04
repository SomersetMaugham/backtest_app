# 주식 트레이딩 백테스트 및 LLM 기반 전략 생성 사이트

## 프로젝트 개요

이 프로젝트는 사용자가 주식 티커와 기간을 입력하여 과거 데이터를 시각화하고, Python 코드로 작성된 트레이딩 전략을 백테스트하며, LLM(대규모 언어 모델)과 대화하여 트레이딩 전략에 대한 아이디어를 얻거나 코드를 생성할 수 있는 웹 애플리케이션입니다.

주요 기능:
*   **데이터 시각화**: `yfinance`를 사용하여 특정 주식의 과거 데이터를 가져와 Plotly 캔들차트로 표시합니다.
*   **백테스팅**: 사용자가 입력하거나 저장된 Python 코드로 작성된 트레이딩 전략을 과거 데이터에 적용하여 성과(총 수익률, 최대 낙폭 등)를 계산하고 매매 시점을 차트에 표시합니다.
*   **LLM 챗봇**: OpenAI API를 사용하여 사용자와 트레이딩 전략에 대해 대화하고, 전략 아이디어를 구체화하거나 Python 코드를 생성하도록 요청할 수 있습니다. 이미지(차트 등)를 첨부하여 질문할 수도 있습니다.
*   **전략 관리**: 생성되거나 작성된 트레이딩 전략 코드를 서버에 저장하고, 필요할 때 불러오거나 삭제할 수 있습니다.

## 기술 스택

*   **백엔드**: Flask (Python)
    *   API 엔드포인트 제공 (데이터 수집, 백테스트 실행, LLM 연동, 전략 관리)
    *   `yfinance`: 주식 데이터 수집
    *   `pandas`: 데이터 처리
    *   `openai`: LLM 연동
    *   `python-dotenv`: 환경 변수 관리
*   **프론트엔드**: Streamlit (Python)
    *   사용자 인터페이스 (입력 필드, 버튼, 차트 표시, 챗봇 인터페이스)
    *   `requests`: 백엔드 API 호출
    *   `plotly`: 데이터 시각화
*   **데이터 저장**: 파일 시스템 (전략 코드 저장)

## 프로젝트 구조

```
backtest_app/
├── backend/
│   ├── api/                 # Flask Blueprints for API endpoints
│   │   ├── __init__.py
│   │   ├── backtest_runner.py # Backtest execution API
│   │   ├── llm_chat.py        # LLM interaction API
│   │   ├── stock_data.py      # Stock data fetching API
│   │   └── strategy_manager.py # Strategy save/load/delete API
│   ├── core/                # Core logic modules
│   │   ├── __init__.py
│   │   ├── backtesting.py     # Backtesting engine logic
│   │   └── llm_service.py     # LLM API call logic
│   ├── data/
│   │   └── strategies/      # Directory to store saved strategy .py files
│   ├── venv/                # Python virtual environment for backend
│   ├── .env                 # Environment variables (OpenAI API Key, etc.) - **생성 필요**
│   ├── .env.example         # Example environment variables
│   ├── app.py               # Main Flask application file
│   ├── flask.log            # Log file for Flask server
│   ├── flask.pid            # Process ID file for Flask server
│   └── requirements.txt     # Backend Python dependencies
├── frontend/
│   ├── utils/               # Utility functions for frontend
│   │   ├── __init__.py
│   │   └── charting.py        # Plotly chart generation logic
│   ├── venv/                # Python virtual environment for frontend
│   ├── app.py               # Main Streamlit application file
│   └── requirements.txt     # Frontend Python dependencies
├── README.md              # This file
└── run.sh                 # Script to install dependencies and run both servers
```

## 설정 방법

1.  **저장소 복제**: (이 단계는 이미 완료되었다고 가정)
2.  **백엔드 설정**:
    *   `cd backend`
    *   Python 가상 환경 생성 및 활성화:
        ```bash
        python3 -m venv venv
        source venv/bin/activate
        ```
    *   의존성 설치:
        ```bash
        pip install -r requirements.txt
        ```
    *   `.env` 파일 생성: `.env.example` 파일을 복사하여 `.env` 파일을 만들고, 실제 OpenAI API 키를 `OPENAI_API_KEY` 변수에 입력합니다.
        ```bash
        cp .env.example .env
        # nano .env 또는 다른 편집기를 사용하여 API 키 입력
        ```
3.  **프론트엔드 설정**:
    *   `cd ../frontend`
    *   Python 가상 환경 생성 및 활성화:
        ```bash
        python3 -m venv venv
        source venv/bin/activate
        ```
    *   의존성 설치:
        ```bash
        pip install -r requirements.txt
        ```

## 실행 방법

프로젝트 루트 디렉토리(`backtest_app/`)에서 `run.sh` 스크립트를 실행하면 필요한 모든 설정(가상 환경 생성 및 의존성 설치 포함)을 수행하고 백엔드 및 프론트엔드 서버를 시작합니다.

```bash
chmod +x run.sh
./run.sh
```

스크립트 실행 후:
*   **백엔드 서버**: `http://0.0.0.0:5001` 에서 실행됩니다.
*   **프론트엔드 앱**: `http://<your-ip-address>:8501` 에서 접근 가능합니다. Streamlit 실행 시 터미널에 정확한 로컬 및 네트워크 URL이 표시됩니다.

**참고**: `run.sh` 스크립트는 백그라운드에서 서버를 실행하고 로그를 각 서버 디렉토리의 `.log` 파일에 저장합니다. 서버를 중지하려면 각 디렉토리의 `.pid` 파일에 저장된 프로세스 ID를 사용하여 `kill` 명령어를 실행해야 합니다.

## API 엔드포인트 (백엔드: http://localhost:5001)

*   **GET /api/stock_data**: 주식 데이터를 가져옵니다.
    *   쿼리 파라미터: `ticker`, `start_date`, `end_date`
    *   성공 시: 주식 데이터 (JSON)
*   **POST /api/run_backtest**: 백테스트를 실행합니다.
    *   요청 본문 (JSON): `ticker`, `start_date`, `end_date`, `initial_capital`, `strategy_code`, `stock_data` (JSON 형태의 주식 데이터)
    *   성공 시: 백테스트 결과 (trades, metrics) (JSON)
*   **POST /api/llm_chat**: LLM 챗봇과 상호작용합니다.
    *   요청 본문 (JSON): `history` (list), `message` (str), `image` (str, optional base64)
    *   성공 시: LLM 응답 (JSON)
*   **GET /api/strategies**: 저장된 전략 목록을 가져오거나 특정 전략 코드를 로드합니다.
    *   쿼리 파라미터: `name` (optional, 특정 전략 로드 시)
    *   성공 시: 전략 이름 목록 또는 특정 전략 코드 (JSON)
*   **POST /api/strategies**: 새로운 전략을 저장합니다.
    *   요청 본문 (JSON): `name` (str), `code` (str)
    *   성공 시: 성공 메시지 (JSON)
*   **DELETE /api/strategies/<name>**: 특정 전략을 삭제합니다.
    *   경로 파라미터: `name` (str)
    *   성공 시: 성공 메시지 (JSON)

## 향후 개선 사항

*   사용자 인증 추가
*   데이터베이스를 사용한 전략 및 백테스트 결과 저장
*   더 다양한 백테스트 지표 추가
*   프론트엔드 UI/UX 개선
*   오류 처리 강화

