# -*- coding: utf-8 -*-
"""
Attribute Reset Automation
솔리드웍스 속성 리셋 자동화 핵심 로직
"""

import sys
import os
import time
import datetime
import pyautogui
import pyperclip
import pandas as pd
import winsound
from pathlib import Path
from pywinauto.application import Application

# Add common modules path
current_dir = Path(__file__).resolve().parent
common_path = current_dir.parent.parent / "10.common"
if common_path.exists():
    sys.path.append(str(common_path))
else:
    print(f"Error: Common modules path not found at {common_path}", file=sys.stderr)

# Local and common imports
from app_setting_data import get_config
try:
    import wf_log as wflog
except ImportError:
    print("Warning: wf_log not found. Using basic logging.", file=sys.stderr)
    import logging
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    wflog = logging

try:
    from wf_email import send_error_email, send_completion_email as wf_send_completion
except ImportError:
    print("Warning: wf_email not found. Email notifications disabled.", file=sys.stderr)
    send_error_email = None
    wf_send_completion = None

class AttributeResetAutomation:
    """Attribute Reset Automation Core Class"""

    def __init__(self, console_mode=True):
        self.config = get_config()
        self.logger = wflog.getLogger('attribute_reset') if hasattr(wflog, 'getLogger') else wflog.getLogger()
        self.console_mode = console_mode
        
        self.app = None
        self.dlg = None
        self.progress_callback = None
        self.credit_manager = None
        self.stop_flag = False

        width, height = pyautogui.size()
        self.resolution = 'qhd' if width > 1920 else 'fhd'
        self.logger.info(f"Detected resolution: {self.resolution}")

        # Email settings
        self._init_email_settings()

    def set_progress_callback(self, callback_func):
        self.progress_callback = callback_func

    def set_credit_manager(self, credit_manager):
        self.credit_manager = credit_manager
        self.logger.info("Credit manager has been set.")

    def _init_email_settings(self):
        """이메일 설정 초기화 (wf_rpa_config.json에서 로드)"""
        self.user_email = None
        self.report_email = None
        try:
            config_file = common_path / "config" / "wf_rpa_config.json"
            if config_file.exists():
                import json
                with open(config_file, 'r', encoding='utf-8') as f:
                    rpa_config = json.load(f)
                self.user_email = rpa_config.get('user_email')
                self.report_email = rpa_config.get('report_email')
                self.logger.info(f"Email settings loaded: user={self.user_email}, report={self.report_email}")
        except Exception as e:
            self.logger.warning(f"Failed to load email settings: {e}")

    def handle_error(self, error, context="", mail_title_prefix="[AR] [Error]", send_email=True):
        """에러 처리 및 이메일 알림"""
        error_msg = f"{context}: {error}" if context else str(error)
        self.logger.error(error_msg)

        screenshot_path = None
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_dir = Path(__file__).parent / "logs"
            screenshot_dir.mkdir(exist_ok=True)
            screenshot_path = screenshot_dir / f"error_{timestamp}.png"
            pyautogui.screenshot(str(screenshot_path))
            self.logger.info(f"Screenshot saved: {screenshot_path}")
        except Exception as e:
            self.logger.warning(f"Screenshot failed: {e}")

        if send_email and send_error_email and self.user_email:
            try:
                import traceback
                full_error = f"{error_msg}\n\nTraceback:\n{traceback.format_exc()}"
                send_error_email(
                    to_email=self.user_email,
                    subject=f"{mail_title_prefix} {context[:30] if context else 'Error'}",
                    error_message=full_error,
                    screenshot_path=str(screenshot_path) if screenshot_path and screenshot_path.exists() else None
                )
                self.logger.info("Error email sent successfully")
            except Exception as e:
                self.logger.warning(f"Failed to send error email: {e}")

    def send_completion_email(self, total_folders: int, processed_count: int, skipped_count: int):
        """완료 이메일 발송"""
        if not wf_send_completion or not self.user_email:
            self.logger.info("Completion email skipped (disabled or no email)")
            return

        try:
            body = f"""Attribute Reset 작업이 완료되었습니다.

처리 결과:
- 전체 폴더: {total_folders}개
- 처리 완료: {processed_count}개
- 스킵: {skipped_count}개

완료 시각: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            wf_send_completion(
                to_email=self.user_email,
                subject=f"[AR] Attribute Reset 완료 - {processed_count}/{total_folders}",
                body=body
            )
            self.logger.info("Completion email sent successfully")
        except Exception as e:
            self.logger.warning(f"Failed to send completion email: {e}")

    def update_progress(self, current, total, status_text=""):
        if self.progress_callback:
            try:
                self.master.after(0, lambda: self.progress_callback(current, total, status_text))
            except:
                 self.progress_callback(current, total, status_text)

    def connect_to_solidworks(self):
        """Connect to or start SOLIDWORKS application."""
        try:
            self.logger.info("Connecting to SOLIDWORKS...")
            self.app = Application(backend='uia').connect(title_re=self.config.solidworks.application_title, timeout=10)
            self.logger.info("Successfully connected to existing SOLIDWORKS instance.")
        except Exception:
            self.logger.info("No running SOLIDWORKS instance found. Starting a new one...")
            self.app = Application(backend='uia').start(self.config.solidworks.program_path)
            time.sleep(30)
            self.app = Application(backend='uia').connect(title_re=self.config.solidworks.application_title, timeout=30)
            self.logger.info("Successfully started and connected to SOLIDWORKS.")
        
        self.dlg = self.app.window(title_re=self.config.solidworks.application_title)
        self.dlg.set_focus()
        return self.app, self.dlg
        
    def delete_row_by_element(self):
        """Deletes all attribute rows using UI elements."""
        time.sleep(self.config.runtime_config.short_sleep)
        try:
            self.dlg.child_window(title="속성 이름", auto_id="PropNameCol", control_type="HeaderItem").wait('visible', timeout=5)
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(self.config.runtime_config.short_sleep)
            self.dlg.child_window(title="삭제(D)", auto_id="2016", control_type="Button").click_input()
            self.logger.info("Clicked delete button for attributes.")
            time.sleep(self.config.runtime_config.short_sleep)
            confirm_button = self.dlg.child_window(title='확인', auto_id="18294", control_type="Button")
            if confirm_button.exists():
                confirm_button.click_input()
                self.logger.info("Confirmed attribute deletion.")
        except Exception:
            self.logger.warning("Could not delete attribute rows, they may already be empty.")

    def clear_existing_attribute_by_element(self):
        """Clears attributes from both 'Custom' and 'Configuration Specific' tabs."""
        try:
            self.dlg.child_window(title="파일 속성", control_type="Button").click_input()
            time.sleep(self.config.runtime_config.mid_sleep)
            self.dlg.child_window(title='사용자 정의', control_type='TabItem').click_input()
            self.delete_row_by_element()
            self.dlg.child_window(title='설정 특정', control_type='TabItem').click_input()
            self.delete_row_by_element()
            self.dlg.child_window(title='확인', auto_id='1', control_type='Button').click_input()
            self.logger.info("Cleared existing attributes.")
        except Exception as e:
            self.logger.error(f"Failed to clear existing attributes: {e}")
            pyautogui.press('esc', presses=3, interval=0.5)

    def operate_by_element(self, target_dir, target_files, attribute_data):
        self.logger.info(f"Running 'operate_by_element' for {len(target_files)} files in {target_dir}.")
        makerNameValue, listCategoryText, itemNameKorValue, itemNameEngValue = "", "", "", ""
        if len(attribute_data) > 8:
            makerNameValue = attribute_data[5]
            listCategoryText = attribute_data[6]
            itemNameKorValue = attribute_data[7]
            itemNameEngValue = attribute_data[8]
        else:
            self.logger.error("Attribute data from Excel is incomplete.")
            return

        for index, file in enumerate(target_files):
            if self.stop_flag:
                self.logger.info("Stop flag is set, aborting process.")
                break
            
            self.update_progress(index, len(target_files), f"Processing {os.path.basename(file)}")
            self.dlg.set_focus()
            full_path = os.path.join(target_dir, file)
            self.logger.info(f"Opening file: {full_path}")

            try:
                pyautogui.hotkey('ctrl', 'o')
                time.sleep(self.config.runtime_config.short_sleep)
                pyperclip.copy(full_path)
                pyautogui.hotkey('ctrl', 'v')
                self.dlg.child_window(title="열기", auto_id="1", control_type="SplitButton").click_input()
                time.sleep(self.config.runtime_config.long_sleep)
                self.clear_existing_attribute_by_element()
                self.dlg.child_window(title="파일 속성", control_type="Button").click_input()
                time.sleep(self.config.runtime_config.mid_sleep)
                self.dlg.child_window(title='사용자 정의', control_type='TabItem').click_input()
                time.sleep(self.config.runtime_config.short_sleep)
                rbPurchase = self.dlg.child_window(title="구매품", auto_id="Radio2", control_type="RadioButton")
                rbPurchase.click()
                makerName = self.dlg.child_window(auto_id="TBRich", control_type="Document", found_index=0)
                listCategory = self.dlg.child_window(auto_id="CBCtrl", control_type="ComboBox")
                itemNameKor = self.dlg.child_window(auto_id="TBRich", control_type="Document", found_index=1)
                itemNameEng = self.dlg.child_window(auto_id="TBRich", control_type="Document", found_index=2)
                
                self.logger.info(f"Applying attributes - Maker: {makerNameValue}, Category: {listCategoryText}")
                makerName.type_keys('^a^c', set_foreground=False)
                pyperclip.copy(makerNameValue)
                pyautogui.hotkey('ctrl', 'v')
                listCategory.select(listCategoryText)
                itemNameKor.type_keys('^a^c', set_foreground=False)
                pyperclip.copy(itemNameKorValue)
                pyautogui.hotkey('ctrl', 'v')
                itemNameEng.type_keys('^a^c', set_foreground=False)
                pyperclip.copy(itemNameEngValue)
                pyautogui.hotkey('ctrl', 'v')

                self.dlg.child_window(auto_id="ApplyBtn", control_type="Button").click()
                time.sleep(self.config.runtime_config.short_sleep)
                self.dlg.click_input()
                pyautogui.hotkey('ctrl', 's')
                time.sleep(self.config.runtime_config.mid_sleep)
                pyautogui.hotkey('ctrl', 'w')
                time.sleep(self.config.runtime_config.short_sleep)
            except Exception as e:
                self.logger.error(f"Failed to process file {file}. Error: {e}")
                pyautogui.press('esc', presses=3, interval=0.5)
                continue
    
    def process_folders_from_excel(self, excel_path, master_tk=None):
        self.master = master_tk
        self.logger.info(f"Starting attribute reset process from excel: {excel_path}")
        
        if not self.app:
            self.connect_to_solidworks()

        try:
            df = pd.read_excel(excel_path, sheet_name='Sheet1', header=None)
            task_list = df.values.tolist()
        except Exception as e:
            self.logger.error(f"Failed to read Excel file: {e}")
            self.update_progress(1, 1, f"Error reading Excel: {e}")
            return

        total_folders = len(task_list)
        self.logger.info(f"Found {total_folders} folders to process.")

        for i, row in enumerate(task_list):
            if self.stop_flag:
                break

            if self.credit_manager:
                cost_per_folder = 1
                has_credit, reason = self.credit_manager.has_sufficient_credits(cost_per_folder)
                if not has_credit:
                    self.logger.error(f"Credit insufficient. Stopping process. Reason: {reason}")
                    self.update_progress(i, total_folders, f"크레딧 부족: {reason}")
                    break
                
                deduction_success, deduction_msg = self.credit_manager.deduct_credits(cost_per_folder)
                if not deduction_success:
                    self.logger.error(f"Credit deduction failed. Stopping process. Reason: {deduction_msg}")
                    self.update_progress(i, total_folders, f"크레딧 차감 실패: {deduction_msg}")
                    break
                self.logger.info(f"Deducted {cost_per_folder} credit(s).")
                
            folder_path = row[0]
            status_text = f"Folder {i+1}/{total_folders}: {os.path.basename(folder_path)}"
            self.update_progress(i, total_folders, status_text)
            
            if not os.path.isdir(folder_path):
                self.logger.warning(f"Folder not found, skipping: {folder_path}")
                continue

            file_list = [f for f in os.listdir(folder_path) if f.lower().endswith('.sldprt') and not f.startswith('~')]
            
            if file_list:
                attribute_data = row
                self.operate_by_element(folder_path, file_list, attribute_data)
            else:
                self.logger.info(f"No '.sldprt' files found in {folder_path}")
        
        self.update_progress(total_folders, total_folders, "Process finished.")
        self.logger.info("Attribute reset process completed.")

if __name__ == '__main__':
    automation = AttributeResetAutomation(console_mode=True)
    print("Automation script can be run in console mode for testing.")
    print("Provide a valid excel file path to 'process_folders_from_excel'.")


