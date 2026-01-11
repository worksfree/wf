import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os

from automation import ExcelAutomation


class ExcelPerformanceTester(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("대용량 Excel 성능 테스터")
        self.geometry("550x280")  # 창 크기 확장
        self.resizable(False, False)

        try:
            self.automation = ExcelAutomation()
        except ImportError as e:
            messagebox.showerror("패키지 오류", f"{e}")
            self.destroy()
            return

        self.file_path = None
        self._init_ui()

    def _init_ui(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- 파일 선택 ---
        file_frame = ttk.LabelFrame(main_frame, text="파일 선택 (.xlsx 선택 시 .xlsb와 자동 비교)")
        file_frame.pack(fill=tk.X, pady=5)

        self.file_entry = ttk.Entry(file_frame, state="readonly")
        self.file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)

        self.open_button = ttk.Button(file_frame, text="파일 열기", command=self.open_file)
        self.open_button.pack(side=tk.RIGHT, padx=5, pady=5)

        # --- 성능 측정 결과 (Grid 레이아웃으로 변경) ---
        self.result_frame = ttk.LabelFrame(main_frame, text="성능 측정 결과")
        self.result_frame.pack(fill=tk.X, pady=5)
        self.result_frame.columnconfigure(1, weight=1)
        self.result_frame.columnconfigure(2, weight=1)

        # -- XLSX 행 --
        ttk.Label(self.result_frame, text="XLSX", font=("TkDefaultFont", 13, "bold")).grid(
            row=0, column=0, padx=5, pady=2, sticky="w"
        )
        self.xlsx_load_label = ttk.Label(self.result_frame, text="로딩 시간: -")
        self.xlsx_load_label.grid(row=0, column=1, padx=5, pady=2, sticky="w")
        self.xlsx_size_label = ttk.Label(self.result_frame, text="파일 크기: -")
        self.xlsx_size_label.grid(row=0, column=2, padx=5, pady=2, sticky="w")

        # -- XLSB 행 (초기에는 숨김) --
        self.xlsb_type_label = ttk.Label(
            self.result_frame, text="XLSB", font=("TkDefaultFont", 13, "bold")
        )
        self.xlsb_load_label = ttk.Label(self.result_frame, text="로딩 시간: -")
        self.xlsb_size_label = ttk.Label(self.result_frame, text="파일 크기: -")
        self.speed_comp_label = ttk.Label(self.result_frame, text="", foreground="green")
        self.size_comp_label = ttk.Label(self.result_frame, text="", foreground="green")

        # --- 제어 버튼 & 프로그레스바 ---
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=(10, 0))
        self.exit_button = ttk.Button(bottom_frame, text="종료", command=self.quit)
        self.exit_button.pack(side=tk.RIGHT)
        self.progress = ttk.Progressbar(bottom_frame, mode="determinate", value=0)
        self.progress.pack(fill=tk.X, side=tk.LEFT, expand=True, padx=(0, 10))

    def open_file(self):
        file_path = filedialog.askopenfilename(
            title="Excel 파일 선택",
            filetypes=(("Excel files", "*.xlsx *.xlsb"), ("All files", "*.*")),
        )
        if not file_path:
            return

        self.file_path = file_path
        self.file_entry.config(state="normal")
        self.file_entry.delete(0, tk.END)
        self.file_entry.insert(0, os.path.basename(file_path))
        self.file_entry.config(state="readonly")

        self._reset_labels()
        threading.Thread(target=self._run_performance_test, daemon=True).start()
        self.progress.config(mode="indeterminate")
        self.progress.start()
        self.open_button.config(state="disabled")
        self.exit_button.config(state="disabled")

    def _run_performance_test(self):
        result = self.automation.run_performance_check(self.file_path)
        self.after(0, self._update_ui_with_result, result)

    def _update_ui_with_result(self, result):
        self.progress.stop()
        self.progress.config(mode="determinate")
        self.progress["value"] = 0
        self.open_button.config(state="normal")
        self.exit_button.config(state="normal")

        if result.get("warning"):
            messagebox.showwarning("경고", result["warning"])

        if not result["comparison_mode"]:
            res = result["result"]
            if res["success"]:
                self.xlsx_load_label.config(text=f"로딩 시간: {res['load_time']:.4f} 초")
                self.xlsx_size_label.config(text=f"파일 크기: {self._format_bytes(res['size'])}")
            else:
                messagebox.showerror("오류", f"파일 처리 중 오류 발생:\n{res['error']}")
            return

        # 비교 모드 UI 업데이트
        xlsx = result["xlsx"]
        xlsb = result["xlsb"]
        metrics = result["metrics"]

        self.xlsx_load_label.config(text=f"로딩 시간: {xlsx['load_time']:.4f} 초")
        self.xlsx_size_label.config(text=f"파일 크기: {self._format_bytes(xlsx['size'])}")

        self.xlsb_load_label.config(text=f"로딩 시간: {xlsb['load_time']:.4f} 초")
        self.xlsb_size_label.config(text=f"파일 크기: {self._format_bytes(xlsb['size'])}")
        self.speed_comp_label.config(text=f"({metrics['speed_multiplier']:.1f}배 빠름)")
        self.size_comp_label.config(text=f"({metrics['size_reduction_percent']:.1f}% 작음)")

        # XLSB 행 위젯들을 grid에 추가하여 표시
        self.xlsb_type_label.grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.xlsb_load_label.grid(row=1, column=1, padx=5, pady=2, sticky="w")
        self.xlsb_size_label.grid(row=1, column=2, padx=5, pady=2, sticky="w")
        self.speed_comp_label.grid(row=1, column=1, padx=(120, 0), sticky="w")
        self.size_comp_label.grid(row=1, column=2, padx=(120, 0), sticky="w")

    def _reset_labels(self):
        self.xlsx_load_label.config(text="로딩 시간: -")
        self.xlsx_size_label.config(text="파일 크기: -")
        # grid에서 XLSB 행 위젯들을 제거하여 숨김
        self.xlsb_type_label.grid_remove()
        self.xlsb_load_label.grid_remove()
        self.xlsb_size_label.grid_remove()
        self.speed_comp_label.grid_remove()
        self.size_comp_label.grid_remove()

    def _format_bytes(self, size_bytes: int) -> str:
        if not isinstance(size_bytes, (int, float)) or size_bytes < 0:
            return "-"
        if size_bytes < 1024:
            return f"{size_bytes} Bytes"
        size_kb = size_bytes / 1024
        if size_kb < 1024:
            return f"{size_kb:.2f} KB"
        size_mb = size_kb / 1024
        if size_mb < 1024:
            return f"{size_mb:.2f} MB"
        size_gb = size_mb / 1024
        return f"{size_gb:.2f} GB"


if __name__ == "__main__":
    app = ExcelPerformanceTester()
    app.mainloop()
