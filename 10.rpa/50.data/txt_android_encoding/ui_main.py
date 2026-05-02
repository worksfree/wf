# -*- coding: utf-8 -*-
"""
Text Encoding Fixer Main UI
"""

import os
import sys
import threading
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import filedialog, messagebox
from pathlib import Path

# --- 경로 설정 ---
# 10.common 모듈 경로 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
common_path = os.path.abspath(os.path.join(current_dir, "..", "..", "10.common"))
if common_path not in sys.path:
    sys.path.insert(0, common_path)

# 현재 앱 관련 모듈 import
from app_setting_data import get_config, APP_DISPLAY_NAME, FULL_VERSION
from automation import EncodingFixer

class EncodingFixerApp:
    def __init__(self, master: tk.Tk):
        self.master = master
        self.config = get_config()
        self.automation = None
        self.is_running = False

        self.init_ui()
    
    def init_ui(self):
        """UI 초기화"""
        self.master.title(f"{APP_DISPLAY_NAME} {FULL_VERSION}")
        
        window_width = 500
        window_height = 220
        self.master.geometry(f"{window_width}x{window_height}")
        self.master.minsize(window_width, window_height)
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)

        main_frame = tk.Frame(self.master, padx=10, pady=10)
        main_frame.pack(fill="both", expand=True)

        # --- 1. 폴더 선택 ---
        folder_frame = tk.Frame(main_frame)
        folder_frame.pack(fill="x", pady=5)

        folder_label = tk.Label(folder_frame, text="대상 폴더:", width=10)
        folder_label.pack(side="left")

        self.folder_var = tk.StringVar(value=self.config.get("last_folder"))
        self.folder_entry = tk.Entry(folder_frame, textvariable=self.folder_var)
        self.folder_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self.browse_button = tk.Button(folder_frame, text="폴더 선택", command=self.browse_folder)
        self.browse_button.pack(side="left")

        # --- 2. 진행률 ---
        progress_frame = tk.Frame(main_frame)
        progress_frame.pack(fill="x", pady=5)
        
        self.progress_bar = ttk.Progressbar(progress_frame, orient="horizontal", mode="determinate")
        self.progress_bar.pack(fill="x", expand=True)

        # --- 3. 상태 메시지 ---
        self.status_var = tk.StringVar(value="준비 완료.")
        status_label = tk.Label(main_frame, textvariable=self.status_var, anchor="w", fg="gray")
        status_label.pack(fill="x", pady=5)

        # --- 4. 로그 박스 ---
        log_frame = tk.Frame(main_frame)
        log_frame.pack(fill="both", expand=True, pady=5)
        
        scrollbar = tk.Scrollbar(log_frame)
        scrollbar.pack(side="right", fill="y")
        
        self.log_text = tk.Text(log_frame, height=5, yscrollcommand=scrollbar.set, state="disabled", fg="#333")
        self.log_text.pack(fill="both", expand=True)
        scrollbar.config(command=self.log_text.yview)

        # --- 5. 버튼 ---
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill="x", pady=(10, 0))

        self.run_button = tk.Button(button_frame, text="변환 시작", command=self.start_conversion)
        self.run_button.pack(side="right")
        
        self.cancel_button = tk.Button(button_frame, text="취소", command=self.cancel_conversion, state="disabled")
        self.cancel_button.pack(side="right", padx=(0, 5))


    def browse_folder(self):
        """'폴더 선택' 대화상자를 열어 폴더를 선택하고 경로를 업데이트합니다."""
        folder_selected = filedialog.askdirectory(initialdir=self.folder_var.get())
        if folder_selected:
            self.folder_var.set(folder_selected)
            self.config.set("last_folder", folder_selected)
            self.config.save_settings()

    def start_conversion(self):
        """변환 작업을 시작합니다."""
        if self.is_running:
            return

        folder_path = self.folder_var.get()
        if not folder_path or not os.path.isdir(folder_path):
            messagebox.showerror("오류", "유효한 폴더를 선택해주세요.")
            return

        self.is_running = True
        self.set_ui_state(running=True)
        
        # 로그창 초기화
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.config(state="disabled")

        self.automation = EncodingFixer(
            log_callback=self.log_message,
            progress_callback=self.update_progress
        )
        
        # 별도 스레드에서 작업 실행
        threading.Thread(
            target=self.run_worker,
            args=(folder_path,),
            daemon=True
        ).start()

    def run_worker(self, folder_path):
        """자동화 작업을 실행하는 워커 함수"""
        try:
            self.automation.run_conversion(folder_path)
        except Exception as e:
            self.log_message(f"심각한 오류 발생: {e}", "error")
        finally:
            self.master.after(0, self.on_conversion_complete)

    def cancel_conversion(self):
        """실행 중인 작업을 취소합니다."""
        if self.automation:
            self.automation.cancel()

    def on_conversion_complete(self):
        """작업 완료 시 UI 상태를 복원합니다."""
        self.is_running = False
        self.set_ui_state(running=False)
        self.automation = None

    def set_ui_state(self, running: bool):
        """UI 요소들의 활성화/비활성화 상태를 설정합니다."""
        state = "disabled" if running else "normal"
        self.browse_button.config(state=state)
        self.folder_entry.config(state=state)
        self.run_button.config(state=state)
        self.cancel_button.config(state="normal" if running else "disabled")
        
        if not running:
            self.progress_bar["value"] = 0
            self.status_var.set("준비 완료.")

    def log_message(self, message):
        """automation 모듈의 로그를 UI에 표시합니다."""
        def _update():
            # 상태바 메시지는 마지막 로그 메시지의 첫 줄만 표시
            self.status_var.set(message.split('\n')[0])
            
            # 로그 텍스트 박스에 추가
            self.log_text.config(state="normal")
            self.log_text.insert("end", message + "\n")
            self.log_text.see("end")
            self.log_text.config(state="disabled")
        
        # 메인 스레드에서 UI 업데이트
        self.master.after(0, _update)

    def update_progress(self, value):
        """automation 모듈의 진행률을 UI에 표시합니다."""
        self.master.after(0, lambda: self.progress_bar.config(value=value))

    def on_closing(self):
        """창을 닫을 때 실행됩니다."""
        if self.is_running:
            if messagebox.askyesno("확인", "작업이 진행 중입니다. 정말로 종료하시겠습니까?"):
                if self.automation:
                    self.automation.cancel()
                self.master.destroy()
        else:
            self.config.save_settings()
            self.master.destroy()

def main():
    try:
        root = tk.Tk()
        app = EncodingFixerApp(root)
        root.mainloop()
    except Exception as e:
        # GUI 관련 오류가 발생할 경우를 대비한 최후의 보루
        try:
            messagebox.showerror("치명적 오류", f"프로그램 실행 중 오류가 발생했습니다.\n\n{e}")
        except Exception:
            print(f"FATAL ERROR: {e}")

if __name__ == "__main__":
    main()
