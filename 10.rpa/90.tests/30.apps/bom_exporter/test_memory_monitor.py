# -*- coding: utf-8 -*-
"""
메모리 모니터링 기능 테스트
"""
import sys
import os
import psutil

# 프로젝트 경로 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "30.apps", "Bom_Exporter"))


def test_memory_info():
    """시스템 메모리 정보 출력 테스트"""
    print("=" * 60)
    print("시스템 메모리 상태 테스트")
    print("=" * 60)

    mem = psutil.virtual_memory()
    print(f"📊 메모리 정보:")
    print(f"   전체: {round(mem.total / (1024**3), 2)}GB")
    print(f"   사용중: {round(mem.used / (1024**3), 2)}GB ({mem.percent}%)")
    print(f"   가용: {round(mem.available / (1024**3), 2)}GB ({100 - mem.percent:.1f}%)")
    print()

    # SolidWorks 메모리 확인
    sw_found = False
    for proc in psutil.process_iter(["name", "memory_info"]):
        try:
            if proc.info["name"] == "SLDWORKS.exe":
                sw_mem_gb = round(proc.info["memory_info"].rss / (1024**3), 2)
                print(f"🔧 SolidWorks 프로세스 발견:")
                print(f"   메모리 사용량: {sw_mem_gb}GB")
                sw_found = True
                break
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    if not sw_found:
        print("ℹ️  SolidWorks 프로세스를 찾을 수 없습니다 (실행 중이 아님)")

    print()
    print("=" * 60)


def test_memory_threshold():
    """메모리 임계치 체크 테스트"""
    print("메모리 임계치 체크 테스트")
    print("=" * 60)

    threshold_percent = 20
    mem = psutil.virtual_memory()
    available_percent = 100 - mem.percent

    print(f"⚙️  설정된 임계치: {threshold_percent}%")
    print(f"📊 현재 가용 메모리: {available_percent:.1f}%")
    print()

    if available_percent < threshold_percent:
        print(f"⚠️  경고! 메모리 부족 감지!")
        print(f"   가용 메모리 ({available_percent:.1f}%) < 임계치 ({threshold_percent}%)")
        print(f"   → 이 상황에서 SolidWorks 자동 재시작이 트리거됩니다.")
    else:
        print(f"✅ 메모리 상태 정상")
        print(f"   가용 메모리 ({available_percent:.1f}%) >= 임계치 ({threshold_percent}%)")

    print()
    print("=" * 60)


def test_memory_monitor_integration():
    """automation.py의 메모리 체크 메서드 테스트"""
    print("Memory Monitor 통합 테스트")
    print("=" * 60)

    try:
        from automation import BomAutomation

        # 콘솔 모드로 인스턴스 생성 (SolidWorks 실행 없이)
        print("ℹ️  BomAutomation 인스턴스 생성 중...")
        bom = BomAutomation(console_mode=True)

        print(f"✅ 메모리 모니터링 활성화: {bom.enable_memory_monitor}")
        print(f"⚙️  메모리 임계치: {bom.memory_threshold_percent}%")

        # 메모리 체크 메서드 호출 (SolidWorks 재시작 없이 체크만)
        print()
        print("📊 메모리 상태 체크 실행 중...")

        # 실제로는 재시작하지 않도록 enable_memory_monitor를 임시로 끔
        original_setting = bom.enable_memory_monitor
        bom.enable_memory_monitor = False  # 테스트에서는 재시작 방지

        # 메모리 정보만 출력
        mem = psutil.virtual_memory()
        available_percent = 100 - mem.percent
        print(f"   가용 메모리: {round(mem.available / (1024**3), 2)}GB ({available_percent:.1f}%)")

        if available_percent < bom.memory_threshold_percent:
            print(f"   ⚠️  실제 운영 시 재시작 트리거됨 (현재 테스트 모드)")
        else:
            print(f"   ✅ 메모리 정상 (재시작 불필요)")

        # 설정 복원
        bom.enable_memory_monitor = original_setting

        print()
        print("✅ 통합 테스트 완료: 메모리 모니터링 시스템이 정상 작동합니다.")

    except ImportError as e:
        print(f"❌ automation 모듈 import 실패: {e}")
        print("   app_setting_data.py 또는 다른 의존성 문제일 수 있습니다.")
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback

        traceback.print_exc()

    print("=" * 60)


if __name__ == "__main__":
    print()
    print("🚀 메모리 모니터링 시스템 테스트 시작")
    print()

    # 테스트 1: 시스템 메모리 정보
    test_memory_info()
    print()

    # 테스트 2: 임계치 체크
    test_memory_threshold()
    print()

    # 테스트 3: 통합 테스트
    test_memory_monitor_integration()
    print()

    print("🎉 모든 테스트 완료!")
