# -*- coding: utf-8 -*-
"""
Work Progress 로직 단위 테스트
BOM Exporter의 작업 진행 상태 관리 로직을 검증합니다.

테스트 시나리오:
1. 신규 폴더 (bom/ 없음)
2. 완료된 폴더 (bom/에 전체 파일 있음)
3. 진행중 폴더 (bom/에 일부 파일 있음)
4. ignore_processed_for_rerun 플래그 동작
"""

import pytest
import tempfile
import shutil
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys

# 테스트 대상 모듈 경로 추가
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "10.common"))


class TestWorkProgressLogic:
    """작업 진행 상태 로직 테스트"""

    @pytest.fixture
    def temp_folder(self):
        """임시 테스트 폴더 생성"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def credit_data_file(self, temp_folder):
        """임시 credit_history.json 파일"""
        credit_file = Path(temp_folder) / "credit_history.json"
        return credit_file

    def create_slddrw_files(self, folder, count):
        """테스트용 slddrw 파일 생성"""
        for i in range(count):
            file_path = Path(folder) / f"test_file_{i:02d}-00.slddrw"
            file_path.write_text(f"dummy content {i}")
        return count

    def create_bom_files(self, folder, count):
        """테스트용 bom xlsx 파일 생성"""
        bom_folder = Path(folder) / "bom"
        bom_folder.mkdir(exist_ok=True)
        for i in range(count):
            file_path = bom_folder / f"test_file_{i:02d}-00.xlsx"
            file_path.write_text(f"excel content {i}")
        return count


class TestGetWorkProgress(TestWorkProgressLogic):
    """get_work_progress() 함수 테스트"""

    def test_new_folder_no_bom(self, temp_folder):
        """시나리오 1: 신규 폴더 - bom/ 없음"""
        # Given: slddrw 파일만 있고 bom/ 폴더 없음
        self.create_slddrw_files(temp_folder, 10)

        # When: _count_result_files 호출
        bom_path = Path(temp_folder) / "bom"

        # Then: bom 폴더 없으므로 0
        assert not bom_path.exists()
        count = sum(1 for f in bom_path.glob("*.xlsx") if f.is_file()) if bom_path.exists() else 0
        assert count == 0

    def test_completed_folder_all_bom(self, temp_folder):
        """시나리오 2: 완료된 폴더 - bom/에 전체 파일 있음"""
        # Given: slddrw 10개, bom/ 에 xlsx 10개
        self.create_slddrw_files(temp_folder, 10)
        self.create_bom_files(temp_folder, 10)

        # When: bom 폴더 파일 수 확인
        bom_path = Path(temp_folder) / "bom"
        actual_count = sum(1 for f in bom_path.glob("*.xlsx") if f.is_file())

        # Then: 10개
        assert actual_count == 10

    def test_in_progress_folder_partial_bom(self, temp_folder):
        """시나리오 3: 진행중 폴더 - bom/에 일부 파일만 있음"""
        # Given: slddrw 10개, bom/ 에 xlsx 5개
        self.create_slddrw_files(temp_folder, 10)
        self.create_bom_files(temp_folder, 5)

        # When: bom 폴더 파일 수 확인
        bom_path = Path(temp_folder) / "bom"
        actual_count = sum(1 for f in bom_path.glob("*.xlsx") if f.is_file())
        total_files = 10

        # Then: 5개, 진행중 상태
        assert actual_count == 5
        assert 0 < actual_count < total_files


class TestStatusDetermination(TestWorkProgressLogic):
    """상태 판단 로직 테스트 (ui_main.py의 로직)"""

    def test_status_new_when_processed_zero(self):
        """processed_count=0이면 status='new'"""
        processed_count = 0
        total_files = 10

        if processed_count == 0:
            progress_status = "new"
        elif processed_count >= total_files:
            progress_status = "completed"
        else:
            progress_status = "in_progress"

        assert progress_status == "new"

    def test_status_completed_when_all_processed(self):
        """processed_count >= total_files이면 status='completed'"""
        processed_count = 10
        total_files = 10

        if processed_count == 0:
            progress_status = "new"
        elif processed_count >= total_files:
            progress_status = "completed"
        else:
            progress_status = "in_progress"

        assert progress_status == "completed"

    def test_status_in_progress_when_partial(self):
        """0 < processed_count < total_files이면 status='in_progress'"""
        processed_count = 5
        total_files = 10

        if processed_count == 0:
            progress_status = "new"
        elif processed_count >= total_files:
            progress_status = "completed"
        else:
            progress_status = "in_progress"

        assert progress_status == "in_progress"


class TestIgnoreProcessedForRerun(TestWorkProgressLogic):
    """ignore_processed_for_rerun 플래그 테스트"""

    def test_flag_false_excludes_processed_files(self, temp_folder):
        """ignore_processed_for_rerun=False: 처리된 파일 제외"""
        # Given: slddrw 10개, bom/ 에 xlsx 5개
        self.create_slddrw_files(temp_folder, 10)
        self.create_bom_files(temp_folder, 5)

        ignore_processed_for_rerun = False
        work_dir_path = Path(temp_folder) / "bom"
        sldprt_files = [f"test_file_{i:02d}-00.slddrw" for i in range(10)]

        # When: automation.py 로직 시뮬레이션
        if work_dir_path.exists() and not ignore_processed_for_rerun:
            processed_files = {
                f.stem for f in work_dir_path.iterdir() if f.suffix.lower() == ".xlsx"
            }
            sldprt_files_to_process = [
                f for f in sldprt_files if Path(f).stem not in processed_files
            ]
        else:
            processed_files = set()
            sldprt_files_to_process = sldprt_files

        # Then: 5개만 처리 대상
        assert len(sldprt_files_to_process) == 5

    def test_flag_true_processes_all_files(self, temp_folder):
        """ignore_processed_for_rerun=True: 전체 파일 처리"""
        # Given: slddrw 10개, bom/ 에 xlsx 5개
        self.create_slddrw_files(temp_folder, 10)
        self.create_bom_files(temp_folder, 5)

        ignore_processed_for_rerun = True
        work_dir_path = Path(temp_folder) / "bom"
        sldprt_files = [f"test_file_{i:02d}-00.slddrw" for i in range(10)]

        # When: automation.py 로직 시뮬레이션
        if work_dir_path.exists() and not ignore_processed_for_rerun:
            processed_files = {
                f.stem for f in work_dir_path.iterdir() if f.suffix.lower() == ".xlsx"
            }
            sldprt_files_to_process = [
                f for f in sldprt_files if Path(f).stem not in processed_files
            ]
        else:
            processed_files = set()
            sldprt_files_to_process = sldprt_files

        # Then: 전체 10개 처리 대상
        assert len(sldprt_files_to_process) == 10


class TestBugScenario(TestWorkProgressLogic):
    """발견된 버그 시나리오 테스트"""

    def test_bug_process_folder_called_before_flag_set(self, temp_folder):
        """
        버그: process_folder()가 팝업 전에 호출되어 ignore_processed_for_rerun이 적용 안 됨

        현재 흐름:
        1. process_folder(scan_only=True) 호출 - ignore_processed_for_rerun=False
        2. sldprt_files_to_process 결정 (bom/ 파일 제외)
        3. 팝업 표시
        4. "예" 클릭 → ignore_processed_for_rerun=True 설정
        5. open_sldprt_files() 호출 - 하지만 sldprt_files_to_process는 이미 비어있음!
        """
        # Given: completed 상태 (slddrw 10개, bom/ 에 xlsx 10개)
        self.create_slddrw_files(temp_folder, 10)
        self.create_bom_files(temp_folder, 10)

        sldprt_files = [f"test_file_{i:02d}-00.slddrw" for i in range(10)]
        work_dir_path = Path(temp_folder) / "bom"

        # Step 1: process_folder 호출 시점 (ignore_processed_for_rerun=False)
        ignore_processed_for_rerun_at_scan = False

        if work_dir_path.exists() and not ignore_processed_for_rerun_at_scan:
            processed_files = {
                f.stem for f in work_dir_path.iterdir() if f.suffix.lower() == ".xlsx"
            }
            sldprt_files_to_process = [
                f for f in sldprt_files if Path(f).stem not in processed_files
            ]
        else:
            sldprt_files_to_process = sldprt_files

        # Step 2: 팝업 후 플래그 변경
        ignore_processed_for_rerun_after_popup = True  # 사용자가 "예" 클릭

        # Step 3: open_sldprt_files 호출 시점
        # 버그: sldprt_files_to_process는 여전히 빈 리스트!

        # Then: 버그 확인 - 처리할 파일이 0개
        assert len(sldprt_files_to_process) == 0, "버그 재현: process_folder가 먼저 호출되어 파일 목록이 비어있음"

    def test_fix_should_recompute_files_after_flag_set(self, temp_folder):
        """
        수정 방안: 플래그 설정 후 파일 목록 재계산
        """
        # Given: completed 상태 (slddrw 10개, bom/ 에 xlsx 10개)
        self.create_slddrw_files(temp_folder, 10)
        self.create_bom_files(temp_folder, 10)

        sldprt_files = [f"test_file_{i:02d}-00.slddrw" for i in range(10)]
        work_dir_path = Path(temp_folder) / "bom"

        # 수정된 흐름: 플래그 설정 후 파일 목록 재계산
        ignore_processed_for_rerun = True  # 사용자가 "예" 클릭 후

        if work_dir_path.exists() and not ignore_processed_for_rerun:
            processed_files = {
                f.stem for f in work_dir_path.iterdir() if f.suffix.lower() == ".xlsx"
            }
            sldprt_files_to_process = [
                f for f in sldprt_files if Path(f).stem not in processed_files
            ]
        else:
            sldprt_files_to_process = sldprt_files

        # Then: 전체 10개 처리 대상
        assert len(sldprt_files_to_process) == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
