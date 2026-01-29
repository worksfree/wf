# -*- coding: utf-8 -*-
"""
FilenameNormalizer Automation Module
한글 파일명 정규화 핵심 로직을 담당하는 모듈
"""

import os
import sys
import unicodedata
from pathlib import Path
import shutil
import time
import argparse

# 현재 스크립트의 디렉토리를 Python 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# 10.common 경로 추가
common_path = os.path.abspath(os.path.join(current_dir, "..", "..", "10.common"))
if common_path not in sys.path:
    sys.path.insert(0, common_path)

# 로컬 모듈 import
from app_setting_data import get_config

# 이메일 모듈 import
try:
    import wf_email as wfm
except ImportError:
    wfm = None


from datetime import datetime


class KoreanNormalizer:
    """한글 파일명 정규화 엔진"""

    def __init__(self, config=None, log_callback=None):
        self.config = config or get_config()
        self.log_callback = log_callback or self.default_log_callback

        # 이메일 설정 (에러/완료 알림용)
        self.itself_dir = current_dir
        self.user_email = ""
        self.report_email = ""

        # 로그 디렉토리 설정
        run_mode = os.environ.get("WF_RPA_MODE", "release")
        if run_mode in ("dev", "demo"):
            log_dir_path = Path(current_dir) / "logs"
        else:
            log_dir_path = Path.home() / ".wf_rpa" / "korean_filename_normalizer" / "logs"
        log_dir_path.mkdir(parents=True, exist_ok=True)
        self.log_dir = str(log_dir_path).replace("\\", "/")
        self.logfile = str(log_dir_path / f"{time.strftime('%Y%m%d')}.txt").replace("\\", "/")

        # 이메일 설정 초기화
        self._init_email_settings()

        # 한글 자모 정의
        self.CHOSEONG = [
            "ㄱ",
            "ㄲ",
            "ㄴ",
            "ㄷ",
            "ㄸ",
            "ㄹ",
            "ㅁ",
            "ㅂ",
            "ㅃ",
            "ㅅ",
            "ㅆ",
            "ㅇ",
            "ㅈ",
            "ㅉ",
            "ㅊ",
            "ㅋ",
            "ㅌ",
            "ㅍ",
            "ㅎ",
        ]
        self.JUNGSEONG = [
            "ㅏ",
            "ㅐ",
            "ㅑ",
            "ㅒ",
            "ㅓ",
            "ㅔ",
            "ㅕ",
            "ㅖ",
            "ㅗ",
            "ㅘ",
            "ㅙ",
            "ㅚ",
            "ㅛ",
            "ㅜ",
            "ㅝ",
            "ㅞ",
            "ㅟ",
            "ㅠ",
            "ㅡ",
            "ㅢ",
            "ㅣ",
        ]
        self.JONGSEONG = [
            "",
            "ㄱ",
            "ㄲ",
            "ㄳ",
            "ㄴ",
            "ㄵ",
            "ㄶ",
            "ㄷ",
            "ㄹ",
            "ㄺ",
            "ㄻ",
            "ㄼ",
            "ㄽ",
            "ㄾ",
            "ㄿ",
            "ㅀ",
            "ㅁ",
            "ㅂ",
            "ㅄ",
            "ㅅ",
            "ㅆ",
            "ㅇ",
            "ㅈ",
            "ㅊ",
            "ㅋ",
            "ㅌ",
            "ㅍ",
            "ㅎ",
        ]

    def _init_email_settings(self):
        """이메일 설정 초기화 (wf_rpa_config.json에서 로드)"""
        try:
            import json
            config_file = Path.home() / ".wf_rpa" / "wf_rpa_config.json"

            if config_file.exists():
                with open(config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)

                # 사용자 이메일
                self.user_email = config.get("user_info", {}).get("user_email", "")

                # 리포트 수신 이메일
                email_settings = config.get("email_settings", {})
                self.report_email = email_settings.get("email_to", "")

                # report_email이 없으면 user_email로 폴백
                if not self.report_email:
                    self.report_email = self.user_email

        except Exception as e:
            self.log_callback(f"이메일 설정 로드 실패: {e}")

    def handle_error(self, error, context="", mail_title_prefix="[KFN] [Error]", send_email=True):
        """공통 에러 처리: 스크린샷 저장 및 이메일 전송

        Args:
            error: 발생한 예외 또는 에러 메시지
            context: 에러 발생 컨텍스트 (파일명, 단계 등)
            mail_title_prefix: 이메일 제목 접두사
            send_email: 이메일 전송 여부 (기본값: True)

        Returns:
            tuple: (screenshot_path, timestamp) - 스크린샷 경로와 타임스탬프
        """
        timestamp4img = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 스크린샷 캡처
        screenshot_path = None
        try:
            import pyautogui
            screenshot = pyautogui.screenshot()
            screenshot_path = Path(self.log_dir) / f"{timestamp4img}.png"
            screenshot.save(str(screenshot_path))
            self.log_callback(f"스크린샷 저장: {screenshot_path}")
        except Exception as e:
            self.log_callback(f"스크린샷 캡처 실패: {e}")

        # 이메일 전송
        if send_email and wfm and self.report_email and hasattr(wfm, 'mail_send_attach'):
            error_content = f"{str(error)}"
            if context:
                error_content = f"{error_content}\n{context}"

            attach = []
            if screenshot_path:
                attach.append(str(screenshot_path).replace("\\", "/"))
            attach.append(self.logfile)

            try:
                wfm.init(self.itself_dir)
                mail_title = f"{mail_title_prefix} {self.user_email}"
                wfm.mail_send_attach(mail_title, self.report_email, error_content, attach)
                self.log_callback("에러 이메일 전송 완료")
            except Exception as mail_e:
                self.log_callback(f"에러 이메일 전송 실패: {mail_e}")

        return str(screenshot_path) if screenshot_path else None, timestamp4img

    def send_completion_email(self, total_count: int, normalized_count: int, skipped_count: int):
        """작업 완료 이메일 전송

        Args:
            total_count: 전체 파일 수
            normalized_count: 정규화 파일 수
            skipped_count: 건너뛴 파일 수
        """
        if not wfm or not self.report_email or not hasattr(wfm, 'mail_send_attach'):
            self.log_callback("이메일 전송 건너뜀 (설정 없음)")
            return

        try:
            wfm.init(self.itself_dir)
            mail_title = f"[KFN] [Complete] {self.user_email}"
            content = (
                f"파일명 정규화 완료\n\n"
                f"• 전체: {total_count}개\n"
                f"• 정규화: {normalized_count}개\n"
                f"• 건너뜀: {skipped_count}개\n"
            )
            attach = [self.logfile]
            wfm.mail_send_attach(mail_title, self.report_email, content, attach)
            self.log_callback("완료 이메일 전송 완료")
        except Exception as e:
            self.log_callback(f"완료 이메일 전송 실패: {e}")

    def default_log_callback(self, message):
        """기본 로그 콜백"""
        print(f"[LOG] {message}")

    def normalize_korean_filename(self, filename):
        """개선된 한글 파일명 정규화 함수"""
        normalization_method = self.config.get("normalization_method", "nfc_plus_manual")

        if normalization_method == "nfc_only":
            # NFC 정규화만 사용
            normalized = unicodedata.normalize("NFC", filename)
        elif normalization_method == "manual_only":
            # 수동 자모 조합만 사용
            normalized = self.manual_jamo_combination(filename)
        else:
            # NFC + 수동 조합 (기본값)
            # 1단계: 유니코드 NFC 정규화 (가장 기본적이고 효과적)
            normalized = unicodedata.normalize("NFC", filename)

            # 2단계: 추가 정규화가 필요한지 확인
            if normalized != filename:
                self.log_callback(f"NFC 정규화: {filename} → {normalized}")

            # 3단계: 여전히 자모가 분리되어 있다면 수동 매핑
            if self.has_separated_jamo(normalized):
                normalized = self.manual_jamo_combination(normalized)

        # 확장자 대소문자 보존 설정 적용
        if self.config.get("preserve_extension_case", True):
            original_ext = Path(filename).suffix
            if original_ext:
                normalized_path = Path(normalized)
                normalized = str(normalized_path.with_suffix(original_ext))

        return normalized

    def has_separated_jamo(self, text):
        """분리된 자모가 여전히 있는지 확인"""
        for char in text:
            if "\u3131" <= char <= "\u318e":  # 한글 호환 자모
                return True
            if "\u1100" <= char <= "\u11ff":  # 한글 자모
                return True
        return False

    def manual_jamo_combination(self, text):
        """수동 자모 결합 - 완전한 한글 조합 로직"""
        result = []
        i = 0
        while i < len(text):
            char = text[i]

            # 자모가 아닌 경우 그대로 추가
            if (
                char not in self.CHOSEONG
                and char not in self.JUNGSEONG
                and char not in self.JONGSEONG[1:]
            ):
                result.append(char)
                i += 1
                continue

            # 초성 확인
            if char in self.CHOSEONG:
                cho_idx = self.CHOSEONG.index(char)
                i += 1

                # 중성 확인
                if i < len(text) and text[i] in self.JUNGSEONG:
                    jung_idx = self.JUNGSEONG.index(text[i])
                    i += 1

                    # 종성 확인
                    jong_idx = 0  # 기본값 (종성 없음)
                    if i < len(text) and text[i] in self.JONGSEONG[1:]:  # 빈 문자열 제외
                        jong_idx = self.JONGSEONG.index(text[i])
                        i += 1

                    # 완성형 한글 문자 생성
                    hangul_code = 0xAC00 + (cho_idx * 21 * 28) + (jung_idx * 28) + jong_idx
                    result.append(chr(hangul_code))
                else:
                    # 중성이 없으면 그대로 추가
                    result.append(char)
            else:
                # 초성이 아닌 자모는 그대로 추가
                result.append(char)
                i += 1

        combined = "".join(result)
        if combined != text:
            self.log_callback(f"자모 조합: {text} → {combined}")

        return combined

    def is_korean_decomposed(self, filename):
        """한글 파일명이 자소 분리되어 있는지 확인"""
        # 1차: NFC 정규화 후 비교
        normalized = unicodedata.normalize("NFC", filename)
        if normalized != filename:
            return True

        # 2차: 분리된 자모 직접 확인
        return self.has_separated_jamo(filename)

    def log_unicode_info(self, filename, max_chars=20):
        """파일명의 유니코드 정보를 로그에 출력 (디버깅용)"""
        info_parts = []
        for i, char in enumerate(filename[:max_chars]):
            try:
                char_name = unicodedata.name(char, f"U+{ord(char):04X}")
                info_parts.append(f"'{char}'({char_name})")
            except:
                info_parts.append(f"'{char}'(U+{ord(char):04X})")

        if len(filename) > max_chars:
            info_parts.append("...")

        self.log_callback(f"  유니코드 정보: {' '.join(info_parts[:10])}")


