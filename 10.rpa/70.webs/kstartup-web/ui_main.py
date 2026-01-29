# -*- coding: utf-8 -*-
"""
K-Startup Web Automation UI
웹 자동화를 위한 간단하고 안정적인 GUI
"""

import os
import sys
import json
import logging
import threading
from pathlib import Path
from datetime import datetime

# Tkinter 임포트
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import messagebox, filedialog, simpledialog

# 경로 설정
SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_DIR = SCRIPT_DIR / "config" / "kstartup_web"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

# 로거 설정
LOG_DIR = CONFIG_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("kstartup_web")
logger.setLevel(logging.INFO)

# 파일 핸들러
log_file = LOG_DIR / f"ui_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
fh = logging.FileHandler(log_file, encoding='utf-8')
fh.setLevel(logging.INFO)

# 콘솔 핸들러
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

# 포매터
formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
fh.setFormatter(formatter)
ch.setFormatter(formatter)

logger.addHandler(fh)
logger.addHandler(ch)

# 공통 경로 추가
COMMON_PATH = Path(__file__).resolve().parents[2] / "10.common"
if str(COMMON_PATH) not in sys.path:
    sys.path.insert(0, str(COMMON_PATH))

# WorksFree 모듈 임포트
try:
    from wf_log import get_app_logger
    from wf_credit_manager import WorksFreeManager, CreditManager
    from wf_app_init_helpers import init_credit_and_policy_managers
    WORKSFREE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"WorksFree 모듈 import 실패: {e}")
    WORKSFREE_AVAILABLE = False

# automation 모듈 임포트
try:
    from automation import WebAutomationConfig, WebActionParser, WebAutomationEngine
    AUTOMATION_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Automation 모듈 import 실패: {e}")
    AUTOMATION_AVAILABLE = False


