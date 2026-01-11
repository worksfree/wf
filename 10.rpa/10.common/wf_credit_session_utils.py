"""
크레딧 세션 관리 유틸리티
- 세션 통계 계산
- 진행률 라벨 포맷팅
- 팝업 메시지 생성
"""
from typing import Dict, Tuple, List, Any
import os


def calculate_processable_count(remaining_credits: int, cost_per_item: int) -> int:
    """현재 크레딧으로 처리 가능한 파일 개수 계산
    
    Args:
        remaining_credits: 보유 크레딧
        cost_per_item: 파일당 크레딧 비용
    
    Returns:
        처리 가능한 파일 개수
    """
    return remaining_credits // cost_per_item if cost_per_item > 0 else 0


def compute_session_stats(
    already_processed_count: int,
    current_processed: int,
    total_file_count: int
) -> Dict[str, int]:
    """세션 통계 계산
    
    Args:
        already_processed_count: 이미 처리된 파일 수
        current_processed: 이번 실행에서 처리한 파일 수
        total_file_count: 전체 파일 수
    
    Returns:
        {
            'cumulative_processed': 누적 처리 건수,
            'remaining': 남은 파일 수
        }
    """
    cumulative_processed = already_processed_count + current_processed
    remaining = max(0, total_file_count - cumulative_processed)
    
    return {
        'cumulative_processed': cumulative_processed,
        'remaining': remaining
    }


def format_progress_label(
    already_processed_count: int,
    current_processed: int,
    total_file_count: int,
    is_finished: bool = False
) -> str:
    """진행률 라벨 포맷팅
    
    Args:
        already_processed_count: 이미 처리된 파일 수
        current_processed: 이번 실행에서 처리한 파일 수
        total_file_count: 전체 파일 수
        is_finished: 작업 완료 여부
    
    Returns:
        포맷된 라벨 문자열
        - 초기(0/0): "0/45"
        - 처리 중: "15/45 (잔여 30건)"
        - 완료: "45/45 (완료)"
    """
    # 초기 상태 (아무것도 처리하지 않음)
    if already_processed_count == 0 and current_processed == 0:
        return f"{current_processed}/{total_file_count}"
    
    # 처리 중이거나 재시작 상황
    display_current = already_processed_count + current_processed
    remaining = max(0, total_file_count - display_current)
    
    if is_finished and remaining == 0:
        return f"{display_current}/{total_file_count} (완료)"
    else:
        if remaining > 0:
            return f"{display_current}/{total_file_count} (잔여 {remaining}건)"
        else:
            return f"{display_current}/{total_file_count} (완료)"


def build_credit_shortage_init_message(
    remaining_count: int,
    processable_count: int,
    needed_credits: int,
    remaining_credits: int,
    shortage_credits: int,
    allow_continue: bool
) -> str:
    """초기(분류 전) 크레딧 부족 메시지 생성
    
    Args:
        remaining_count: 처리할 파일 수 (이미 처리된 것 제외)
        processable_count: 현재 크레딧으로 처리 가능한 파일 수
        needed_credits: 필요 크레딧
        remaining_credits: 보유 크레딧
        shortage_credits: 부족 크레딧
        allow_continue: 계속 진행 허용 여부
    
    Returns:
        팝업 메시지 문자열
    """
    if allow_continue:
        msg = (
            f"현재 크레딧으로 총 {remaining_count}건 중 {processable_count}건만 처리될 수 있습니다.\n\n"
            f"필요 크레딧: {needed_credits} / 보유 크레딧: {remaining_credits}\n"
            f"부족 크레딧: {shortage_credits}\n\n"
            "그래도 진행하시겠습니까?"
        )
    else:
        msg = (
            f"크레딧 부족으로 실행할 수 없습니다.\n\n"
            f"현재 크레딧으로 총 {remaining_count}건 중 {processable_count}건만 처리 가능합니다.\n\n"
            f"필요 크레딧: {needed_credits} / 보유 크레딧: {remaining_credits}\n"
            f"부족 크레딧: {shortage_credits}\n\n"
            "크레딧을 구매한 후 다시 실행해 주세요."
        )
    return msg


