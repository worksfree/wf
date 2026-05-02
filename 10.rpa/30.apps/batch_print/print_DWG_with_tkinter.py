#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# import sys 및 co init 플래그를 2로 설정하는 것을 가장 먼저 해야 함
# 이렇게 하지 않으면 askdirectory 함수를 호출할 때 진행이 안됨
# https://pywinauto.readthedocs.io/en/latest/HowTo.html#com-threading-model
import pythoncom
pythoncom.CoInitializeEx(pythoncom.COINIT_APARTMENTTHREADED)

import os
import time
from time import ctime
import ntplib
import datetime
import tkinter.messagebox
import tkinter as tk
from tkinter import filedialog, ttk

import pyautogui as pgui
from pywinauto.application import Application


class DwgPrinterApp:
    def __init__(self, master):
        self.master = master
        master.title('DWG 출력')

        # Initialize variables
        self.folder_path = None
        self.stop_progress_flag = False
        self.restart_count = 30
        self.max_count = 0
        # 사내 배포용 만기일, 만기일 없애려면 로직을 바꿔야 하므로 어렵다고 할 것.
        self.expire_date = datetime.datetime(2025, 12, 31, 23, 59)
        # 외주 배포용 만기일
        # self.expire_date = datetime.datetime(2023, 4, 27, 23, 59, 59)
        # 테스트용 만기일
        # self.expire_date = datetime.datetime(2023, 4, 17, 15, 5, 0, 0)

        # Create UI elements
        self.folder_button = tk.Button(
            master, text='폴더 선택', command=self.select_folder)
        self.print_button = tk.Button(
            master, text='출력', command=self.print_dwg_files)
        self.print_button.config(state='disabled')
        self.stop_button = tk.Button(
            master, text='일시 정지', command=self.stop_progress, state='disabled')
        self.exit_button = tk.Button(
            master, text='종료', command=self.master.destroy)
        self.progress_bar = tk.ttk.Progressbar(
            master, orient='horizontal', length=200, mode='determinate')
        self.progress_label = tk.Label(master, text='?/?')
        format = '%m/%d 만료'
        self.expire_label = tk.Label(master, text=datetime.datetime.strftime(self.expire_date, format))
        
        # Position UI elements
        self.folder_button.grid(row=0, column=0, padx=10, pady=10)
        self.progress_bar.grid(row=0, column=1, columnspan=2, padx=10, pady=10)
        self.expire_label.grid(row=1, column=0, padx=10, pady=0)
        self.progress_label.grid(row=1, column=1, columnspan=2, padx=10, pady=0)
        self.print_button.grid(row=2, column=0, padx=10, pady=10)
        self.stop_button.grid(row=2, column=1, padx=10, pady=10)
        self.exit_button.grid(row=2, column=2, padx=10, pady=10)

    def select_folder(self):
        # 로컬 타임이 아닌 타임서버로 만료일 체크, 네트워크가 없으면 동작 안할 거임
        ntp_client = ntplib.NTPClient()
        # response = ntp_client.request('time.windows.com')
        response = ntp_client.request('time.google.com')
        ntp_time = datetime.datetime.fromtimestamp(response.tx_time)
        if self.expire_date < ntp_time: # 로컬PC 시간이랑 비교할 경우는 =>  < datetime.datetime.now():
            self.print_button.config(state='disabled')
            # tkinter.messagebox.showinfo('기간 만료 경과', f"{self.expired_date}까지 사용이 허가 되어 있습니다.\
            #                              \n사용기간이 만료되었으니 <a href='mailto:insung.lee1973@gmail.com'>\
            #                              담당자</a>에 문의하세요")
            # 위 코드로는 이메일 링크를 넣을 수 없고 그냥 링크가 텍스트로 노출이 되며 링크로 먹지도 않음
            tkinter.messagebox.showinfo('기간 만료 경과', f"{self.expire_date}까지 사용이 허가 되어 있습니다.\
                                        \n사용기간이 만료되었으니 제일FA 담당자에 문의하세요")
        else:
            # Show folder dialog and get selected path
            self.folder_path = filedialog.askdirectory(initialdir=r'D:\test_data\mct_batch_print')
            if self.folder_path:
                # Check if there are any DWG or dwg files in the folder
                dwg_files = [f for f in os.listdir(
                    self.folder_path) if f.lower().endswith('.dwg')]
                if dwg_files:
                    # Get file count
                    self.max_count = len(dwg_files)
                    # Enable print button if there are DWG files
                    self.print_button.config(state='normal')
                    self.stop_button.config(state='normal')
                    # Set progress bar max value
                    self.progress_bar.config(maximum=self.max_count)
                    self.progress_bar.config(value=0)
                    self.progress_bar.update()
                    # Set progress label max value
                    self.progress_label.config(text = f'0/{self.max_count}')
                else:
                    # Disable print button if there are no DWG files
                    self.print_button.config(state='disabled')
                    self.progress_bar.config(maximum=1, value=0)
                    self.progress_bar.stop()
                    tk.messagebox.showwarning(
                        'Warning', 'No DWG files found in selected folder.')
            else:
                # Disable print button if no folder is selected
                self.print_button.config(state='disabled')
                self.progress_bar.config(maximum=1, value=0)
                self.progress_bar.stop()

    def print_dwg_files(self):
        # Disable UI elements while printing
        self.folder_button.config(state='disabled')
        self.print_button.config(state='disabled')
        self.stop_button.config(state='normal')

        # Loop through DWG files in folder and print them
        dwg_files = [f for f in os.listdir(
            self.folder_path) if f.lower().endswith('.dwg')]
        self.max_count = len(dwg_files)
        for i, dwg_file in enumerate(dwg_files):
            if self.stop_progress_flag:
                # Stop printing if stop button is clicked
                break
            else:
                # Update progress bar and print DWG file
                self.progress_bar.config(value=i+1)
                self.progress_label.config(text = f'{i+1}/{self.max_count}')
                self.print_dwg_file(i, dwg_file)
                self.progress_bar.update()

        # Reset UI elements after printing
        self.folder_button.config(state='normal')
        self.print_button.config(state='disabled')
        self.stop_button.config(state='disabled')

        # self.progress_bar.stop()
        # self.progress_bar.config(value=0)

    def print_dwg_file(self, idx, dwg_file):
        file_path = os.path.join(str(self.folder_path), str(dwg_file))
        print(f'{ctime()} {idx+1}/{self.max_count} {file_path}')
        # eDrawings.exe 파일은 멀티플 인스턴스가 생성되지 않음, start를 계속 실행해도 싱글 인스턴스로 실행됨
        # SNG 전용으로 eDrawings.exe가 위치한 경로가 상이함
        # eDrawings_App = Application(backend='uia').start(
            # f'C:\Program Files\Common Files\eDrawings2023\eDrawings.exe {os.path.join(self.folder_path, dwg_file)}')
        # eDrawings_App = Application(backend='uia').start(   
        #     f'C:\Program Files\SOLIDWORKS Corp\eDrawings\eDrawings.exe {os.path.join(self.folder_path, dwg_file)}')
        eDrawings_App = Application(backend='uia').start(   
            f'C:\Program Files\SOLIDWORKS Corp\eDrawings\eDrawings.exe "{file_path}"')
        print('started')
        eDrawings_App = eDrawings_App.connect(title_re='eDrawings', timeout=10, found_index=0)
        print('connected')

        pgui.hotkey('ctrl', 'p')
        dlg = eDrawings_App.top_window()
        dlg.wait('enabled')
        # dlg.child_window(title='확인', control_type='Button').click()
        # dlg.child_window(title='확인', control_type='Button').wait('enabled', timeout=300).click()
        dlg.child_window(title='취소', control_type='Button').wait('enabled', timeout=300).click()
        print(dwg_file)
        # dialog box for printing has appeared and disappeared when it finished to print
        dlg.wait('enabled')

        print(idx, self.restart_count, self.max_count)
        # 리스트 인덱스가 0이 아닌 경우이면서: 즉 처음은 0부터 시작하므로...
        # 현재 인덱스 값을 restart_count로 나머지 연산한 값이 restart_count-1과 같은 경우이면서
        # 또는 목록의 끝에 도달한 경우 이드로잉스 뷰어를 종료함
        if (idx !=0 and idx%self.restart_count==self.restart_count-1):
            print(f'app kill {idx}, {self.max_count-1}')
            eDrawings_App.kill()
            time.sleep(5) # 3초 했더니 20장 이후 연속처리가 안됨 10장은 3초 슬립도 OK
        if(idx == self.max_count-1):
            print('end')
            time.sleep(3)   # 마지막 출력을 마무리 하는 시간이 필요하여 3초 슬립 부여하고 앱 종료
            eDrawings_App.kill()

    def stop_progress(self):
        # Set stop flag to stop printing
        self.stop_progress_flag = True


root = tk.Tk()
root.wm_attributes('-topmost', 1)
app = DwgPrinterApp(root)
root.mainloop()
