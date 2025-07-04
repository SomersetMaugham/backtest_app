import pymysql
from dotenv import load_dotenv
import os

load_dotenv()

# Naver News API ID
maria_db_pw = os.getenv("MARIA_DB_PASSWORD")
maria_db_name = os.getenv("MARIA_DB_NAME")

def get_company_code(company_name):
    # 데이터베이스 연결 정보 (환경에 맞게 수정)
    db_config = {
        'host': '192.168.219.100',
        'user': 'root',
        'password': maria_db_pw,  # ⚠️ 보안에 주의
        'database': maria_db_name,
        'port': 3307,
        'charset': 'utf8mb4'
    }

    try:
        # DB 연결
        conn = pymysql.connect(**db_config)
        cursor = conn.cursor()

        # 회사명으로 코드 조회
        query = "SELECT code FROM company_info WHERE company = %s"
        cursor.execute(query, (company_name,))
        result = cursor.fetchone()

        if result:
            return result[0]
        else:
            return None

    except Exception as e:
        print(f"Error: {e}")
        return None

    finally:
        if conn:
            conn.close()

# 사용 예시
if __name__ == "__main__":
    company = input("회사명을 입력하세요: ")
    code = get_company_code(company)
    if code:
        print(f"{company}의 종목코드는: {code}")
    else:
        print("해당 회사명을 찾을 수 없습니다.")
