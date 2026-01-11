# -*- coding: utf-8 -*-
"""
ConversionVerifier Automation Module
SOLIDWORKS DWG 변환 검증 핵심 로직을 담당하는 모듈
"""

import os
import sys
import time
import threading
from pathlib import Path
from datetime import datetime

# 현재 스크립트의 디렉토리를 Python 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# 기존 utils 경로 추가 (원본 코드와 호환성 유지)
utils_path = os.path.join(current_dir, "..", "..", "10.common")
utils_path = os.path.abspath(utils_path)
if os.path.exists(utils_path):
    sys.path.append(utils_path)

# utils 모듈들 import
try:
    import wf_log as wflog_module
    import wf_license as wflic
    import wf_email as wfm
    import wf_gen_code as wfgc
    import wf_hwinfo as wfhwinfo

    # 크레딧 매니저 (정책/사용 로그/동기화)
    from wf_credit_manager import CreditManager, WorksFreeManager

    # wf_log 사용을 위해 logger 설정
    logger, log_file_path = wflog_module.set_logger(
        filepath=os.path.join(current_dir, "logs"), level=20  # INFO level
    )

    class WFLogWrapper:
        def __init__(self, logger):
            self.logger = logger

        def info(self, msg):
            try:
                self.logger.info(msg)
            except Exception as e:
                print(f"[INFO] {msg}")

        def error(self, msg):
            try:
                self.logger.error(msg)
            except Exception as e:
                print(f"[ERROR] {msg}")

        def warning(self, msg):
            try:
                self.logger.warning(msg)
            except Exception as e:
                print(f"[WARNING] {msg}")

        def debug(self, msg):
            try:
                self.logger.debug(msg)
            except Exception as e:
                print(f"[DEBUG] {msg}")

    wflog = WFLogWrapper(logger)
    print("WorksFree 모듈 로드 성공")

except ImportError as e:
    print(f"WorksFree 모듈 import 실패: {e}")

    # 데모 모드용 대체 클래스들
    class MockWFLog:
        def __init__(self):
            pass

        def info(self, msg):
            print(f"[INFO] {msg}")

        def error(self, msg):
            print(f"[ERROR] {msg}")

        def warning(self, msg):
            print(f"[WARNING] {msg}")

        def debug(self, msg):
            print(f"[DEBUG] {msg}")

    class MockWFLicense:
        def __init__(self):
            try:
                self.email = "demo@worksfree.com"
                self.license_type = "데모 라이선스"
                print("MockWFLicense 초기화 완료")
            except Exception as e:
                print(f"MockWFLicense 초기화 오류: {e}")

        def is_valid(self):
            try:
                return True
            except Exception as e:
                print(f"is_valid 오류: {e}")
                return False

        def get_user_email(self):
            try:
                return "demo@worksfree.com"
            except Exception as e:
                print(f"get_user_email 오류: {e}")
                return "demo@worksfree.com"

        def get_license_type(self):
            try:
                return "데모 라이선스"
            except Exception as e:
                print(f"get_license_type 오류: {e}")
                return "데모 라이선스"

    class MockWFHwInfo:
        def __init__(self):
            pass

        def get_mac_address(self):
            try:
                import uuid

                mac = ":".join(
                    [
                        "{:02x}".format((uuid.getnode() >> elements) & 0xFF)
                        for elements in range(0, 2 * 6, 2)
                    ][::-1]
                )
                return mac.upper()
            except:
                return "demo:mac:address:12:34:56"

    class MockWFEmail:
        def __init__(self):
            pass

        def send_email(self, *args, **kwargs):
            print("데모 모드: 이메일 전송 시뮬레이션")
            return True

    class MockWFGenCode:
        def __init__(self):
            pass

        def generate_code(self, length=8):
            return "DEMO1234"

    # Mock 객체들 사용
    wflog = MockWFLog()
    wflic = MockWFLicense()
    wfhwinfo = MockWFHwInfo()
    wfm = MockWFEmail()
    wfgc = MockWFGenCode()
    CreditManager = None
    WorksFreeManager = None