def build_credit_shortage_completion_message(
    processed: int,
    already_processed_count: int,
    total_file_count: int,
    folder_stats: Dict[str, int],
    unclassified_count: int
) -> str:
    """작업 중 크레딧 부족으로 중단된 후 표시할 메시지
    
    Args:
        processed: 이번 실행에서 처리한 파일 수
        already_processed_count: 이미 처리된 파일 수
        total_file_count: 전체 파일 수
        folder_stats: 폴더별 분류 통계 {폴더명: 개수}
        unclassified_count: 미분류 파일 수
    
    Returns:
        팝업 메시지 문자열
    """
    stats = compute_session_stats(already_processed_count, processed, total_file_count)
    cumulative_processed = stats['cumulative_processed']
    remaining = stats['remaining']
    
    msg_lines = []
    msg_lines.append("분류 작업이 크레딧 부족으로 중단되었습니다.")
    msg_lines.append("")
    msg_lines.append(f"이번 실행: {processed}개 처리")
    msg_lines.append(f"누적 처리: {cumulative_processed}개 / 전체 {total_file_count}개")
    msg_lines.append(f"남은 파일: {remaining}개")
    msg_lines.append("")
    
    # 현재까지의 폴더별 분류 현황
    if folder_stats:
        msg_lines.append("📁 현재까지 분류된 현황:")
        sorted_folders = sorted(folder_stats.items(), key=lambda x: x[1], reverse=True)
        for folder_name, count in sorted_folders:
            msg_lines.append(f"  • {folder_name}: {count}개")
        if unclassified_count > 0:
            msg_lines.append(f"  • _미분류: {unclassified_count}개")
    
    msg_lines.append("")
    msg_lines.append("나머지 파일을 처리하려면")
    msg_lines.append("크레딧을 추가로 구매해야 합니다.")
    msg_lines.append("")
    msg_lines.append("지금 크레딧을 구매하시겠습니까?")
    
    return "\n".join(msg_lines)


def build_normal_completion_message(
    total: int,
    processed: int,
    failed: int,
    folder_stats: Dict[str, int],
    unclassified_count: int,
    unmatched_files: List[str] = None
) -> str:
    """정상 완료 팝업 메시지
    
    Args:
        total: 전체 파일 수
        processed: 처리 성공 파일 수
        failed: 처리 실패 파일 수
        folder_stats: 폴더별 분류 통계 {폴더명: 개수}
        unclassified_count: 미분류 파일 수
        unmatched_files: 엑셀에 없는 파일 목록 (선택사항)
    
    Returns:
        팝업 메시지 문자열
    """
    if unmatched_files is None:
        unmatched_files = []
    
    summary_lines = []
    summary_lines.append(f"전체 DWG 파일: {total}개")
    summary_lines.append(f"✅ 처리 성공: {processed}개")
    if failed > 0:
        summary_lines.append(f"❌ 처리 실패: {failed}개")
    summary_lines.append("")
    
    # 폴더별 분류 통계
    if folder_stats:
        summary_lines.append("📁 폴더별 분류 결과:")
        sorted_folders = sorted(folder_stats.items(), key=lambda x: x[1], reverse=True)
        for folder_name, count in sorted_folders:
            summary_lines.append(f"  • {folder_name}: {count}개")
    
    # 미분류 파일
    if unclassified_count > 0:
        summary_lines.append("")
        summary_lines.append(f"❓ 미분류 파일: {unclassified_count}개")
    
    # 엑셀에 없는 파일 (정상 완료 시만 표시)
    if unmatched_files:
        summary_lines.append("")
        summary_lines.append(f"⚠️ 엑셀에 없는 파일 {len(unmatched_files)}개를 '_미분류' 폴더로 처리했습니다:")
        for i, unmatched_file in enumerate(unmatched_files[:10]):
            filename = os.path.basename(unmatched_file)
            summary_lines.append(f"  • {filename}")
        if len(unmatched_files) > 10:
            summary_lines.append(f"  ... 외 {len(unmatched_files) - 10}개")
    
    return "\n".join(summary_lines)


def get_credit_purchase_url() -> str:
    """크레딧 구매 페이지 URL"""
    return "https://www.worksfree.co.kr/buy-credits"