class FilenameProcessor:
    """파일명 처리 및 변환 클래스"""

    def __init__(self, config=None, log_callback=None, progress_callback=None):
        self.config = config or get_config()
        self.log_callback = log_callback or self.default_log_callback
        self.progress_callback = progress_callback or self.default_progress_callback

        self.normalizer = KoreanNormalizer(config, log_callback)
        self.target_files = []
        self.conflicts = []
        self.backup_info = []

    def default_log_callback(self, message):
        """기본 로그 콜백"""
        print(f"[LOG] {message}")

    def default_progress_callback(self, value, status):
        """기본 진행률 콜백"""
        print(f"[PROGRESS] {value}% - {status}")

    def find_decomposed_files(self, folder_path):
        """폴더에서 자소 분리된 한글 파일명을 찾음"""
        self.target_files = []
        folder = Path(folder_path)

        if not folder.exists():
            raise FileNotFoundError(f"폴더가 존재하지 않습니다: {folder_path}")

        if not folder.is_dir():
            raise NotADirectoryError(f"지정된 경로가 폴더가 아닙니다: {folder_path}")

        self.log_callback(f"폴더 검사 중: {folder_path}")

        # 보류 목록 확인 (세션 재개용)
        pending_path = folder / "wf_pending_list.txt"
        pending_names = set()
        if pending_path.exists():
            try:
                with open(pending_path, "r", encoding="utf-8") as pf:
                    for line in pf:
                        name = line.strip()
                        if name:
                            pending_names.add(name.lower())
                if pending_names:
                    self.log_callback(f"보류 목록 발견: {len(pending_names)}개 파일")
            except Exception as pe:
                self.log_callback(f"보류 목록 읽기 실패, 전체 스캔 진행: {pe}")

        # 파일 목록 수집
        if self.config.get("recursive_scan", True):
            all_files = list(folder.rglob("*"))
        else:
            all_files = list(folder.iterdir())

        files_only = [f for f in all_files if f.is_file()]

        # 보류 목록이 있으면 해당 파일만 필터링
        if pending_names:
            files_only = [f for f in files_only if f.name.lower() in pending_names]
            self.log_callback(f"보류 목록에서 {len(files_only)}개 파일 로드")

        # 숨김 파일 처리
        if not self.config.get("include_hidden_files", False):
            files_only = [f for f in files_only if not f.name.startswith(".")]

        # 시스템 파일 건너뛰기
        if self.config.get("skip_system_files", True):
            system_files = ["Thumbs.db", "desktop.ini", ".DS_Store"]
            files_only = [f for f in files_only if f.name not in system_files]

        total_files = len(files_only)
        self.log_callback(f"총 {total_files}개 파일을 검사합니다.")

        processed = 0
        for file_path in files_only:
            filename = file_path.name

            self.log_callback(f"검사 중: {filename}")

            if self.normalizer.is_korean_decomposed(filename):
                normalized_name = self.normalizer.normalize_korean_filename(filename)
                self.target_files.append(
                    {
                        "original_path": file_path,
                        "original_name": filename,
                        "normalized_name": normalized_name,
                        "parent_dir": file_path.parent,
                    }
                )
                self.log_callback(f"자소 분리 파일 발견: {filename} → {normalized_name}")

            processed += 1
            if total_files > 0 and processed % 10 == 0:
                progress = (processed / total_files) * 90
                self.progress_callback(progress, f"검사 중... ({processed}/{total_files})")

        self.log_callback(f"자소 분리 파일 {len(self.target_files)}개 발견")
        return self.target_files

    def check_conflicts(self, base_folder_path):
        """변환 후 파일명 충돌 확인"""
        self.conflicts = []

        self.log_callback("파일명 충돌 검사 시작")

        base_folder = Path(base_folder_path)
        # save_to_new_folder 설정에 따라 저장 위치 결정
        if self.config.get("save_to_new_folder", True):
            result_folder = base_folder / "result"
        else:
            result_folder = base_folder

        for i, file_info in enumerate(self.target_files):
            # 원본 파일의 상대 경로 계산
            try:
                relative_path = file_info["parent_dir"].relative_to(base_folder)
                target_dir = result_folder / relative_path
            except ValueError:
                target_dir = result_folder

            # 저장 폴더 내에서의 새 파일 경로
            new_path = target_dir / file_info["normalized_name"]

            if new_path.exists():
                self.conflicts.append(
                    {
                        "original": file_info["original_path"],
                        "normalized_name": file_info["normalized_name"],
                        "conflict_path": new_path,
                    }
                )
                self.log_callback(f"파일명 충돌: {file_info['normalized_name']} (이미 존재)")

        if self.conflicts:
            self.log_callback(f"파일명 충돌 {len(self.conflicts)}개 발견")
        else:
            self.log_callback("파일명 충돌이 없습니다.")

        return self.conflicts

    def execute_conversion(self, base_folder_path):
        """파일 변환 실행"""
        if not self.target_files:
            raise ValueError("변환할 파일이 없습니다. 먼저 대상 확인을 실행하세요.")

        base_folder = Path(base_folder_path)
        
        # 파일 처리 방식 확인
        operation_mode = self.config.get("file_operation_mode", "copy")
        
        # save_to_new_folder 설정에 따라 저장 위치 결정
        if self.config.get("save_to_new_folder", True):
            result_folder = base_folder / "result"
        else:
            result_folder = base_folder
        backup_folder = base_folder / "backup"

        # 백업 폴더 생성
        if self.config.get("backup_enabled", True):
            backup_folder.mkdir(exist_ok=True)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            timestamped_backup = backup_folder / timestamp
            timestamped_backup.mkdir(exist_ok=True)

        # 저장 폴더 생성 (새 폴더 사용 시에만, copy 모드에만 필요)
        if operation_mode == "copy" and self.config.get("save_to_new_folder", True):
            result_folder.mkdir(exist_ok=True)

        total_files = len(self.target_files)
        mode_text = "원본 파일명 변경" if operation_mode == "rename" else "복원본 생성"
        self.log_callback(f"파일 변환 시작 ({mode_text}): {total_files}개 파일")

        for i, file_info in enumerate(self.target_files):
            try:
                original_path = file_info["original_path"]
                
                if operation_mode == "rename":
                    # 원본 파일명 변경 모드
                    target_dir = file_info["parent_dir"]
                    new_path = target_dir / file_info["normalized_name"]
                    
                    # 충돌 처리
                    if new_path.exists() and new_path != original_path:
                        conflict_resolution = self.config.get("conflict_resolution", "skip")
                        if conflict_resolution == "skip":
                            self.log_callback(f"건너뜀 (충돌): {file_info['original_name']}")
                            continue
                        elif conflict_resolution == "overwrite":
                            # 기존 파일 삭제 후 진행
                            new_path.unlink()
                    
                    # 백업 생성
                    if self.config.get("backup_enabled", True):
                        backup_path = timestamped_backup / original_path.name
                        shutil.copy2(original_path, backup_path)
                        self.backup_info.append({"original": original_path, "backup": backup_path})
                    
                    # 파일명 변경 (rename)
                    original_path.rename(new_path)
                    self.log_callback(f"변환 완료: {file_info['original_name']} → {file_info['normalized_name']}")
                    
                else:
                    # 복원본 별도 생성 모드 (copy)
                    # 상대 경로 계산
                    if self.config.get("save_to_new_folder", True):
                        # 새 폴더에 저장: 상대 경로 유지
                        try:
                            relative_path = file_info["parent_dir"].relative_to(base_folder)
                            target_dir = result_folder / relative_path
                        except ValueError:
                            target_dir = result_folder
                    else:
                        # 원본 폴더에 저장: 원본 위치 그대로
                        target_dir = file_info["parent_dir"]

                    # 대상 디렉토리 생성
                    target_dir.mkdir(parents=True, exist_ok=True)

                    # 새 파일 경로
                    new_path = target_dir / file_info["normalized_name"]

                    # 충돌 처리
                    if new_path.exists():
                        conflict_resolution = self.config.get("conflict_resolution", "auto_rename")
                        if conflict_resolution == "auto_rename":
                            new_path = self._get_unique_filename(new_path)
                        elif conflict_resolution == "skip":
                            self.log_callback(f"건너뜀 (충돌): {file_info['original_name']}")
                            continue
                        # overwrite는 그대로 진행

                    # 백업 생성
                    if self.config.get("backup_enabled", True):
                        backup_path = timestamped_backup / original_path.name
                        shutil.copy2(original_path, backup_path)
                        self.backup_info.append({"original": original_path, "backup": backup_path})

                    # 파일 복사
                    shutil.copy2(original_path, new_path)
                    self.log_callback(f"변환 완료: {file_info['original_name']} → {new_path.name}")

                # 사용 횟수 증가
                self.config.increment_usage()

            except Exception as e:
                self.log_callback(f"변환 실패: {file_info['original_name']} - {str(e)}")

            # 진행률 업데이트
            progress = ((i + 1) / total_files) * 100
            self.progress_callback(progress, f"변환 중... ({i + 1}/{total_files})")

        self.log_callback(f"변환 완료: {total_files}개 파일 처리")

        # 세션 재개 파일 목록 정리 (완료 시 제거)
        try:
            pending_path = base_folder / "wf_pending_list.txt"
            if pending_path.exists():
                try:
                    pending_path.unlink()
                    self.log_callback(f"보류 목록 삭제: {pending_path}")
                except Exception as ue:
                    self.log_callback(f"보류 목록 삭제 실패(무시): {ue}")
        except Exception as pe:
            self.log_callback(f"보류 목록 처리 중 경고(무시): {pe}")

        return True

    def _get_unique_filename(self, path):
        """중복되지 않는 파일명 생성"""
        base = path.stem
        ext = path.suffix
        parent = path.parent

        counter = 1
        while True:
            new_name = f"{base}_{counter}{ext}"
            new_path = parent / new_name
            if not new_path.exists():
                return new_path
            counter += 1

    def restore_from_backup(self, backup_timestamp=None):
        """백업에서 파일 복원"""
        base_folder = Path(self.config.get("default_folder_path", ""))
        backup_folder = base_folder / "backup"

        if backup_timestamp:
            restore_folder = backup_folder / backup_timestamp
        else:
            # 가장 최근 백업 찾기
            backup_dirs = [d for d in backup_folder.iterdir() if d.is_dir()]
            if not backup_dirs:
                raise FileNotFoundError("백업 폴더가 없습니다.")
            restore_folder = max(backup_dirs, key=lambda x: x.stat().st_mtime)

        if not restore_folder.exists():
            raise FileNotFoundError(f"백업 폴더를 찾을 수 없습니다: {restore_folder}")

        restored_count = 0
        for backup_file in restore_folder.iterdir():
            if backup_file.is_file():
                original_path = base_folder / backup_file.name
                try:
                    shutil.copy2(backup_file, original_path)
                    restored_count += 1
                    self.log_callback(f"복원: {backup_file.name}")
                except Exception as e:
                    self.log_callback(f"복원 실패: {backup_file.name} - {str(e)}")

        self.log_callback(f"복원 완료: {restored_count}개 파일")
        return restored_count


