# -*- coding: utf-8 -*-
"""
Deployed App Tester - 배포된 앱 자동 테스트 프레임워크

배포된 EXE 파일을 실행하고 기본 동작을 검증합니다.
UI 자동화 없이 프로세스 실행/종료 및 로그 기반 검증을 수행합니다.

사용법:
    python deployed_app_tester.py <app_name> [--register] [--quick]
    python deployed_app_tester.py bom_exporter --register
"""

import os
import sys
import subprocess
import time
import json
import argparse
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Tuple


# 릴리스 후보 경로
CANDIDATES_DIR = Path(r"D:\release\candidates")
USER_CONFIG_DIR = Path.home() / ".wf_rpa"
USER_CONFIG_FILE = USER_CONFIG_DIR / "wf_rpa_config.json"  # 공용 설정 (등록 정보 포함)


class DeployedAppTester:
    """배포된 앱 테스터"""

    def __init__(self, app_name: str, verbose: bool = True):
        self.app_name = app_name
        self.verbose = verbose
        self.exe_path: Optional[Path] = None
        self.app_dir: Optional[Path] = None
        self.version: Optional[str] = None
        self.process: Optional[subprocess.Popen] = None
        self.test_results: List[Dict] = []

    def log(self, msg: str, level: str = "INFO"):
        """로그 출력"""
        if self.verbose or level in ("ERROR", "WARN"):
            timestamp = datetime.now().strftime("%H:%M:%S")
            # cp949 호환 ASCII 문자 사용
            prefix = {"INFO": "[i]", "OK": "[OK]", "WARN": "[!!]", "ERROR": "[ERR]", "RUN": "[>>]"}.get(level, "[*]")
            try:
                print(f"[{timestamp}] {prefix} {msg}")
            except UnicodeEncodeError:
                print(f"[{timestamp}] {prefix} {msg.encode('ascii', 'replace').decode()}")

    def find_latest_build(self) -> bool:
        """최신 빌드 찾기"""
        self.log(f"Finding latest build for {self.app_name}...")

        if not CANDIDATES_DIR.exists():
            self.log(f"Candidates directory not found: {CANDIDATES_DIR}", "ERROR")
            return False

        # 앱 이름으로 시작하는 폴더 찾기
        app_folders = sorted(
            [d for d in CANDIDATES_DIR.iterdir()
             if d.is_dir() and d.name.startswith(f"{self.app_name}_")],
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )

        if not app_folders:
            self.log(f"No builds found for {self.app_name}", "ERROR")
            return False

        latest = app_folders[0]
        self.log(f"Latest build folder: {latest.name}")

        # portable 폴더 찾기
        portable_folders = list(latest.glob("*_portable"))
        if not portable_folders:
            self.log(f"No portable folder in {latest}", "ERROR")
            return False

        portable = portable_folders[0]
        exe_path = portable / f"{self.app_name}.exe"

        if not exe_path.exists():
            self.log(f"EXE not found: {exe_path}", "ERROR")
            return False

        self.app_dir = portable
        self.exe_path = exe_path

        # 버전 추출
        try:
            self.version = latest.name.replace(f"{self.app_name}_", "")
        except:
            self.version = "unknown"

        self.log(f"Found: {exe_path} (v{self.version})", "OK")
        return True

    def check_user_config(self) -> Dict:
        """사용자 설정 상태 확인"""
        result = {
            "config_dir_exists": False,
            "app_config_exists": False,
            "is_registered": False,
            "has_credits": False,
            "credits_remaining": 0,
            "user_email": None
        }

        app_config_dir = USER_CONFIG_DIR / self.app_name
        result["config_dir_exists"] = USER_CONFIG_DIR.exists()
        result["app_config_exists"] = app_config_dir.exists()

        # wf_rpa_config.json에서 등록 정보 확인 (공용)
        if USER_CONFIG_FILE.exists():
            try:
                with open(USER_CONFIG_FILE, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    user_info = config.get("user_info", {})
                    result["is_registered"] = bool(user_info.get("is_registered", False))
                    result["user_email"] = user_info.get("user_email")
            except:
                pass

        # 앱별 credit_history.json 확인
        credit_path = app_config_dir / "credit_history.json"
        if credit_path.exists():
            try:
                with open(credit_path, "r", encoding="utf-8") as f:
                    credits = json.load(f)
                    result["credits_remaining"] = credits.get("remaining_credits", 0)
                    result["has_credits"] = result["credits_remaining"] > 0
            except:
                pass

        return result

    def reset_user_config(self) -> bool:
        """사용자 등록 정보 초기화 (등록 테스트용)

        wf_rpa_config.json의 user_info.is_registered를 false로 설정
        """
        if not USER_CONFIG_FILE.exists():
            self.log("No config file to reset")
            return True

        self.log(f"Resetting registration in: {USER_CONFIG_FILE}", "WARN")

        try:
            with open(USER_CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)

            # user_info 초기화 (등록 해제)
            if "user_info" in config:
                old_email = config["user_info"].get("user_email", "unknown")
                config["user_info"] = {
                    "is_registered": False,
                    "user_email": "",
                    "user_name": "",
                    "user_phone": "",
                    "user_email_consent": "",
                    "client_hw_fingerprint": config["user_info"].get("client_hw_fingerprint", ""),
                    "client_hw_cpuinfo": config["user_info"].get("client_hw_cpuinfo", ""),
                    "client_hw_mbinfo": config["user_info"].get("client_hw_mbinfo", ""),
                    "client_hw_storageinfo": config["user_info"].get("client_hw_storageinfo", ""),
                    "reg_time_local": "",
                    "reg_time_utc": "",
                    "reg_tz_name": "",
                    "last_login": ""
                }
                self.log(f"Registration cleared (was: {old_email})", "OK")

            with open(USER_CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            return True

        except Exception as e:
            self.log(f"Failed to reset config: {e}", "ERROR")
            return False

    def start_app(self, timeout: int = 30) -> bool:
        """앱 실행"""
        if not self.exe_path:
            self.log("EXE path not set", "ERROR")
            return False

        self.log(f"Starting {self.exe_path.name}...", "RUN")

        try:
            # 환경 변수 설정 (테스트 모드)
            env = os.environ.copy()
            env["WF_TEST_MODE"] = "1"

            self.process = subprocess.Popen(
                [str(self.exe_path)],
                cwd=str(self.app_dir),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            # 프로세스 시작 대기
            time.sleep(3)

            if self.process.poll() is not None:
                # 이미 종료됨
                stdout, stderr = self.process.communicate()
                self.log(f"App exited immediately with code {self.process.returncode}", "ERROR")
                if stderr:
                    self.log(f"STDERR: {stderr.decode('utf-8', errors='ignore')[:500]}", "ERROR")
                return False

            self.log(f"App started (PID: {self.process.pid})", "OK")
            return True

        except Exception as e:
            self.log(f"Failed to start app: {e}", "ERROR")
            return False

    def stop_app(self, timeout: int = 10) -> bool:
        """앱 종료"""
        if not self.process:
            return True

        self.log("Stopping app...")

        try:
            self.process.terminate()
            try:
                self.process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                self.log("Force killing app...", "WARN")
                self.process.kill()
                self.process.wait(timeout=5)

            self.log("App stopped", "OK")
            return True

        except Exception as e:
            self.log(f"Error stopping app: {e}", "ERROR")
            return False

    def run_quick_test(self) -> bool:
        """빠른 시작/종료 테스트"""
        self.log("=" * 50)
        self.log("Running Quick Test (Start/Stop)")
        self.log("=" * 50)

        result = {"name": "quick_test", "passed": False, "details": {}}

        # 최신 빌드 찾기
        if not self.find_latest_build():
            result["details"]["error"] = "Build not found"
            self.test_results.append(result)
            return False

        # 앱 실행
        if not self.start_app():
            result["details"]["error"] = "Failed to start"
            self.test_results.append(result)
            return False

        # 5초 대기 후 프로세스 상태 확인
        time.sleep(5)

        if self.process and self.process.poll() is None:
            result["passed"] = True
            result["details"]["status"] = "Running normally"
            self.log("App running normally for 5 seconds", "OK")
        else:
            result["details"]["error"] = "App crashed within 5 seconds"
            self.log("App crashed!", "ERROR")

        # 앱 종료
        self.stop_app()

        self.test_results.append(result)
        return result["passed"]

    def run_registration_test(self, reset_first: bool = True) -> bool:
        """등록 플로우 테스트"""
        self.log("=" * 50)
        self.log("Running Registration Test")
        self.log("=" * 50)

        result = {"name": "registration_test", "passed": False, "details": {}}

        # 최신 빌드 찾기
        if not self.find_latest_build():
            result["details"]["error"] = "Build not found"
            self.test_results.append(result)
            return False

        # 설정 초기화 (선택적)
        if reset_first:
            self.reset_user_config()

        # 초기 상태 확인
        before = self.check_user_config()
        result["details"]["before"] = before
        self.log(f"Before: registered={before['is_registered']}, credits={before['credits_remaining']}")

        # 앱 실행
        if not self.start_app():
            result["details"]["error"] = "Failed to start"
            self.test_results.append(result)
            return False

        # 앱이 초기화될 시간 대기
        self.log("Waiting for app initialization (10s)...")
        time.sleep(10)

        # 상태 다시 확인
        after = self.check_user_config()
        result["details"]["after"] = after
        self.log(f"After: registered={after['is_registered']}, credits={after['credits_remaining']}")

        # 앱 종료
        self.stop_app()

        # 검증
        if after["app_config_exists"]:
            result["passed"] = True
            result["details"]["status"] = "Config created successfully"
            self.log("App config created successfully", "OK")

            if after["is_registered"]:
                self.log(f"User is registered!", "OK")
            elif after["has_credits"]:
                self.log(f"Trial credits granted: {after['credits_remaining']}", "OK")
            else:
                self.log("User not registered, no trial credits", "WARN")
        else:
            result["details"]["error"] = "Config not created"
            self.log("App config was NOT created", "ERROR")

        self.test_results.append(result)
        return result["passed"]

    def print_summary(self):
        """테스트 결과 요약"""
        self.log("")
        self.log("=" * 50)
        self.log("TEST SUMMARY")
        self.log("=" * 50)

        passed = sum(1 for r in self.test_results if r["passed"])
        total = len(self.test_results)

        for r in self.test_results:
            status = "✅ PASS" if r["passed"] else "❌ FAIL"
            self.log(f"  {r['name']}: {status}")
            if not r["passed"] and "error" in r.get("details", {}):
                self.log(f"    → {r['details']['error']}")

        self.log("")
        self.log(f"Result: {passed}/{total} tests passed")

        return passed == total


def main():
    parser = argparse.ArgumentParser(description="Deployed App Tester")
    parser.add_argument("app_name", help="App name (e.g., bom_exporter)")
    parser.add_argument("--register", action="store_true", help="Run registration test")
    parser.add_argument("--quick", action="store_true", help="Run quick start/stop test")
    parser.add_argument("--reset", action="store_true", help="Reset user config before test")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    parser.add_argument("-q", "--quiet", action="store_true", help="Quiet mode")

    args = parser.parse_args()

    tester = DeployedAppTester(args.app_name, verbose=not args.quiet)

    # 기본: quick 테스트
    if args.all or (not args.register and not args.quick):
        args.quick = True

    if args.quick:
        tester.run_quick_test()

    if args.register or args.all:
        tester.run_registration_test(reset_first=args.reset)

    all_passed = tester.print_summary()
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
