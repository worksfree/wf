import time
import os

try:
    import openpyxl
    from pyxlsb import open_workbook as open_xlsb
except ImportError as e:
    raise ImportError(f"Required package not found: {e}. Please run 'pip install openpyxl pyxlsb'")


class ExcelAutomation:
    """Excel 관련 자동화 작업을 처리하는 클래스"""

    def _measure_single_file(self, file_path: str) -> dict:
        """단일 파일의 로딩 시간과 크기를 측정합니다."""
        start_time = time.time()
        try:
            if file_path.lower().endswith(".xlsx"):
                openpyxl.load_workbook(file_path)
            elif file_path.lower().endswith(".xlsb"):
                with open_xlsb(file_path) as wb:
                    pass
            else:
                raise ValueError("지원하지 않는 파일 형식입니다.")

            elapsed = time.time() - start_time
            size = os.path.getsize(file_path)
            return {"success": True, "load_time": elapsed, "size": size}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def run_performance_check(self, file_path: str) -> dict:
        """
        성능 측정을 실행합니다. .xlsx 파일인 경우 .xlsb와 비교를 시도합니다.
        """
        if not file_path.lower().endswith(".xlsx"):
            # .xlsx가 아니면 단일 파일 측정 결과만 반환
            result = self._measure_single_file(file_path)
            return {"comparison_mode": False, "result": result}

        # .xlsx 파일인 경우, .xlsb 파일의 존재 여부 확인
        xlsb_path = os.path.splitext(file_path)[0] + ".xlsb"

        xlsx_result = self._measure_single_file(file_path)
        if not xlsx_result["success"]:
            # 원본 .xlsx 파일 로딩 실패 시, 즉시 오류 반환
            return {"comparison_mode": False, "result": xlsx_result}

        if not os.path.exists(xlsb_path):
            # .xlsb 파일이 없으면 .xlsx 단일 측정 결과만 반환
            return {"comparison_mode": False, "result": xlsx_result}

        # .xlsb 파일이 존재하면, 비교 측정 수행
        xlsb_result = self._measure_single_file(xlsb_path)
        if not xlsb_result["success"]:
            # .xlsb 로딩 실패 시, .xlsx 결과만이라도 반환
            return {
                "comparison_mode": False,
                "result": xlsx_result,
                "warning": f".xlsb 파일({os.path.basename(xlsb_path)}) 로딩 실패",
            }

        # 두 파일 모두 성공적으로 측정된 경우, 비교 데이터 계산
        try:
            speed_multiplier = (
                xlsx_result["load_time"] / xlsb_result["load_time"]
                if xlsb_result["load_time"] > 0
                else float("inf")
            )
            size_reduction_percent = (
                (1 - xlsb_result["size"] / xlsx_result["size"]) * 100
                if xlsx_result["size"] > 0
                else 0
            )
        except ZeroDivisionError:
            speed_multiplier = float("inf")
            size_reduction_percent = 0

        return {
            "comparison_mode": True,
            "xlsx": xlsx_result,
            "xlsb": xlsb_result,
            "metrics": {
                "speed_multiplier": speed_multiplier,
                "size_reduction_percent": size_reduction_percent,
            },
        }
