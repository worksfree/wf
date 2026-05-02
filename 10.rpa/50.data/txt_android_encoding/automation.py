# -*- coding: utf-8 -*-
"""
Text Encoding Fixer Automation Module
"""

import os
import sys
from pathlib import Path
import logging

# 10.common 모듈 경로 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
common_path = os.path.abspath(os.path.join(current_dir, "..", "..", "10.common"))
if common_path not in sys.path:
    sys.path.insert(0, common_path)

from wf_log import get_app_logger

# chardet 라이브러리 import 시도
try:
    import chardet
    CHARDET_AVAILABLE = True
except ImportError:
    CHARDET_AVAILABLE = False
    _import_error = "chardet 라이브러리를 찾을 수 없습니다. 'pip install chardet'으로 설치해주세요."

class EncodingFixer:
    """텍스트 파일 인코딩 변환 자동화 클래스"""

    def __init__(self, log_callback=None, progress_callback=None):
        self.logger = get_app_logger("txt_android_encoding")
        self.log_callback = log_callback
        self.progress_callback = progress_callback
        self.was_cancelled = False

    def _log(self, message, level="info"):
        """로그 콜백 및 로거를 통해 메시지 전달"""
        if self.log_callback:
            self.log_callback(message)
        
        if hasattr(self.logger, level):
            getattr(self.logger, level)(message)

    def _update_progress(self, value):
        """진행률 콜백 호출"""
        if self.progress_callback:
            self.progress_callback(value)

    def cancel(self):
        """작업 취소"""
        self.was_cancelled = True
        self._log("사용자에 의해 작업이 취소되었습니다.", "warning")

    def run_conversion(self, folder_path: str):
        """지정된 폴더 내의 txt 파일 인코딩을 변환하는 메인 메서드"""
        if not CHARDET_AVAILABLE:
            self._log(_import_error, "error")
            self._update_progress(100)
            return

        self.was_cancelled = False
        self._log(f"폴더 스캔 시작: {folder_path}", "info")
        
        try:
            p = Path(folder_path)
            if not p.is_dir():
                self._log(f"오류: 유효한 폴더가 아닙니다: {folder_path}", "error")
                return

            # 변환 대상 파일 목록 생성
            files_to_process = list(p.rglob("*.txt"))
            total_files = len(files_to_process)
            
            if total_files == 0:
                self._log("변환할 .txt 파일을 찾을 수 없습니다.", "warning")
                self._update_progress(100)
                return

            self._log(f"총 {total_files}개의 .txt 파일을 찾았습니다.")

            converted_count = 0
            skipped_count = 0

            for i, file_path in enumerate(files_to_process):
                if self.was_cancelled:
                    break
                
                progress = int((i / total_files) * 100)
                self._update_progress(progress)
                
                self._log(f"[{i+1}/{total_files}] 처리 중: {file_path.name}")

                try:
                    with open(file_path, "rb") as f:
                        raw_data = f.read()
                    
                    if not raw_data:
                        self._log(f"└ 파일이 비어 있어 건너뜁니다.", "debug")
                        skipped_count += 1
                        continue

                    # 인코딩 감지
                    result = chardet.detect(raw_data)
                    encoding = result["encoding"]
                    confidence = result["confidence"]

                    self._log(f"└ 감지된 인코딩: {encoding} (신뢰도: {confidence:.2f})", "debug")

                    # 변환이 필요한 경우 (UTF-8, ascii가 아니고, 신뢰도가 충분히 높은 경우)
                    if encoding and encoding.lower() not in ["utf-8", "ascii"] and confidence > 0.7:
                        decoded_content = raw_data.decode(encoding, errors='replace')
                        
                        with open(file_path, "w", encoding="utf-8") as f_out:
                            f_out.write(decoded_content)
                        
                        self._log(f"└ '{encoding}'에서 'utf-8'로 변환 완료", "info")
                        converted_count += 1
                    else:
                        self._log(f"└ 이미 'utf-8'이거나 신뢰도가 낮아 건너뜁니다.", "info")
                        skipped_count += 1

                except Exception as e:
                    self._log(f"└ 파일 처리 중 오류 발생: {e}", "error")
                    skipped_count += 1
            
            if self.was_cancelled:
                summary_message = f"작업이 중단되었습니다. (변환: {converted_count}, 건너뜀: {skipped_count})"
            else:
                self._update_progress(100)
                summary_message = f"작업 완료! 총 {total_files}개 파일 중 {converted_count}개 변환, {skipped_count}개 건너뜀."
            
            self._log(summary_message, "info")

        except Exception as e:
            self._log(f"전체 작업 중 심각한 오류 발생: {e}", "error")

if __name__ == '__main__':
    # 간단한 테스트 로직
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
    
    def log_to_console(msg):
        logging.info(msg)
        
    def progress_update(val):
        logging.info(f"진행률: {val}%")

    # 테스트용 폴더와 파일을 생성
    test_dir = Path("./encoding_test_folder")
    test_dir.mkdir(exist_ok=True)
    
    (test_dir / "euc_kr_file.txt").write_text("안녕하세요", encoding="euc-kr")
    (test_dir / "utf8_file.txt").write_text("반갑습니다", encoding="utf-8")
    (test_dir / "empty_file.txt").write_text("", encoding="utf-8")
    
    print("-" * 20)
    print(f"테스트 폴더: {test_dir.resolve()}")
    print("-" * 20)
    
    fixer = EncodingFixer(log_callback=log_to_console, progress_callback=progress_update)
    fixer.run_conversion(str(test_dir))
    
    print("-" * 20)
    print("테스트 완료. 파일 인코딩 확인:")
    for f in test_dir.glob("*.txt"):
        with open(f, 'rb') as fp:
            print(f" - {f.name}: {chardet.detect(fp.read())}")