class KStartupWebApp:
    """K-Startup 웹 자동화 GUI 애플리케이션"""

    def __init__(self, root):
        """앱 초기화"""
        self.root = root
        self.root.title("K-Startup 웹 자동화 v1.0")
        self.root.geometry("600x250")
        self.root.resizable(False, False)

        # 변수
        self.excel_file_var = tk.StringVar()
        self.is_running = False
        self.is_admin_mode = False
        # admin 비밀번호: Google Sheets admin_config에서 로드 (실패 시 기본값)
        try:
            from wf_settings_common import get_admin_password  # type: ignore
            self.admin_password = get_admin_password(logger)
        except Exception:
            self.admin_password = "admin2024"  # fallback

        # WorksFree 초기화
        self.wf_manager = None
        self.credit_manager = None
        self.is_registered = False

        logger.info("앱 초기화 시작")

        # UI 생성
        self._create_ui()

        # 종료 처리
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

        # 백그라운드 초기화
        self._init_background()

        logger.info("앱 초기화 완료")

    def _create_ui(self):
        """UI 생성"""
        # 메인 프레임
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill="both", expand=True)

        # 파일 선택 영역
        file_frame = ttk.LabelFrame(main_frame, text="Excel 파일 선택", padding=5)
        file_frame.pack(fill="x", pady=5)

        ttk.Entry(file_frame, textvariable=self.excel_file_var, width=50).pack(side="left", fill="x", expand=True, padx=(0, 5))
        ttk.Button(file_frame, text="찾기", command=self._select_file, width=8).pack(side="left")

        # 버튼 영역
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=10)

        self.start_button = ttk.Button(button_frame, text="시작", command=self._start_automation, width=12)
        self.start_button.pack(side="left", padx=5)

        self.stop_button = ttk.Button(button_frame, text="중지", command=self._stop_automation, state="disabled", width=12)
        self.stop_button.pack(side="left", padx=5)

        ttk.Button(button_frame, text="설정", command=self._open_settings, width=12).pack(side="left", padx=5)

        self.register_button = ttk.Button(button_frame, text="등록", command=self._open_register, width=12)
        self.register_button.pack(side="right", padx=5)

        # 상태 표시
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill="x", pady=5)

        ttk.Label(status_frame, text="상태:").pack(side="left", padx=5)
        self.status_var = tk.StringVar(value="대기 중")
        ttk.Label(status_frame, textvariable=self.status_var, font=("맑은 고딕", 10, "bold")).pack(side="left")

        # 프로그레스 바
        self.progress_var = tk.IntVar(value=0)
        self.progress = ttk.Progressbar(main_frame, variable=self.progress_var, maximum=100)
        self.progress.pack(fill="x", pady=5)

        # 로그 영역 (숨김)
        self.log_frame = ttk.LabelFrame(main_frame, text="로그", padding=5)
        self.log_scrollbar = ttk.Scrollbar(self.log_frame)
        self.log_scrollbar.pack(side="right", fill="y")

        self.log_text = tk.Text(self.log_frame, height=8, font=("Consolas", 9), yscrollcommand=self.log_scrollbar.set)
        self.log_text.pack(side="left", fill="both", expand=True)
        self.log_scrollbar.config(command=self.log_text.yview)

        logger.info("UI 생성 완료")

    def _init_background(self):
        """백그라운드 초기화"""
        def worker():
            try:
                if WORKSFREE_AVAILABLE:
                    logger.info("WorksFreeManager 초기화 중...")
                    self.wf_manager = WorksFreeManager()
                    self.is_registered = self.wf_manager.is_registered()
                    logger.info(f"WorksFreeManager 초기화 완료 (등록: {self.is_registered})")

                    if self.is_registered:
                        self.register_button.config(text="등록 완료")
            except Exception as e:
                logger.warning(f"BackgroundInit 실패: {e}")

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def _select_file(self):
        """파일 선택"""
        initial_dir = str(Path.home())
        file_path = filedialog.askopenfilename(
            title="Excel 파일 선택",
            filetypes=[("Excel", "*.xlsx"), ("모든 파일", "*.*")],
            initialdir=initial_dir
        )
        if file_path:
            self.excel_file_var.set(file_path)
            logger.info(f"파일 선택됨: {file_path}")

    def _start_automation(self):
        """자동화 시작"""
        excel_file = self.excel_file_var.get()
        if not excel_file:
            messagebox.showerror("오류", "Excel 파일을 선택하세요")
            return

        if not Path(excel_file).exists():
            messagebox.showerror("오류", f"파일을 찾을 수 없습니다: {excel_file}")
            return

        self.is_running = True
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.status_var.set("실행 중...")
        self.progress_var.set(0)

        logger.info(f"자동화 시작: {excel_file}")
        thread = threading.Thread(target=self._run_automation, args=(excel_file,), daemon=True)
        thread.start()

    def _run_automation(self, excel_file):
        """자동화 실행"""
        try:
            if not AUTOMATION_AVAILABLE:
                raise Exception("Automation 모듈을 사용할 수 없습니다")

            logger.info("Excel 파일 파싱 중...")
            parser = WebActionParser(excel_file)
            actions = parser.parse()
            logger.info(f"총 {len(actions)}개의 액션을 로드했습니다")

            logger.info("WebDriver 초기화 중...")
            config = WebAutomationConfig()
            engine = WebAutomationEngine(config)
            engine.initialize_driver()

            logger.info("액션 실행 중...")
            results = engine.execute_actions(actions)
            engine.close_driver()

            logger.info(f"실행 완료 - 성공: {results.get('success', 0)}, 실패: {results.get('failed', 0)}")
            self.status_var.set("완료")
            self.progress_var.set(100)

            if results.get('failed', 0) == 0:
                messagebox.showinfo("완료", f"자동화가 완료되었습니다.\n성공: {results.get('success', 0)}개")
            else:
                messagebox.showwarning("부분 완료", f"성공: {results.get('success', 0)}개\n실패: {results.get('failed', 0)}개")

        except Exception as e:
            logger.error(f"자동화 실행 중 오류: {e}", exc_info=True)
            messagebox.showerror("오류", f"자동화 실행 중 오류 발생:\n{str(e)}")
            self.status_var.set("오류")
        finally:
            self._reset_ui_state()

    def _reset_ui_state(self):
        """UI 상태 복원"""
        self.is_running = False
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")

    def _stop_automation(self):
        """자동화 중지"""
        self.is_running = False
        self.status_var.set("중지됨")
        self._reset_ui_state()
        logger.info("자동화 중지됨")

    def _open_settings(self):
        """설정 열기"""
        messagebox.showinfo("설정", "설정 기능은 향후 추가될 예정입니다.")

    def _open_register(self):
        """등록 열기"""
        if self.is_registered:
            messagebox.showinfo("등록", "이미 등록된 사용자입니다.")
        else:
            messagebox.showinfo("등록", "등록 기능은 향후 추가될 예정입니다.")

    def toggle_admin_mode(self):
        """관리자 모드 토글"""
        if not self.is_admin_mode:
            password = simpledialog.askstring("관리자", "비밀번호:", show="*")
            if password == self.admin_password:
                self.is_admin_mode = True
                self.log_frame.pack(fill="both", expand=True, pady=5)
                self.root.geometry("600x500")
                logger.info("관리자 모드 활성화")
            else:
                messagebox.showerror("오류", "비밀번호가 올바르지 않습니다.")
        else:
            self.is_admin_mode = False
            self.log_frame.pack_forget()
            self.root.geometry("600x250")
            logger.info("관리자 모드 비활성화")

    def _on_closing(self):
        """종료"""
        logger.info("프로그램 종료")
        self.root.destroy()


def main():
    """메인 함수"""
    try:
        logger.info("=" * 60)
        logger.info("K-Startup 웹 자동화 시작")
        logger.info("=" * 60)

        root = tk.Tk()
        app = KStartupWebApp(root)

        # Alt+A: 관리자 모드
        root.bind('<Alt-a>', lambda e: app.toggle_admin_mode())
        root.bind('<Alt-A>', lambda e: app.toggle_admin_mode())

        logger.info("메인 루프 시작 - 메인 창이 화면에 표시됩니다")
        root.mainloop()

    except Exception as e:
        logger.error(f"치명적 오류: {e}", exc_info=True)
        messagebox.showerror("오류", f"프로그램 실행 중 오류 발생:\n{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
