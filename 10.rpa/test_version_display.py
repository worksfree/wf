#!/usr/bin/env python3
"""4개 RPA 앱의 버전 표시 시뮬레이션 - 개발/배포 환경 모두 테스트"""

import json
from pathlib import Path

# ANSI 색상 코드
GREEN = '\033[92m'
YELLOW = '\033[93m'
CYAN = '\033[96m'
MAGENTA = '\033[95m'
WHITE = '\033[97m'
RED = '\033[91m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'

def test_version_loading(app_title, dev_path, release_path):
    """개발/배포 환경 모두 테스트"""
    
    print(f"\n{'='*70}")
    print(f"{BOLD}{GREEN}📦 {app_title}{RESET}")
    print(f"{'='*70}")
    
    # 개발 모드 테스트
    print(f"\n{CYAN}🔧 개발 모드 (frozen=False):{RESET}")
    print(f"   경로: {dev_path}")
    
    dev_version = "v0.7.0.0"  # default
    dev_build = 0
    
    if dev_path.exists():
        try:
            with open(dev_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                app_config = data.get("app_config", {})
                dev_version = app_config.get("full_version", "v0.7.0.0")
                dev_build = app_config.get("build_count", 0)
                if not dev_version.startswith("v"):
                    dev_version = "v" + dev_version
            
            print(f"   {GREEN}✅ 파일 존재{RESET}")
            print(f"   └─ full_version: {WHITE}{dev_version}{RESET} (build #{dev_build})")
        except Exception as e:
            print(f"   {RED}❌ 읽기 실패: {e}{RESET}")
    else:
        print(f"   {RED}❌ 파일 없음 → fallback: {dev_version}{RESET}")
    
    # 배포 모드 테스트
    print(f"\n{BLUE}📦 배포 모드 (frozen=True):{RESET}")
    print(f"   경로: {release_path}")
    
    release_version = "v0.7.0.0"  # default
    release_build = 0
    
    if release_path.exists():
        try:
            with open(release_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                app_config = data.get("app_config", {})
                release_version = app_config.get("full_version", "v0.7.0.0")
                release_build = app_config.get("build_count", 0)
                if not release_version.startswith("v"):
                    release_version = "v" + release_version
            
            print(f"   {GREEN}✅ 파일 존재{RESET}")
            print(f"   └─ full_version: {WHITE}{release_version}{RESET} (build #{release_build})")
        except Exception as e:
            print(f"   {RED}❌ 읽기 실패: {e}{RESET}")
    else:
        print(f"   {RED}❌ 파일 없음 → fallback: {release_version}{RESET}")
    
    # 파싱 결과
    dev_parts = dev_version.lstrip("v").split(".")
    dev_display = "v" + ".".join(dev_parts[:2])
    
    release_parts = release_version.lstrip("v").split(".")
    release_display = "v" + ".".join(release_parts[:2])
    
    print(f"\n{YELLOW}🖥️  UI 타이틀 표시:{RESET}")
    print(f"   {CYAN}[개발]{RESET} {app_title} {YELLOW}{dev_display}{RESET} (메인창)")
    print(f"   {CYAN}[개발]{RESET} {app_title} {YELLOW}{dev_version}{RESET} [🔧 관리자 모드]")
    print(f"   {BLUE}[배포]{RESET} {app_title} {YELLOW}{release_display}{RESET} (메인창)")
    print(f"   {BLUE}[배포]{RESET} {app_title} {YELLOW}{release_version}{RESET} [🔧 관리자 모드]")


def main():
    workspace = Path("D:/drive_files/10.worksfree/10.rpa")
    
    print(f"\n{BOLD}{CYAN}╔══════════════════════════════════════════════════════════════════╗{RESET}")
    print(f"{BOLD}{CYAN}║   🔍 4개 RPA 앱 버전 로딩 시뮬레이션 (개발/배포 환경)            ║{RESET}")
    print(f"{BOLD}{CYAN}╚══════════════════════════════════════════════════════════════════╝{RESET}")
    
    apps = [
        {
            "title": "BOM 엑셀 저장",
            "dev": workspace / "30.apps" / "bom_exporter" / "config" / "bom_exporter" / "settings.json",
            "release": Path.home() / ".wf_rpa" / "bom_exporter" / "settings.json"
        },
        {
            "title": "DWG 파일 분류 도구",
            "dev": workspace / "50.data" / "dwg_classifier" / "config" / "dwg_classifier" / "settings.json",
            "release": Path.home() / ".wf_rpa" / "dwg_classifier" / "settings.json"
        },
        {
            "title": "변환 확인 도구",
            "dev": workspace / "50.data" / "conversion_verifier" / "config" / "conversion_verifier" / "settings.json",
            "release": Path.home() / ".wf_rpa" / "conversion_verifier" / "settings.json"
        },
        {
            "title": "한글 파일명 복원",
            "dev": workspace / "50.data" / "korean_filename_normalizer" / "config" / "korean_filename_normalizer" / "settings.json",
            "release": Path.home() / ".wf_rpa" / "korean_filename_normalizer" / "settings.json"
        }
    ]
    
    for app in apps:
        test_version_loading(app["title"], app["dev"], app["release"])
    
    print(f"\n{BOLD}{CYAN}╔══════════════════════════════════════════════════════════════════╗{RESET}")
    print(f"{BOLD}{GREEN}║  ✅ 버전 로딩 시뮬레이션 완료                                     ║{RESET}")
    print(f"{BOLD}{CYAN}╚══════════════════════════════════════════════════════════════════╝{RESET}\n")


if __name__ == "__main__":
    main()
