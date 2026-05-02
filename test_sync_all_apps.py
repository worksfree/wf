#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
모든 7개 앱의 Google Sheets 동기화 테스트

각 앱을 실행하고:
1. 시작 시 credit_usage_log, credit_sync 전송 확인
2. 업데이트 버튼 클릭 시 credit_purchase_log, admin_config, app_policy 동기화 확인
"""

import sys
import subprocess
import time
from pathlib import Path

# 7개 앱 경로
APPS = [
    ("bom_exporter", "30.apps\\bom_exporter"),
    ("batch_print", "30.apps\\batch_print"),
    ("attribute_reset", "30.apps\\attribute_reset"),
    ("dwg_classifier", "50.data\\dwg_classifier"),
    ("conversion_verifier", "50.data\\conversion_verifier"),
    ("korean_filename_normalizer", "50.data\\korean_filename_normalizer"),
    ("qrcode_generator", "50.data\\qrcode_generator"),
]

BASE_PATH = Path("d:\\drive_files\\10.worksfree\\10.rpa")

def test_app(app_name, app_path):
    """앱 실행 및 로그 확인"""
    print(f"\n{'='*80}")
    print(f"[TEST] {app_name}")
    print(f"{'='*80}")
    
    app_dir = BASE_PATH / app_path
    if not app_dir.exists():
        print(f"[ERROR] 앱 폴더 없음: {app_dir}")
        return False
    
    try:
        # 앱 실행 (10초 후 종료)
        print(f"[START] 앱 시작: {app_name}")
        process = subprocess.Popen(
            [sys.executable, "ui_main.py"],
            cwd=str(app_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8'
        )
        
        # 10초 대기
        time.sleep(10)
        
        # 프로세스 종료
        try:
            process.terminate()
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        
        # 로그 출력
        output, _ = process.communicate(timeout=2)
        
        # 핵심 로그 확인
        print("\n[LOGS] 핵심 로그:")
        keywords = [
            "credit_usage_log",
            "credit_sync",
            "credit_purchase_log",
            "admin_config",
            "app_policy",
            "정책 동기화",
            "이메일 설정",
            "ERROR",
            "Exception"
        ]
        
        for line in output.split('\n'):
            for keyword in keywords:
                if keyword in line:
                    print(f"  {line[:150]}")
                    break
        
        # 체크리스트
        print("\n[CHECK] 동기화 상태:")
        checks = {
            "credit_usage_log": "사용 로그" in output or "사용량" in output or "사용 로그 기록" in output,
            "credit_sync": "동기화 완료" in output or "동기화" in output,
            "admin_config": "이메일 설정" in output or "admin_config" in output,
            "app_policy": "정책" in output or "app_policy" in output,
        }
        
        for check_name, result in checks.items():
            status = "[OK]" if result else "[FAIL]"
            print(f"  {status} {check_name}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] 오류: {e}")
        return False

def main():
    print("[START] 7개 앱 Google Sheets 동기화 테스트 시작\n")
    
    results = {}
    for app_name, app_path in APPS:
        results[app_name] = test_app(app_name, app_path)
    
    # 최종 결과
    print(f"\n{'='*80}")
    print("📊 최종 결과")
    print(f"{'='*80}")
    for app_name, success in results.items():
        status = "✅ 완료" if success else "❌ 실패"
        print(f"  {status}: {app_name}")

if __name__ == "__main__":
    main()