class ConversionAnalyzer:
    """SOLIDWORKS DWG 변환 분석 클래스"""

    def __init__(self, config=None, progress_callback=None):
        self.config = config
        self.progress_callback = progress_callback or self.default_progress_callback

        self.slddrw_files = []
        self.dwg_files = []
        self.comparison_data = []
        self.is_analyzing = False

        # MAC 주소 설정
        self.mac_address = self.get_mac_address()

    def get_mac_address(self):
        """MAC 주소 가져오기"""
        try:
            # wf_hwinfo가 실제 모듈이면 하드웨어 정보 사용, 아니면 MAC 주소 직접 생성
            if hasattr(wfhwinfo, "fingerprint"):
                return getattr(wfhwinfo, "fingerprint", "demo:fingerprint")
            elif hasattr(wfhwinfo, "get_network_interface_info"):
                return wfhwinfo.get_network_interface_info()
            else:
                return wfhwinfo.get_mac_address()
        except Exception as e:
            wflog.error(f"MAC 주소 가져오기 오류: {e}")
            # 직접 MAC 주소 생성
            try:
                import uuid

                mac = ":".join(
                    [
                        "{:02x}".format((uuid.getnode() >> elements) & 0xFF)
                        for elements in range(0, 2 * 6, 2)
                    ][::-1]
                )
                return mac.upper()
            except:
                return "demo:mac:address:12:34:56"

    def default_progress_callback(self, value, status):
        """기본 진행률 콜백 (콘솔 출력)"""
        print(f"진행률: {value}% - {status}")

    def analyze_folder(self, folder_path, use_credits=True):
        """폴더 분석"""
        if not os.path.exists(folder_path):
            raise ValueError("선택한 폴더가 존재하지 않습니다.")

        self.is_analyzing = True

        try:
            wflog.info(f"폴더 분석 시작: {folder_path}")

            # 1. SLDDRW 파일 검색
            self.progress_callback(10, "SLDDRW 파일을 검색하는 중...")
            self.slddrw_files = self.find_files(folder_path, "*.slddrw")
            wflog.info(f"SLDDRW 파일 {len(self.slddrw_files)}개 발견")

            if not self.slddrw_files:
                raise ValueError("SLDDRW 파일이 폴더에 없습니다.")

            # 2. DWG 파일 검색
            self.progress_callback(30, "DWG 파일을 검색하는 중...")
            self.dwg_files = self.find_files(folder_path, "*.dwg")
            wflog.info(f"DWG 파일 {len(self.dwg_files)}개 발견")

            # 3. 파일 비교 분석
            self.progress_callback(50, "파일을 비교하는 중...")
            self.comparison_data = self.create_comparison_data()
            wflog.info(f"비교 데이터 {len(self.comparison_data)}개 생성")

            # 4. 크레딧 처리 (정책 기반: 실행당 10, 공통 매니저 사용)
            if use_credits:
                try:
                    if CreditManager and WorksFreeManager:
                        wf_mgr = WorksFreeManager()
                        user_info = (
                            wf_mgr.get_user_info() if hasattr(wf_mgr, "get_user_info") else {}
                        )
                        user_email = user_info.get("user_email") or user_info.get("email") or ""
                        cm = CreditManager("conversion_verifier", user_email)

                        # 실행당 과금: 정책 비용 x 1 (파일 수는 사용 로그로만 기록)
                        per_cost = cm.get_per_item_cost()
                        total_slddrw = len(self.slddrw_files)
                        desc = f"변환 검증 실행 - 대상 {total_slddrw}개 (폴더: {os.path.basename(folder_path)})"
                        result = cm.deduct_credits(per_cost, desc, file_count=total_slddrw)
                        if not result.get("success"):
                            raise ValueError(result.get("message", "크레딧 차감 실패"))
                    else:
                        # 공통 매니저를 사용할 수 없는 환경에서는 차감 스킵 (개발/데모)
                        wflog.warning(
                            "크레딧 매니저를 사용할 수 없어 과금을 건너뜁니다 (개발/데모)."
                        )
                except Exception as ce:
                    wflog.error(f"크레딧 처리 오류: {ce}")
                    raise

            self.progress_callback(90, "결과를 업데이트하는 중...")

            # 5. 분석 완료
            self.progress_callback(100, "분석이 완료되었습니다!")

            result = self.get_analysis_result()
            wflog.info(f"분석 완료: {result['summary']}")

            # 6. 세션 재개 파일 목록 저장/정리
            try:
                folder_base = Path(folder_path)
                pending_path = folder_base / "wf_pending_list.txt"
                # 변환 검증은 실행당 과금이므로 크레딧 부족 시나리오가 없음
                # 완료 시 보류 목록 제거
                if pending_path.exists():
                    try:
                        pending_path.unlink()
                        wflog.info(f"보류 목록 삭제: {pending_path}")
                    except Exception as ue:
                        wflog.warning(f"보류 목록 삭제 실패(무시): {ue}")
            except Exception as pe:
                wflog.warning(f"보류 목록 처리 중 경고(무시): {pe}")

            return result

        except Exception as e:
            wflog.error(f"분석 중 오류: {e}")
            raise
        finally:
            self.is_analyzing = False

    def find_files(self, folder, pattern):
        """파일 검색 (중복/대소문자 확장자 안전 처리)

        Windows 파일 시스템은 대소문자 구분을 하지 않지만 Path.rglob 패턴은
        대소문자 민감하게 동작하므로 *.SLDDRW 같은 대문자 확장자는 *.slddrw
        패턴에서 누락될 수 있다. 또한 여러 패턴을 순차적으로 검색하면 동일
        파일을 두 번 수집할 가능성이 있으므로 (특히 로직 수정 과정에서)
        lower() 기반으로 고유 집합을 구성하여 중복을 제거한다.
        """
        files = {}
        folder_path = Path(folder)

        # 보류 목록 확인 (세션 재개용)
        pending_path = folder_path / "wf_pending_list.txt"
        if pending_path.exists() and pattern == "*.slddrw":
            try:
                pending_names = set()
                with open(pending_path, "r", encoding="utf-8") as pf:
                    for line in pf:
                        name = line.strip()
                        if name:
                            pending_names.add(name.lower())
                if pending_names:
                    wflog.info(f"보류 목록 발견: {len(pending_names)}개 파일")
                    # 보류 파일만 스캔
                    for file_path in folder_path.rglob(pattern):
                        if file_path.is_file() and file_path.name.lower() in pending_names:
                            key = str(file_path.resolve()).lower()
                            if key not in files:
                                stat = file_path.stat()
                                files[key] = {
                                    "name": file_path.name,
                                    "path": str(file_path),
                                    "size": stat.st_size,
                                    "modified": datetime.fromtimestamp(stat.st_mtime),
                                }
                    wflog.info(f"보류 목록에서 {len(files)}개 파일 로드")
                    return list(files.values())
            except Exception as pe:
                wflog.warning(f"보류 목록 읽기 실패, 전체 스캔 진행: {pe}")

        # 일반 스캔
        folder_path = Path(folder)

        # 패턴이 단일 문자열인 경우만 지원 (기존 유지). 필요 시 다중 패턴 외부에서 호출.
        for file_path in folder_path.rglob(pattern):
            if file_path.is_file():
                # 고유 키: 절대경로 lower() (확장자 대소문자 차이로 인한 중복 제거)
                key = str(file_path.resolve()).lower()
                if key in files:
                    continue
                stat = file_path.stat()
                files[key] = {
                    "name": file_path.name,
                    "path": str(file_path),
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime),
                }

        return list(files.values())

    def create_comparison_data(self):
        """비교 데이터 생성 (대소문자 무시, 고유 베이스 이름 기준)

        - SLDDRW/DWG 파일을 lower() 확장자/이름 기준으로 매핑
        - 동일 베이스 이름이 여러 번 등장할 경우 첫 번째 것을 기준으로 함
        - 누락된 DWG는 status='missing'
        """
        # 베이스 이름 -> 파일 정보 매핑 (대소문자 무시)
        sld_map = {}
        for f in self.slddrw_files:
            base = f["name"].rsplit(".", 1)[0].lower()
            if base not in sld_map:  # 첫 발견 우선
                sld_map[base] = f

        dwg_map = {}
        for f in self.dwg_files:
            base = f["name"].rsplit(".", 1)[0].lower()
            if base not in dwg_map:
                dwg_map[base] = f

        comparisons = []
        for i, base in enumerate(sorted(sld_map.keys())):
            sld = sld_map[base]
            dwg = dwg_map.get(base)
            comparisons.append(
                {
                    "index": i + 1,
                    "slddrw_file": sld["name"],
                    "slddrw_path": sld["path"],
                    "dwg_file": dwg["name"] if dwg else "",
                    "dwg_path": dwg["path"] if dwg else "",
                    "status": "converted" if dwg else "missing",
                    "slddrw_size": sld["size"],
                    "dwg_size": dwg["size"] if dwg else 0,
                    "modified_time": dwg["modified"] if dwg else None,
                }
            )

        return comparisons

    # 레거시 크레딧 계산/처리는 공통 매니저로 대체됨 (남겨두지 않음)

    def get_analysis_result(self):
        """분석 결과 반환"""
        converted = len([x for x in self.comparison_data if x["status"] == "converted"])
        missing = len([x for x in self.comparison_data if x["status"] == "missing"])
        total = len(self.slddrw_files)
        rate = (converted / total * 100) if total > 0 else 0

        return {
            "total_slddrw": total,
            "converted": converted,
            "missing": missing,
            "conversion_rate": rate,
            "comparison_data": self.comparison_data,
            "summary": f"SLDDRW: {total}개, 변환완료: {converted}개, 변환누락: {missing}개, 변환율: {rate:.1f}%",
        }

    @staticmethod
    def format_file_size(bytes_size):
        """파일 크기 포맷"""
        for unit in ["B", "KB", "MB", "GB"]:
            if bytes_size < 1024.0:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.1f} TB"


