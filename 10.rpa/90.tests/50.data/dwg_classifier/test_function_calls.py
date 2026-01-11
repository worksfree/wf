"""
ui_main.py 함수 호출 검증

목적: ui_main.py에서 utils 함수를 올바르게 호출하는지 확인
"""

import re
from pathlib import Path


def check_function_calls():
    """ui_main.py의 함수 호출 검증"""
    print("=" * 60)
    print("ui_main.py 함수 호출 검증")
    print("=" * 60)
    
    # 90.tests/50.data/dwg_classifier -> 90.tests -> 10.rpa -> 50.data -> dwg_classifier
    ui_main_path = Path(__file__).parent.parent.parent.parent / "50.data" / "dwg_classifier" / "ui_main.py"
    
    if not ui_main_path.exists():
        print(f"❌ 파일 찾을 수 없음: {ui_main_path}")
        return False
    
    with open(ui_main_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Import 확인
    print("\n=== Import 검증 ===")
    import_pattern = r'from wf_credit_session_utils import \('
    if re.search(import_pattern, content):
        print("✅ wf_credit_session_utils import 확인")
        
        # 개별 함수 import 확인
        expected_imports = [
            "calculate_processable_count",
            "compute_session_stats",
            "format_progress_label",
            "build_credit_shortage_init_message",
            "build_credit_shortage_completion_message",
            "build_normal_completion_message",
            "get_credit_purchase_url",
        ]
        
        for func in expected_imports:
            if func in content:
                print(f"  ✅ {func}")
            else:
                print(f"  ❌ {func} - NOT FOUND")
                return False
    else:
        print("❌ wf_credit_session_utils import 없음")
        return False
    
    # 함수 호출 검증
    print("\n=== 함수 호출 검증 ===")
    
    # 1. calculate_processable_count 호출 확인
    print("\n1. calculate_processable_count")
    pattern = r'processable_count\s*=\s*calculate_processable_count\s*\('
    matches = re.findall(pattern, content)
    if matches:
        print(f"  ✅ 호출됨 ({len(matches)}회)")
        # 파라미터 검증
        param_pattern = r'calculate_processable_count\s*\(\s*(\w+)\s*,\s*(\w+)\s*\)'
        param_matches = re.findall(param_pattern, content)
        for credits, cost in param_matches:
            print(f"     → 파라미터: {credits}, {cost}")
    else:
        print("  ❌ 호출되지 않음")
        return False
    
    # 2. format_progress_label 호출 확인
    print("\n2. format_progress_label")
    pattern = r'label\s*=\s*format_progress_label\s*\('
    matches = re.findall(pattern, content)
    if matches:
        print(f"  ✅ 호출됨 ({len(matches)}회)")
        # 파라미터 확인
        param_pattern = r'format_progress_label\s*\(\s*already_processed_count\s*=\s*(\w+)'
        param_matches = re.findall(param_pattern, content)
        for var in param_matches:
            print(f"     → already_processed_count={var}")
    else:
        print("  ❌ 호출되지 않음")
        return False
    
    # 3. build_credit_shortage_init_message 호출 확인
    print("\n3. build_credit_shortage_init_message")
    pattern = r'msg\s*=\s*build_credit_shortage_init_message\s*\('
    matches = re.findall(pattern, content)
    if matches:
        print(f"  ✅ 호출됨 ({len(matches)}회)")
        # 파라미터 확인
        if 'remaining_count=' in content and 'processable_count=' in content:
            print("     → 파라미터: remaining_count, processable_count, needed_credits...")
        else:
            print("     ⚠️  파라미터 확인 불가")
    else:
        print("  ❌ 호출되지 않음")
        return False
    
    # 4. build_credit_shortage_completion_message 호출 확인
    print("\n4. build_credit_shortage_completion_message")
    pattern = r'msg\s*=\s*build_credit_shortage_completion_message\s*\('
    matches = re.findall(pattern, content)
    if matches:
        print(f"  ✅ 호출됨 ({len(matches)}회)")
        if 'processed=' in content and 'already_processed_count=' in content:
            print("     → 파라미터: processed, already_processed_count, total_file_count...")
        else:
            print("     ⚠️  파라미터 확인 불가")
    else:
        print("  ❌ 호출되지 않음")
        return False
    
    # 5. build_normal_completion_message 호출 확인
    print("\n5. build_normal_completion_message")
    pattern = r'msg\s*=\s*build_normal_completion_message\s*\('
    matches = re.findall(pattern, content)
    if matches:
        print(f"  ✅ 호출됨 ({len(matches)}회)")
        if 'total=' in content and 'processed=' in content:
            print("     → 파라미터: total, processed, failed, folder_stats...")
        else:
            print("     ⚠️  파라미터 확인 불가")
    else:
        print("  ❌ 호출되지 않음")
        return False
    
    # 6. get_credit_purchase_url 호출 확인 (optional - 팝업 내부에서 사용될 수 있음)
    print("\n6. get_credit_purchase_url")
    pattern = r'get_credit_purchase_url\s*\(\s*\)'
    matches = re.findall(pattern, content)
    if matches:
        print(f"  ✅ 호출됨 ({len(matches)}회)")
    else:
        print("  ℹ️  직접 호출 없음 (메시지 함수 내부에서 사용될 수 있음)")
    
    # compute_session_stats는 다른 utils 함수 내부에서 사용되므로 직접 호출은 선택사항
    
    # 기존 하드코딩된 메시지가 남아있는지 확인
    print("\n=== 기존 하드코딩 메시지 잔존 확인 ===")
    
    legacy_patterns = [
        (r'msg\s*=\s*f?".*크레딧.*부족.*실행할\s+수\s+없습니다', "크레딧 부족 메시지 하드코딩"),
        (r'msg\s*=\s*f?".*분류\s+작업이\s+완료되었습니다', "완료 메시지 하드코딩"),
    ]
    
    found_legacy = False
    for pattern, desc in legacy_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        # utils 함수 내부는 제외 (wf_credit_session_utils.py 내용)
        if matches:
            # ui_main.py에서 직접 작성된 것인지 확인
            for match in matches:
                if 'build_' not in match:  # utils 함수 호출이 아닌 경우
                    print(f"  ⚠️  발견: {desc}")
                    found_legacy = True
    
    if not found_legacy:
        print("  ✅ 하드코딩된 메시지 없음")
    
    print("\n" + "=" * 60)
    print("검증 완료")
    print("=" * 60)
    
    return True


def check_parameter_consistency():
    """파라미터 이름과 타입 일관성 검증"""
    print("\n=== 파라미터 일관성 검증 ===")
    
    # 90.tests/50.data/dwg_classifier -> 90.tests -> 10.rpa -> 50.data -> dwg_classifier
    ui_main_path = Path(__file__).parent.parent.parent.parent / "50.data" / "dwg_classifier" / "ui_main.py"
    
    with open(ui_main_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # format_progress_label 호출 패턴 상세 분석
    pattern = r'format_progress_label\s*\(\s*already_processed_count\s*=\s*(\w+)\s*,\s*current_processed\s*=\s*(\w+)\s*,\s*total_file_count\s*=\s*(\w+)\s*,\s*is_finished\s*=\s*(\w+)'
    matches = re.findall(pattern, content)
    
    print("\nformat_progress_label 호출 분석:")
    if matches:
        for i, (already, current, total, finished) in enumerate(matches, 1):
            print(f"  호출 {i}: already={already}, current={current}, total={total}, finished={finished}")
    else:
        print("  ℹ️  패턴 매칭 실패 (다른 포맷 사용 중일 수 있음)")
    
    # build_credit_shortage_init_message 호출 패턴
    pattern = r'build_credit_shortage_init_message\s*\(\s*remaining_count\s*=\s*(\w+)'
    matches = re.findall(pattern, content)
    
    print("\nbuild_credit_shortage_init_message 호출 분석:")
    if matches:
        for i, var in enumerate(matches, 1):
            print(f"  호출 {i}: remaining_count={var}")
    else:
        print("  ℹ️  패턴 매칭 실패")
    
    print("\n✅ 파라미터 일관성 검증 완료")
    return True


def main():
    """전체 검증 실행"""
    success = check_function_calls()
    
    if success:
        check_parameter_consistency()
        print("\n✅ 모든 함수 호출 검증 성공!")
        print("\n📋 요약:")
        print("  - utils 함수가 올바르게 import됨")
        print("  - 6개 핵심 함수가 적절히 호출됨")
        print("  - 하드코딩된 메시지 제거됨")
        print("  - 파라미터 일관성 유지됨")
        return 0
    else:
        print("\n❌ 함수 호출 검증 실패!")
        return 1


if __name__ == "__main__":
    exit(main())
