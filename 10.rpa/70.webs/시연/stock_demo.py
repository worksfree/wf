import pandas as pd
import requests
import os
from bs4 import BeautifulSoup
import io


def get_current_price(stock_code: str):
    """네이버 증권에서 특정 종목의 현재가만 가져옵니다."""
    url = f"https://finance.naver.com/item/main.naver?code={stock_code}"
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        price_area = soup.select_one("div.today p.no_today")

        if not price_area:
            return {
                "success": False,
                "error": "가격 정보 영역(div.today p.no_today)을 찾지 못했습니다.",
            }

        price_span = price_area.find("span", class_="blind")

        if not price_span:
            return {"success": False, "error": "영역 내에서 가격 값(span.blind)을 찾지 못했습니다."}

        return {"success": True, "price": price_span.text}

    except Exception as e:
        return {"success": False, "error": str(e)}


def get_daily_sise(stock_code: str):
    """네이버 증권에서 일별 시세 테이블을 가져옵니다."""
    url = f"https://finance.naver.com/item/sise_day.naver?code={stock_code}"
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        # pandas의 read_html을 사용하여 페이지의 모든 테이블을 읽어옵니다.
        # read_html은 HTML 문자열을 직접 처리할 수 있습니다.
        tables = pd.read_html(io.StringIO(response.text))

        # 일별 시세 테이블은 보통 첫 번째 테이블입니다.
        df = tables[0]

        # 데이터 클리닝: 비어있는 행(NaN) 제거
        df = df.dropna()

        return {"success": True, "data": df.head(10)}

    except Exception as e:
        return {"success": False, "error": str(e)}


def read_stocks_from_excel(file_path: str):
    """엑셀 파일에서 조회할 종목 리스트를 읽어옵니다."""
    try:
        df = pd.read_excel(file_path)
        df["종목코드"] = df["종목코드"].astype(str).str.zfill(6)
        return df.to_dict("records")
    except FileNotFoundError:
        print(f"오류: 엑셀 파일('{file_path}')을 찾을 수 없습니다.")
        return []
    except Exception as e:
        print(f"엑셀 파일을 읽는 중 오류가 발생했습니다: {e}")
        return []


if __name__ == "__main__":
    excel_file_path = os.path.join(os.path.dirname(__file__), "stock_list.xlsx")
    stocks_to_check = read_stocks_from_excel(excel_file_path)

    if stocks_to_check:
        print("--- 주식 현재가 및 일별 시세 조회 --- (출처: 네이버 증권)")
        for stock in stocks_to_check:
            stock_name = stock["종목명"]
            stock_code = stock["종목코드"]

            print(f"\n조회 중: {stock_name}({stock_code})...")

            # 1. 현재가 조회
            price_result = get_current_price(stock_code)
            if price_result["success"]:
                print(f"  현재가: {price_result['price']}원")
            else:
                print(f"  현재가 조회 실패. 오류: {price_result['error']}")

            # 2. 일별 시세 조회
            sise_result = get_daily_sise(stock_code)
            if sise_result["success"]:
                print("  --- 일별 시세 (최근 10건) ---")
                # DataFrame을 보기 좋게 출력하기 위해 to_string() 사용, 인덱스 제외
                print(sise_result["data"].to_string(index=False))
            else:
                print(f"  일별 시세 조회 실패. 오류: {sise_result['error']}")