class TestFileGenerator:
    """테스트 파일 생성 클래스"""

    def __init__(self, log_callback=None):
        self.log_callback = log_callback or self.default_log_callback

    def default_log_callback(self, message):
        print(f"[TEST] {message}")

    def create_test_files(self, base_folder_path):
        """자소 분리 테스트 파일들 생성"""
        base_folder = Path(base_folder_path)
        test_folder = base_folder / "test_files"
        test_folder.mkdir(exist_ok=True)

        # 다양한 자소 분리 패턴 테스트 파일명들
        test_filenames = [
            "테ㅅㅌ_파ㅇ일1.txt",  # 기본 자소 분리
            "한ㄱㅡㄹ_문ㅅ서.docx",  # 복합 자소 분리
            "ㅅ장ㅍ서류_ㅊㅗ안.pdf",  # 혼합 패턴
            "회ㅇ의록_2024ㄴ년.xlsx",  # 숫자 포함
            "정ㄱ기_보ㄱ고서.pptx",  # 간단한 분리
        ]

        created_count = 0
        for filename in test_filenames:
            test_file = test_folder / filename
            try:
                test_file.write_text("테스트 파일입니다.", encoding="utf-8")
                self.log_callback(f"테스트 파일 생성: {filename}")
                created_count += 1
            except Exception as e:
                self.log_callback(f"테스트 파일 생성 실패: {filename} - {str(e)}")

        self.log_callback(f"테스트 파일 생성 완료: {created_count}개")
        return created_count


