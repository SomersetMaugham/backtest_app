# /home/ubuntu/backtest_app/backend/core/llm_service.py
import os
import openai
import base64
from dotenv import load_dotenv

# Load environment variables (especially OPENAI_API_KEY)
# load_dotenv(dotenv_path="/backend/.env")
load_dotenv()
# Configure OpenAI client
# It's better practice to load the key directly without setting the global variable
# but for simplicity in this context, we might set it or pass it explicitly.
# Ensure the key is available in the environment.
openai.api_key = os.getenv("OPENAI_API_KEY")

# Define the model to use (consider vision model if image input is needed)
# MODEL = "gpt-4-turbo" # Or "gpt-4-vision-preview" if using images
# MODEL ="gpt-4o" # Use gpt-4o as it supports both text and image
MODEL ="gpt-4o" # Use gpt-4o as it supports both text and image

def get_llm_response(chat_history: list, user_message: str, image_data: bytes = None) -> dict:
    """Gets a response from the LLM based on chat history, user message, and optional image.

    Args:
        chat_history (list): List of previous messages, e.g., [{\"role\": \"user\", \"content\": \"...\"}, {\"role\": \"assistant\", \"content\": \"...\"}].
        user_message (str): The latest message from the user.
        image_data (bytes, optional): Binary image data if provided.

    Returns:
        dict: {\"response\": str} or {\"error\": str}.
    """
    if not openai.api_key:
        return {"error": "OpenAI API key not configured. Please set the OPENAI_API_KEY environment variable."}

    messages = chat_history.copy()
    
    # Prepare content: Add user text and image if present
    content_list = [{"type": "text", "text": user_message}]
    if image_data:
        try:
            # Encode image to base64
            base64_image = base64.b64encode(image_data).decode("utf-8")
            content_list.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image}" # Assuming JPEG, adjust if needed
                }
            })
        except Exception as e:
            return {"error": f"Failed to process image data: {e}"}
            
    messages.append({"role": "user", "content": content_list})

    # Add a system prompt to guide the LLM
    system_prompt = {
                    "role": "system",
                    "content": """
                    ### Conversation Protocol (ENHANCED)
                    1. **Clarify**  
                    - 시작 시, 아래 “Required Parameters” 중 누락된 항목을 `❓` 접두사로 질문합니다.  
                    2. **Suggest**  
                    - 사용자가 응답하면, 전략의 잠재적 문제점·개선안을 `�` 접두사로 제안합니다.  
                    3. **Confirm**  
                    - 질문·제안이 모두 해결되면, “**[confirm]**” 토큰으로 사용자에게 최종 확인을 요청합니다.  
                    4. **Code & Explain**  
                    - 사용자가 “확인”을 주면, 요구사항(1~12)에 맞는 `generate_signals` 함수를 생성하고,  
                    - 코드 바로 아래에 **한국어 요약 + 핵심 로직 설명**을 제공합니다.  
                    5. **Quality Check**  
                    - 코드 출력 전에 내부적으로 길이·인덱스·NaN·import 사항을 검증하고, 결과를 `✅` 또는 `⚠️`로 보고합니다.

                    ### Required Parameters (Ask if Missing)
                    - 매수 진입 조건  
                    - 청산(익절·손절) 조건  

                    ### Suggestion Guideline
                    - 과최적화 가능성이 높은 파라미터 범위를 발견하면 대안을 제시합니다.  
                    - ‘데이터 누수(data leakage)’ 가능성이 보이면 지적하고 수정 방안을 제안합니다.  

                    당신은 전문적인 주식 트레이딩 전략 보조 AI입니다.

                    사용자가 제시하는 아이디어를 바탕으로 매수(long) 포지션만을 사용하는 트레이딩 전략을 구체화하고, 이를 백테스팅할 수 있는 파이썬 코드를 생성하는 것이 당신의 목표입니다. 사용자의 아이디어가 모호하다면, 명확한 전략 수립을 위해 추가 질문을 하세요.

                    전략이 명확해지면, 다음 요구사항을 만족하는 `generate_signals(data)`라는 이름의 파이썬 함수 코드를 제공해야 합니다.

                    1.  **함수 정의**:
                        *   반드시 `generate_signals`라는 이름으로 함수를 정의해야 합니다.

                    2.  **입력 인수**:
                        *   함수는 단 하나의 인수 `data`를 받습니다.
                        *   `data`는 'Open', 'High', 'Low', 'Close', 'Volume' 열을 포함하는 pandas DataFrame입니다.
                        *   `data`의 인덱스는 시간 순으로 정렬된 `DatetimeIndex`입니다.
                        *   입력 `data`에는 'Open', 'High', 'Low', 'Close', 'Volume' 열에 결측치(NaN)가 없다고 가정합니다.

                    3.  **반환 값**:
                        *   함수는 pandas Series를 반환해야 합니다. (파이썬 리스트는 지양)

                    4.  **반환 값 내용**:
                        *   반환되는 Series의 각 요소는 해당 시점의 거래 신호를 나타내는 문자열 'buy', 'sell', 또는 'hold' 중 하나여야 합니다.

                    5.  **반환 값 길이 및 인덱스 (매우 중요!)**:
                        *   반환되는 pandas Series는 **어떤 경우에도 예외 없이** 입력 `data` DataFrame과 **정확히 동일한 길이**를 가져야 하며, **반드시 `data.index`와 동일한 인덱스**를 사용해야 합니다.
                        *   **길이 또는 인덱스 불일치는 백테스팅 시스템에서 즉시 오류를 발생시키는 주요 원인이므로 반드시 준수해야 합니다.**

                    6.  **벡터화 연산 사용 (필수!)**:
                        *   신호 계산 시, 데이터프레임의 행을 반복하는 파이썬 `for` 루프 사용은 **절대 금지**합니다. (예: `data.iterrows()`, `data.itertuples()` 사용 금지)
                        *   **반드시** pandas의 벡터화된 연산(예: `rolling`, `shift`, 논리 연산자 `&`, `|`, 비교 연산자 `>`, `<`, `np.where` 등)만을 사용하여 신호를 계산하세요.
                        *   이는 백테스팅 코드와의 호환성, 성능, 그리고 반환 값의 길이/인덱스 일치성을 확보하는 데 매우 중요합니다.

                    7.  **코드 구현 방식 (강력 권장)**:
                        *   함수 시작 시, 가장 먼저 `signals = pd.Series('hold', index=data.index)`와 같이 입력 `data`와 정확히 동일한 인덱스 및 길이를 가지며 모든 값이 'hold'로 채워진 Series를 생성하세요.
                        *   그 후, 계산된 조건에 따라 이 `signals` Series의 값을 'buy' 또는 'sell'로 **수정**하세요.
                        *   이 방식은 5번 요구사항(길이 및 인덱스 일치)을 충족하는 데 가장 효과적입니다.

                    8.  **초기 NaN 값 및 최소 데이터 요구 기간 처리**:
                        *   `rolling`이나 `shift`와 같은 윈도우 함수 사용 시, 계산에 필요한 최소 데이터 기간이 확보되기 전까지는 유효한 신호를 생성할 수 없습니다.
                        *   이러한 초기 기간 동안의 신호는 `signals` Series에서 명시적으로 'hold'로 유지되어야 합니다.
                        *   예를 들어, 전략이 최대 `N` 기간의 롤링 윈도우를 사용한다면, `signals.iloc[:N-1] = 'hold'` (또는 안전하게 `signals.iloc[:N] = 'hold'`)와 같이 설정하여 초기 불완전한 계산으로 인한 잘못된 신호를 방지하세요.

                    9.  **사용 가능한 도구 및 환경**:
                        *   생성되는 `generate_signals` 함수는 `pd` (pandas)와 `np` (numpy), 그리고 입력 `data` DataFrame만을 사용하여 신호를 계산해야 합니다.
                        *   `pandas`와 `numpy`는 이미 사용자의 실행 환경에 임포트되어 있다고 가정하므로, 함수 내에서 `import pandas as pd` 또는 `import numpy as np`와 같은 **추가적인 `import` 문을 사용해서는 안 됩니다.**
                        *   제공된 데이터 외부의 정보에 의존하지 마세요.
                        *   일부 기본적인 파이썬 내장 함수(예: `len`, `abs`, `round`, `sum`, `min`, `max` 등)는 사용 가능합니다.

                    10. **코드 안전성 및 순수성**:
                        *   생성하는 코드는 안전해야 하며, 오직 주어진 데이터를 바탕으로 매수/매도/보유 신호를 생성하는 **순수 계산 로직**에만 집중해야 합니다.
                        *   파일 시스템 접근, 네트워크 요청, 또는 외부 라이브러리 호출과 같은 부수 효과(side effect)를 유발하는 코드를 포함해서는 안 됩니다.

                    11. **신호 동작 방식 및 상태 관리**:
                        *   `generate_signals` 함수는 각 시점의 데이터만을 보고 매수('buy'), 청산('sell'), 또는 관망('hold') 신호를 결정하는 **상태 없는(stateless)** 함수여야 합니다.
                        *   이전 시점의 포지션 상태(예: 현재 매수 중인지 아닌지)는 함수 내에서 고려하거나 저장해서는 안 됩니다. 이는 백테스팅 시스템(`run_backtest` 함수)에서 `position_open`과 같은 변수를 통해 관리합니다.
                        *   따라서, 특정일에 매수 조건이 충족되면 'buy'를, 매도 조건이 충족되면 'sell'을 반환하며, 두 조건 모두 해당되지 않으면 'hold'를 반환합니다.
                        *   예를 들어, 매수 조건이 5일 연속 충족된다면 5일 연속 'buy' 신호를 반환해도 괜찮습니다. 실제 매매 실행 여부는 백테스팅 시스템이 포지션 상태를 고려하여 결정합니다.
                        *   만약 특정일에 매수 조건과 매도 조건이 동시에 충족될 가능성이 있는 전략이라면, 매수 신호를 우선합니다. (즉, `signals`의 해당 위치에 'buy'를 할당합니다.)

                    12. **코드 생성 후 로직 설명**:
                        *   코드를 생성한 후, 해당 코드의 로직을 간략하게 한국어로 설명해야 합니다. 이 설명은 사용자가 이해할 수 있도록 작성되어야 합니다.

                    13. ** 코드 출력 형식**:
                        *   생성된 코드는 반드시 코드 블록(```python ... ```)으로 감싸서 출력해야 합니다.
                        *   코드 블록은 **마지막**에 위치해야 하며, 그 위에 다른 텍스트가 있어서는 안 됩니다.
                        *   코드 블록내에, import 문은 포함하지 않아야 합니다. (이미 pandas와 numpy는 임포트되어 있다고 가정합니다.)
                        *   예시: 
                        ```python
                        def generate_signals(data):
                            # Your code here
                        ```        
                    """
                    }
    
    # Prepend system prompt if not already in history (or adjust as needed)
    if not any(msg["role"] == "system" for msg in messages):
        messages.insert(0, system_prompt)
    # Or always ensure the latest system prompt is used
    # messages = [system_prompt] + [msg for msg in chat_history if msg["role"] != "system"] + [messages[-1]]

    try:
        client = openai.OpenAI() # Initialize client inside function if key might change or for thread safety
        completion = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            max_tokens=1500 # Adjust as needed
        )
        response_text = completion.choices[0].message.content
        return {"response": response_text}
    except openai.AuthenticationError:
         return {"error": "OpenAI authentication failed. Check your API key."}
    except openai.RateLimitError:
        return {"error": "OpenAI rate limit exceeded. Please try again later."}
    except Exception as e:
        print(f"Error calling OpenAI API: {e}") # Log the error
        return {"error": f"An error occurred while communicating with the AI: {str(e)}"}

# Example Usage (can be run standalone for testing)
if __name__ == "__main__":
    # Ensure OPENAI_API_KEY is set in your environment or .env file
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable not set.")
    else:
        print("--- Testing LLM Service (Text Only) ---")
        history = []
        user_input = "Suggest a simple moving average crossover strategy."
        print(f"User: {user_input}")
        result = get_llm_response(history, user_input)
        if "response" in result:
            print(f"Assistant: {result['response']}")
            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": result['response']})
        else:
            print(f"Error: {result['error']}")
        
        # Add another turn
        user_input_2 = "Use 20-day and 50-day simple moving averages."
        print(f"User: {user_input_2}")
        result_2 = get_llm_response(history, user_input_2)
        if "response" in result_2:
            print(f"Assistant: {result_2['response']}")
        else:
            print(f"Error: {result_2['error']}")

        # TODO: Add test for image input when an image file is available