class DemoWFLicense:
    """WorksFree 라이선스 관리 클래스"""

    def __init__(self, config=None):
        self.config = config

    def check_license_status(self):
        """라이선스 상태 체크"""
        try:
            # 실제 wf_license 모듈 사용
            if hasattr(wflic, "is_valid"):
                return wflic.is_valid()
            return True
        except Exception as e:
            wflog.error(f"라이선스 체크 오류: {e}")
            return False

    def get_license_info(self):
        """라이선스 정보 반환"""
        try:
            if hasattr(wflic, "get_user_email") and hasattr(wflic, "get_license_type"):
                return {
                    "email": wflic.get_user_email(),
                    "license_type": wflic.get_license_type(),
                    "is_valid": wflic.is_valid(),
                }
        except Exception as e:
            wflog.error(f"라이선스 정보 가져오기 오류: {e}")

        # 기본값 반환
        return {"email": "demo@worksfree.com", "license_type": "데모 라이선스", "is_valid": True}


def run_cli_analysis(folder_path, verbose=False):
    """CLI 모드에서 분석 실행"""
    from app_setting_data import get_config

    config = get_config()

    def cli_progress(value, status):
        if verbose:
            print(f"[{value:3d}%] {status}")

    analyzer = ConversionAnalyzer(config, cli_progress)

    try:
        result = analyzer.analyze_folder(folder_path)

        print("\n=== 분석 결과 ===")
        print(f"SLDDRW 파일: {result['total_slddrw']}개")
        print(f"변환완료: {result['converted']}개")
        print(f"변환누락: {result['missing']}개")
        print(f"변환율: {result['conversion_rate']:.1f}%")

        if verbose and result["comparison_data"]:
            print("\n=== 상세 결과 ===")
            for data in result["comparison_data"]:
                status = "✅" if data["status"] == "converted" else "⚠️"
                print(f"{status} {data['slddrw_file']} → {data['dwg_file'] or '누락'}")

        return result

    except Exception as e:
        print(f"오류: {e}")
        return None


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SOLIDWORKS DWG 변환 검증")
    parser.add_argument("folder", help="분석할 폴더 경로")
    parser.add_argument("-v", "--verbose", action="store_true", help="상세 출력")

    args = parser.parse_args()

    if os.path.exists(args.folder):
        run_cli_analysis(args.folder, args.verbose)
    else:
        print(f"오류: 폴더를 찾을 수 없습니다: {args.folder}")