def run_cli_normalization(folder_path, verbose=False):
    """CLI 모드에서 정규화 실행"""
    config = get_config()

    def cli_log(message):
        if verbose:
            print(f"[LOG] {message}")

    def cli_progress(value, status):
        if verbose:
            print(f"[{value:3.0f}%] {status}")

    processor = FilenameProcessor(config, cli_log, cli_progress)

    try:
        # 파일 검사
        print("자소 분리 파일 검사 중...")
        target_files = processor.find_decomposed_files(folder_path)

        if not target_files:
            print("자소 분리된 파일이 없습니다.")
            return False

        print(f"\n발견된 자소 분리 파일: {len(target_files)}개")
        for file_info in target_files:
            print(f"  {file_info['original_name']} → {file_info['normalized_name']}")

        # 충돌 검사
        conflicts = processor.check_conflicts(folder_path)
        if conflicts:
            print(f"\n경고: {len(conflicts)}개 파일명 충돌 발견")
            for conflict in conflicts:
                print(f"  충돌: {conflict['normalized_name']}")

        # 변환 실행
        response = input("\n변환을 실행하시겠습니까? (y/N): ")
        if response.lower() in ["y", "yes"]:
            print("\n파일 변환 실행 중...")
            processor.execute_conversion(folder_path)
            print("변환 완료!")
            return True
        else:
            print("변환이 취소되었습니다.")
            return False

    except Exception as e:
        print(f"오류: {e}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="한글 파일명 자소 분리 수정 도구")
    parser.add_argument("folder", help="처리할 폴더 경로")
    parser.add_argument("-v", "--verbose", action="store_true", help="상세 출력")
    parser.add_argument("--test", action="store_true", help="테스트 파일 생성")

    args = parser.parse_args()

    if args.test:
        generator = TestFileGenerator()
        generator.create_test_files(args.folder)
    else:
        if os.path.exists(args.folder):
            run_cli_normalization(args.folder, args.verbose)
        else:
            print(f"오류: 폴더를 찾을 수 없습니다: {args.folder}")
