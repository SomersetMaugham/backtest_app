import pandas as pd
import FinanceDataReader as fdr # FinanceDataReader 추가
import pymysql, calendar, time, json, random
import requests
from datetime import datetime, timedelta # timedelta 추가
from threading import Timer

class DBUpdater:
    def __init__(self):
        """생성자: MariaDB 연결 및 종목코드 딕셔너리 생성"""
        self.conn = pymysql.connect(host='localhost', user='stockuser',
            password='1111', db='INVESTAR', charset='utf8', port=3306)

        with self.conn.cursor() as curs:
            sql = """
            CREATE TABLE IF NOT EXISTS company_info (
                code VARCHAR(20),
                company VARCHAR(40),
                last_update DATE,
                PRIMARY KEY (code))
            """
            curs.execute(sql)
            sql = """
            CREATE TABLE IF NOT EXISTS daily_price (
                code VARCHAR(20),
                date DATE,
                open BIGINT(20),
                high BIGINT(20),
                low BIGINT(20),
                close BIGINT(20),
                diff BIGINT(20),
                volume BIGINT(20),
                PRIMARY KEY (code, date))
            """
            curs.execute(sql)
        self.conn.commit()
        self.codes = dict()

    def __del__(self):
        """소멸자: MariaDB 연결 해제"""
        self.conn.close()

    def read_krx_code(self):
        """KRX로부터 상장기업 목록 파일을 읽어와서 데이터프레임으로 반환"""
        url = 'http://kind.krx.co.kr/corpgeneral/corpList.do?method='\
            'download&searchType=13'
        krx = pd.read_html(url, header=0, encoding='cp949')[0]
        krx = krx[['종목코드', '회사명']]
        krx = krx.rename(columns={'종목코드': 'code', '회사명': 'company'})
        krx.code = krx.code.map('{:06d}'.format)
        return krx

    def update_comp_info(self):
        """종목코드를 company_info 테이블에 업데이트 한 후 딕셔너리에 저장"""
        sql = "SELECT * FROM company_info"
        df = pd.read_sql(sql, self.conn)
        for idx in range(len(df)):
            self.codes[df['code'].values[idx]] = df['company'].values[idx]

        with self.conn.cursor() as curs:
            sql = "SELECT max(last_update) FROM company_info"
            curs.execute(sql)
            rs = curs.fetchone()
            today = datetime.today().strftime('%Y-%m-%d')
            if rs[0] == None or rs[0].strftime('%Y-%m-%d') < today:
                krx = self.read_krx_code()
                for idx in range(len(krx)):
                    code = krx.code.values[idx]
                    company = krx.company.values[idx]
                    sql = f"REPLACE INTO company_info (code, company, last"\
                        f"_update) VALUES ('{code}', '{company}', '{today}')"
                    curs.execute(sql)
                    self.codes[code] = company
                    tmnow = datetime.now().strftime('%Y-%m-%d %H:%M')
                    print(f"[{tmnow}] #{idx+1:04d} REPLACE INTO company_info "\
                        f"VALUES ({code}, {company}, {today})")
                self.conn.commit()
                print('')

    def fetch_daily_price_fdr(self, code, start_date, end_date):
        """FinanceDataReader를 사용하여 주식 시세를 읽어서 데이터프레임으로 반환"""
        try:
            # FinanceDataReader는 'YYYY-MM-DD' 형식의 날짜를 받음
            df = fdr.DataReader(code, start=start_date, end=end_date)

            if df.empty:
                # print(f"FinanceDataReader: No data found for {code} from {start_date} to {end_date}")
                return None

            # 컬럼 이름 변경
            df = df.rename(columns={
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume',
                'Change': 'change_percent' # Change는 등락률이므로 diff 계산에 사용
            })

            # 'diff' (전일비) 계산: 현재 종가 - 전일 종가
            # shift(1)은 이전 행의 값을 가져옴
            df['diff'] = df['close'] - df['close'].shift(1)

            # 첫 행의 diff는 NaN이 되므로 제거 (또는 필요에 따라 처리)
            df = df.dropna(subset=['diff'])

            # Index (날짜)를 컬럼으로 변환하고 'date'로 이름 변경
            df = df.reset_index()
            df = df.rename(columns={'Date': 'date'})

            # 날짜 형식을 'YYYY-MM-DD' 문자열로 변환 (DB DATE 형식에 맞춤)
            df['date'] = df['date'].dt.strftime('%Y-%m-%d')

            # 필요한 컬럼만 선택하고 순서 맞추기 및 데이터 타입 변환
            # diff 컬럼은 float일 수 있으므로 int로 변환 시 주의 필요 (소수점 버림)
            df = df[['date', 'open', 'high', 'low', 'close', 'diff', 'volume']].astype({
                'date': str,
                'open': int,
                'high': int,
                'low': int,
                'close': int,
                'diff': int, # float -> int 변환 시 소수점 버림
                'volume': int
            })


            return df

        except Exception as e:
            print(f'\nException occurred while fetching data for {code} using FinanceDataReader: {str(e)}')
            return None
        return df


    def replace_into_db(self, df, num, code, company):
        """FinanceDataReader에서 읽어온 주식 시세를 DB에 REPLACE"""
        with self.conn.cursor() as curs:
            for r in df.itertuples():
                sql = f"REPLACE INTO daily_price VALUES ('{code}', "\
                    f"'{r.date}', {r.open}, {r.high}, {r.low}, {r.close}, "\
                    f"{r.diff}, {r.volume})"
                curs.execute(sql)
            self.conn.commit()
            print('[{}] #{:04d} {} ({}) : {} rows > REPLACE INTO daily_'\
                'price [OK]'.format(datetime.now().strftime('%Y-%m-%d'\
                ' %H:%M'), num+1, company, code, len(df)))
            # Optional: Add a small delay after inserting data for a stock
            # time.sleep(random.uniform(0.1, 0.5))


    def update_daily_price(self): # pages_to_fetch parameter is no longer needed
        """KRX 상장법인의 주식 시세를 FinanceDataReader로부터 읽어서 DB에 업데이트"""
        # Ensure codes dictionary is populated
        if not self.codes:
             self.update_comp_info() # Make sure company info is updated and codes dict is filled

        total_codes = len(self.codes)
        print(f"Updating daily price for {total_codes} companies...")

        for idx, code in enumerate(self.codes):
            company = self.codes[code]
            tmnow = datetime.now().strftime('%Y-%m-%d %H:%M')
            print(f"[{tmnow}] #{idx+1:04d}/{total_codes:04d} Updating {company} ({code})...", end="\r")

            # DB에서 해당 종목의 마지막 날짜 조회
            last_date_in_db = None
            with self.conn.cursor() as curs:
                sql = f"SELECT MAX(date) FROM daily_price WHERE code = '{code}'"
                curs.execute(sql)
                result = curs.fetchone()
                if result and result[0]:
                    last_date_in_db = result[0] # result[0] is a datetime.date object

            # 데이터 가져올 시작 날짜 설정
            # 마지막 날짜의 다음 날부터 가져옴. DB에 데이터가 없으면 아주 오래전부터 가져옴.
            # FinanceDataReader는 시작 날짜를 포함하므로, DB 마지막 날짜의 다음 날로 설정
            start_date_str = (last_date_in_db + timedelta(days=1)).strftime('%Y-%m-%d') if last_date_in_db else '2000-01-01'

            # 데이터 가져올 종료 날짜 설정 (오늘)
            end_date_str = datetime.today().strftime('%Y-%m-%d')

            # FinanceDataReader로 데이터 가져오기
            # Note: FinanceDataReader might return data up to the *last trading day* on or before end_date_str
            df = self.fetch_daily_price_fdr(code, start_date_str, end_date_str)
            if df is None or df.empty: # 데이터가 없거나 비어있으면 건너뛰기
                continue
            self.replace_into_db(df, idx, code, self.codes[code])


    def execute_daily(self):
        """실행 즉시 및 매일 오후 여덟시에 daily_price 테이블 업데이트"""
        self.update_comp_info()

        self.update_daily_price() # pages_to_fetch 인자 제거

        tmnow = datetime.now()
        lastday = calendar.monthrange(tmnow.year, tmnow.month)[1]
        if tmnow.month == 12 and tmnow.day == lastday:
            tmnext = tmnow.replace(year=tmnow.year+1, month=1, day=1,
                hour=17, minute=0, second=0)
        elif tmnow.day == lastday:
            tmnext = tmnow.replace(month=tmnow.month+1, day=1, hour=20,
                minute=0, second=0)
        else:
            tmnext = tmnow.replace(day=tmnow.day+1, hour=20, minute=0,
                second=0)
        tmdiff = tmnext - tmnow # timedelta 객체
        secs = tmdiff.total_seconds() # total_seconds()를 사용하여 정확한 초 계산

        # 만약 이미 오후 5시를 지났다면 다음 날 오후 5시로 설정
        if secs < 0:
             tmnext = tmnext + timedelta(days=1)
             secs = (tmnext - tmnow).total_seconds()

        t = Timer(secs, self.execute_daily)
        print("Waiting for next update ({}) ... ".format(tmnext.strftime
            ('%Y-%m-%d %H:%M')))
        t.start()

if __name__ == '__main__':
    dbu = DBUpdater()
    dbu.execute_daily() # 주석 해제 시 매일 업데이트 시작
