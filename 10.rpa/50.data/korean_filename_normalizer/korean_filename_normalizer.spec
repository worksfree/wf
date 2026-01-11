# -*- mode: python ; coding: utf-8 -*-
"""
WorksFree 통합 앱 빌드 Spec Template
- 모든 빌드 로직을 spec 파일에 통합
- NSIS 인스톨러 자동 생성
- 멀티앱 지원 및 중복 설치 방지
- 배포 후 자동 정리 및 패키징
"""

import os
import sys
import json
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
import hashlib

# Windows 콘솔 인코딩 설정 (UTF-8 출력 지원)
if sys.platform == "win32":
    try:
        import io

        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except:
        pass  # 설정 실패 시 무시


# ==================== 유효한 기본 아이콘 생성 ====================
def ensure_b2e_icon():
    """res/KFN.ico를 생성(또는 교체)합니다. 16x16 32-bit BGRA BMP 기반 ICO.
    외부 라이브러리 없이 순수 바이트로 만듭니다."""
    res_dir = Path("res")
    res_dir.mkdir(exist_ok=True)
    ico_path = res_dir / "KFN.ico"

    import struct

    width = 16
    height = 16
    biHeight = height * 2  # XOR + AND
    biSizeImage = width * height * 4

    # BITMAPINFOHEADER
    bih = struct.pack(
        "<IIIHHIIIIII",
        40,  # biSize
        width,  # biWidth
        biHeight,  # biHeight
        1,  # biPlanes
        32,  # biBitCount
        0,  # biCompression
        biSizeImage,
        0,
        0,
        0,
        0,
    )

    # Solid blue-ish (BGRA) pixels
    b, g, r, a = 0x8F, 0xA3, 0xFF, 0xFF
    xor_bitmap = bytes([b, g, r, a]) * (width * height)

    # AND mask (all opaque). Each row padded to 32 bits: 16 pixels -> 2 bytes, pad to 4 bytes per row
    and_row = b"\x00\x00\x00\x00"
    and_mask = and_row * height

    bmp_data = bih + xor_bitmap + and_mask

    bytes_in_res = len(bmp_data)
    icondir = struct.pack("<HHH", 0, 1, 1)
    entry = struct.pack(
        "<BBBBHHII",
        width if width < 256 else 0,
        height if height < 256 else 0,
        0,
        0,
        1,
        32,
        bytes_in_res,
        6 + 16,
    )

    ico_bytes = icondir + entry + bmp_data
    with open(ico_path, "wb") as f:
        f.write(ico_bytes)
    return ico_path


# ==================== 버전 관리 ====================
def load_and_increment_version():
    """settings.json에서 버전을 읽고 자동으로 증가시킴"""
    try:
        SPEC_DIR_LOCAL = Path(__file__).resolve().parent
    except NameError:
        SPEC_DIR_LOCAL = Path(os.getcwd())

    settings_file = SPEC_DIR_LOCAL / "config" / "korean_filename_normalizer" / "settings.json"
    default_version = [0, 7, 0, 0]

    if settings_file.exists():
        try:
            with open(settings_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                full_version = data.get("app_config", {}).get("full_version", "v0.7.0.0")
                version = [int(x) for x in full_version.lstrip("v").split(".")]
        except Exception:
            version = default_version
    else:
        version = default_version

    version[3] += 1
    if version[3] > 9:
        version[3] = 0
        version[2] += 1
        if version[2] > 9:
            version[2] = 0
            version[1] += 1

    if settings_file.exists():
        with open(settings_file, "r", encoding="utf-8") as f:
            settings_data = json.load(f)
    else:
        settings_data = {"app_config": {}}

    if "app_config" not in settings_data:
        settings_data["app_config"] = {}

    settings_data["app_config"][
        "full_version"
    ] = f"v{version[0]}.{version[1]}.{version[2]}.{version[3]}"
    settings_data["app_config"]["build_count"] = (
        settings_data.get("app_config", {}).get("build_count", 0) + 1
    )

    with open(settings_file, "w", encoding="utf-8") as f:
        json.dump(settings_data, f, ensure_ascii=False, indent=2)

    version_data = {
        "full_version": f"{version[0]}.{version[1]}.{version[2]}.{version[3]}",
        "display_version": f"v{version[0]}.{version[1]}",
        "build_count": settings_data["app_config"]["build_count"],
    }

    print(f"✓ 버전 증가: {version_data['full_version']} (빌드 #{version_data['build_count']})")
    return version_data


VERSION_INFO = load_and_increment_version()
APP_VERSION_FULL = VERSION_INFO["full_version"].lstrip('v')  # v 제거
APP_VERSION_DISPLAY = VERSION_INFO["display_version"]

# ==================== 앱 정보 설정 (각 앱별로 수정) ====================
APP_NAME = "korean_filename_normalizer"  # 빌드할 앱 이름
APP_VERSION = APP_VERSION_FULL
APP_DISPLAY_NAME = "Korean Filename Normalizer"
APP_DESCRIPTION = "한글 파일명 정규화 도구"
APP_PUBLISHER = "WorksFree Co., Ltd."
APP_URL = "https://worksfree.co.kr"
APP_CONTACT = "support@worksfree.co.kr"

# ==================== 디버그 및 최적화 설정 ====================
DEBUG_BUILD = False  # False: 릴리스 모드 (console 숨김)
STARTUP_PROFILING = False  # False: 프로파일링 비활성화 (성능 최적화)

# ==================== 경로 및 환경 설정 ====================
# spec 파일 위치 기준으로 시도, 실패 시 현재 작업 디렉토리 사용
try:
    SPEC_DIR = Path(__file__).resolve().parent  # 일부 실행 컨텍스트에서 __file__ 미정의 가능
except NameError:
    SPEC_DIR = Path(os.getcwd())
WORKSPACE_ROOT = SPEC_DIR.parent.parent
COMMON_DIR = WORKSPACE_ROOT / "10.common"
TEMPLATES_DIR = WORKSPACE_ROOT / "templates"
BUILD_OUTPUT_DIR = Path("D:/release/candidates")

# WorksFree 앱 목록 (NSIS 중복 설치 방지용)
WORKSFREE_APPS = [
    "{APP_NAME}",
    "dwg_classifier",
    "conversion_verifier",
    "korean_filename_normalizer",
    "file_list_check",
    "spreadsheet_manager",
]

print(f"\n{'='*80}")
print(f"WorksFree {APP_DISPLAY_NAME} v{APP_VERSION} 통합 빌드 시작")
print(f"{'='*80}")

# (레거시) 글로벌 정책 파일 생성 로직은 제거되었습니다.


# ==================== 사용자 홈 설정 파일 준비 ====================
def prepare_user_configs():
    """사용자 홈 디렉토리용 설정 파일들 준비"""
    # config 폴더를 빌드용 임시 구조로 복사
    home_dir = SPEC_DIR / "build" / "user_home_bundle"
    home_dir.mkdir(parents=True, exist_ok=True)

    wf_rpa_dir = home_dir / ".wf_rpa"
    app_dir = wf_rpa_dir / APP_NAME

    for directory in [wf_rpa_dir, app_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    # 1. wf_rpa_config.json - 실제 config 파일에서 복사 (관리자 이메일, Google Sheets 포함)
    app_config_dir = SPEC_DIR / "config"
    source_wf_config = app_config_dir / "wf_rpa_config.json"
    
    if source_wf_config.exists():
        shutil.copy2(source_wf_config, wf_rpa_dir / "wf_rpa_config.json")
        print(f"✓ wf_rpa_config.json 복사 완료 (email_settings, google_sheets 포함)")
    else:
        print(f"⚠️ wf_rpa_config.json을 찾을 수 없음: {source_wf_config}")

    # 2. Google Credentials 복사 (.wf_rpa 루트에 직접 복사, wf_rpa_config와 동일 위치)
    google_creds_found = False
    if app_config_dir.exists():
        # .silver-argon-445712-a0-4ce021aa64be.json 파일만 복사 (원본 이름 유지)
        actual_key = app_config_dir / ".silver-argon-445712-a0-4ce021aa64be.json"
        if actual_key.exists():
            shutil.copy2(actual_key, wf_rpa_dir / actual_key.name)
            google_creds_found = True
            print(f"✓ Google credentials 포함 (.wf_rpa 루트): {actual_key.name}")
        else:
            # fallback: .silver-argon으로 시작하는 첫 번째 파일
            for json_file in app_config_dir.glob(".silver-argon*.json"):
                shutil.copy2(json_file, wf_rpa_dir / json_file.name)
                google_creds_found = True
                print(f"✓ Google credentials 포함 (.wf_rpa 루트): {json_file.name}")
                break

    if not google_creds_found:
        print("⚠️ Google credentials를 찾을 수 없습니다.")
    
    # 3. settings.json 처리: 버전 주입 + 사용자 경로 초기화
    app_config_dir = SPEC_DIR / "config" / "korean_filename_normalizer"
    settings_src = app_config_dir / "settings.json"
    if settings_src.exists():
        with open(settings_src, 'r', encoding='utf-8') as f:
            settings_data = json.load(f)
        
        # 버전 정보 주입 (runtime_config에만)
        if 'runtime_config' not in settings_data:
            settings_data['runtime_config'] = {}
        settings_data['runtime_config']['full_version'] = f"v{APP_VERSION_FULL}"
        settings_data['runtime_config']['build_count'] = VERSION_INFO['build_count']
        settings_data['runtime_config']['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 사용자 경로 초기화 (배포 환경에서 깨끗한 상태로 시작)
        if 'ui_config' not in settings_data:
            settings_data['ui_config'] = {}
        settings_data['ui_config']['last_selected_folder'] = ""
        settings_data['ui_config']['window_geometry_override'] = ""
        
        # 저장
        app_settings_dir = wf_rpa_dir / "korean_filename_normalizer"
        app_settings_dir.mkdir(parents=True, exist_ok=True)
        bundled_settings = app_settings_dir / "settings.json"
        with open(bundled_settings, 'w', encoding='utf-8') as f:
            json.dump(settings_data, f, ensure_ascii=False, indent=2)
        
        print(f"✓ settings.json 처리 완료 (.wf_rpa/korean_filename_normalizer/) - 버전: {APP_VERSION_FULL}, 빌드: #{VERSION_INFO['build_count']}")

    # 4. policy.json 복사 (버전 정보는 settings.json의 runtime_config에만 있음)
    # policy.json은 identity + policy만 포함 (변하지 않는 값들)
    # 버전 정보는 settings.json의 runtime_config에만 있음
    # policy.json은 그대로 복사만 함 (버전 주입 안함)
    source_config_dir = SPEC_DIR / "config"
    policy_src = source_config_dir / "korean_filename_normalizer" / "policy.json"
    if policy_src.exists():
        app_settings_dir = wf_rpa_dir / "korean_filename_normalizer"
        app_settings_dir.mkdir(parents=True, exist_ok=True)
        bundled_policy = app_settings_dir / "policy.json"
        shutil.copy2(policy_src, bundled_policy)
        print(f"✓ policy.json 복사 완료 (.wf_rpa/korean_filename_normalizer/)")

    print(f"✓ 사용자 설정 파일 준비 완료: {home_dir}")
    return home_dir


# ==================== NSIS 스크립트 생성 ====================
def create_nsis_script():
    """NSIS 인스톨러 스크립트 생성"""
    # 고정 아이콘: KFN.ico (요청에 따라 fallback 제거)
    # PyInstaller 단계에서 ensure_b2e_icon 수행되므로 바로 사용
    ensure_b2e_icon()
    icon_define = '!define MUI_ICON "res\\KFN.ico"\n!define MUI_UNICON "res\\KFN.ico"\n'

    nsis_script = f"""!include "MUI2.nsh"
!include "FileFunc.nsh"
!include "LogicLib.nsh"

; ==================== 기본 정보 ====================
Name "{APP_DISPLAY_NAME}"
OutFile "{APP_NAME}_{APP_VERSION}_installer.exe"
InstallDir "$PROGRAMFILES64\\WorksFree\\{APP_NAME}"
InstallDirRegKey HKLM "Software\\WorksFree\\{APP_NAME}" "InstallPath"
RequestExecutionLevel admin

; ==================== 버전 정보 ====================
VIProductVersion "{APP_VERSION}.0"
VIAddVersionKey "ProductName" "{APP_DISPLAY_NAME}"
VIAddVersionKey "CompanyName" "{APP_PUBLISHER}"
VIAddVersionKey "ProductVersion" "{APP_VERSION}"
VIAddVersionKey "FileVersion" "{APP_VERSION}.0"
VIAddVersionKey "FileDescription" "{APP_DESCRIPTION}"
VIAddVersionKey "LegalCopyright" "Copyright © 2024 {APP_PUBLISHER}"

; ==================== 인터페이스 설정 ====================
!define MUI_ABORTWARNING
{icon_define}

; 페이지 설정
!insertmacro MUI_PAGE_WELCOME
; !insertmacro MUI_PAGE_LICENSE "license.txt"
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

!insertmacro MUI_LANGUAGE "Korean"
!insertmacro MUI_LANGUAGE "English"

; ==================== 전역 변수 ====================
Var IsFirstWorksFreeApp
Var GlobalConfigExists
Var CredentialsExists

; ==================== 사전 설치 검사 ====================
Function .onInit
    ; WorksFree 전역 설정 디렉토리 확인
    IfFileExists "$PROFILE\\.wf_rpa\\wf_rpa_config.json" 0 +3
        StrCpy $GlobalConfigExists "true"
        Goto +2
        StrCpy $GlobalConfigExists "false"
    
    ; Google Credentials 존재 확인 (실제 키 파일명으로 확인)
    IfFileExists "$PROFILE\\.wf_rpa\\credentials\\.silver-argon-445712-a0-4ce021aa64be.json" 0 +3
        StrCpy $CredentialsExists "true"
        Goto +2
        StrCpy $CredentialsExists "false"
    
    ; 첫 번째 WorksFree 앱인지 확인
    ${{If}} $GlobalConfigExists == "false"
        StrCpy $IsFirstWorksFreeApp "true"
        DetailPrint "첫 번째 WorksFree 앱 설치를 감지했습니다."
    ${{Else}}
        StrCpy $IsFirstWorksFreeApp "false"
        DetailPrint "기존 WorksFree 환경에 추가 설치합니다."
    ${{EndIf}}
FunctionEnd

; ==================== 설치 섹션 ====================
Section "!{APP_DISPLAY_NAME} (필수)" SecMain
    SectionIn RO ; 필수 섹션
    
    SetOutPath "$INSTDIR"
    
    ; 메인 앱 파일들 설치
    File /r "dist\\{APP_NAME}\\*.*"
    
    ; 레지스트리 등록
    WriteRegStr HKLM "Software\\WorksFree\\{APP_NAME}" "InstallPath" "$INSTDIR"
    WriteRegStr HKLM "Software\\WorksFree\\{APP_NAME}" "Version" "{APP_VERSION}"
    WriteRegStr HKLM "Software\\WorksFree\\{APP_NAME}" "DisplayName" "{APP_DISPLAY_NAME}"
    WriteRegStr HKLM "Software\\WorksFree\\{APP_NAME}" "Publisher" "{APP_PUBLISHER}"
    WriteRegStr HKLM "Software\\WorksFree\\{APP_NAME}" "InstallDate" "$DATE"
    
    ; 프로그램 추가/제거 등록
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{APP_NAME}" "DisplayName" "{APP_DISPLAY_NAME}"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{APP_NAME}" "UninstallString" "$\\"$INSTDIR\\uninstall.exe$\\""
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{APP_NAME}" "DisplayIcon" "$INSTDIR\\{APP_NAME}.exe"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{APP_NAME}" "Publisher" "{APP_PUBLISHER}"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{APP_NAME}" "DisplayVersion" "{APP_VERSION}"
    WriteRegDWORD HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{APP_NAME}" "NoModify" 1
    WriteRegDWORD HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{APP_NAME}" "NoRepair" 1
    
    ; 설치 크기 계산
    ${{GetSize}} "$INSTDIR" "/S=0K" $0 $1 $2
    IntFmt $0 "0x%08X" $0
    WriteRegDWORD HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{APP_NAME}" "EstimatedSize" "$0"
    
    ; 언인스톨러 생성
    WriteUninstaller "$INSTDIR\\uninstall.exe"
SectionEnd

Section "사용자 설정 파일" SecUserConfig
    ; 첫 번째 앱이거나 글로벌 설정이 없을 때만 설치
    ${{If}} $IsFirstWorksFreeApp == "true"
    ${{OrIf}} $GlobalConfigExists == "false"
        DetailPrint "WorksFree 전역 설정을 초기화합니다..."
        
        ; .wf_rpa 디렉토리 생성
        CreateDirectory "$PROFILE\\.wf_rpa"
        CreateDirectory "$PROFILE\\.wf_rpa\\{APP_NAME}"
        CreateDirectory "$PROFILE\\.wf_rpa\\credentials"
        CreateDirectory "$PROFILE\\.wf_rpa\\logs"
        
        ; 전역 설정 파일들 복사
        SetOutPath "$PROFILE\\.wf_rpa"
        File "build\\user_home_bundle\\.wf_rpa\\wf_rpa_config.json"
        
        ; 앱별 설정 파일 복사
        SetOutPath "$PROFILE\\.wf_rpa\\{APP_NAME}"
        File "build\\user_home_bundle\\.wf_rpa\\{APP_NAME}\\*.*"
        
        DetailPrint "✓ WorksFree 환경 설정 완료"
    ${{Else}}
        DetailPrint "기존 WorksFree 설정을 사용합니다."
        
        ; 앱별 설정 디렉토리만 생성
        CreateDirectory "$PROFILE\\.wf_rpa\\{APP_NAME}"
        SetOutPath "$PROFILE\\.wf_rpa\\{APP_NAME}"
        File "build\\user_home_bundle\\.wf_rpa\\{APP_NAME}\\*.*"
    ${{EndIf}}
SectionEnd

Section "Google Credentials" SecCredentials
    ; Credentials가 없을 때만 설치
    ${{If}} $CredentialsExists == "false"
        DetailPrint "Google Service Account 인증 정보를 설치합니다..."
        
        SetOutPath "$PROFILE\\.wf_rpa"
        File "build\\user_home_bundle\\.wf_rpa\\.silver-argon-*.json"
        
        DetailPrint "✓ Google 인증 정보 설치 완료 (.wf_rpa 루트)"
    ${{Else}}
        DetailPrint "기존 Google 인증 정보를 사용합니다."
    ${{EndIf}}
SectionEnd

Section "바탕화면 바로가기" SecDesktopShortcut
    CreateShortCut "$DESKTOP\\{APP_NAME}.lnk" "$INSTDIR\\{APP_NAME}.exe"
SectionEnd

Section "시작 메뉴 항목" SecStartMenu
    CreateDirectory "$SMPROGRAMS\\WorksFree"
    CreateShortCut "$SMPROGRAMS\\WorksFree\\{APP_NAME}.lnk" "$INSTDIR\\{APP_NAME}.exe"
    CreateShortCut "$SMPROGRAMS\\WorksFree\\{APP_NAME} 제거.lnk" "$INSTDIR\\uninstall.exe"
SectionEnd

; ==================== 컴포넌트 설명 ====================
!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
    !insertmacro MUI_DESCRIPTION_TEXT ${{SecMain}} "{APP_DESCRIPTION}의 핵심 실행 파일들을 설치합니다."
    !insertmacro MUI_DESCRIPTION_TEXT ${{SecUserConfig}} "사용자 설정 및 크레딧 관리 파일들을 설치합니다. (첫 설치시 자동 선택)"
    !insertmacro MUI_DESCRIPTION_TEXT ${{SecCredentials}} "Google Sheets 연동을 위한 인증 정보를 설치합니다. (없을 경우에만)"
    !insertmacro MUI_DESCRIPTION_TEXT ${{SecDesktopShortcut}} "바탕화면에 실행 바로가기를 만듭니다."
    !insertmacro MUI_DESCRIPTION_TEXT ${{SecStartMenu}} "시작 메뉴에 프로그램 항목을 추가합니다."
!insertmacro MUI_FUNCTION_DESCRIPTION_END

; ==================== 설치 완료 후 처리 ====================
Function .onInstSuccess
    ; 전역 설정에 앱 추가
    DetailPrint "설치된 앱 목록을 업데이트합니다..."
    
    ; 간단한 JSON 업데이트 (실제로는 Python 스크립트 실행하거나 더 정교한 방법 사용)
    ExecWait '"$INSTDIR\\{APP_NAME}.exe" --register-install' $0
    
    DetailPrint "{APP_NAME} 설치가 완료되었습니다."
FunctionEnd

; ==================== 제거 섹션 ====================
Section "Uninstall"
    DetailPrint "{APP_NAME}을 제거합니다..."
    
    ; 실행 중인 프로세스 강제 종료 (오류 무시)
    nsExec::Exec 'taskkill /F /IM {APP_NAME}.exe /T'
    Sleep 1000
    
    ; 앱 파일들 제거
    DetailPrint "프로그램 파일을 제거합니다..."
    RMDir /r "$INSTDIR"
    
    ; 레지스트리 제거
    DetailPrint "레지스트리 정보를 제거합니다..."
    DeleteRegKey HKLM "Software\\WorksFree\\{APP_NAME}"
    DeleteRegKey HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{APP_NAME}"
    
    ; 바로가기 제거
    DetailPrint "바로가기를 제거합니다..."
    Delete "$DESKTOP\\{APP_NAME}.lnk"
    Delete "$SMPROGRAMS\\WorksFree\\{APP_NAME}.lnk"
    Delete "$SMPROGRAMS\\WorksFree\\{APP_NAME} 제거.lnk"
    
    ; WorksFree 폴더 정리 (다른 앱이 없으면)
    RMDir "$SMPROGRAMS\\WorksFree"
    
    ; 사용자 데이터 제거 옵션
    MessageBox MB_YESNO "사용자 설정, 크레딧, 로그를 함께 제거하시겠습니까?$\\n$\\n• 설정 파일: %USERPROFILE%\\.wf_rpa\\{APP_NAME}$\\n• 크레딧 정보 및 사용 기록$\\n• 로그 파일$\\n$\\n'아니오'를 선택하면 재설치시 기존 데이터를 유지할 수 있습니다." IDNO skip_user_data
        DetailPrint "사용자 데이터를 제거합니다..."
        RMDir /r "$PROFILE\\.wf_rpa\\{APP_NAME}"
        
        ; 전역 설정 파일도 정리 (다른 앱이 없으면)
        IfFileExists "$PROFILE\\.wf_rpa\\*.*" 0 remove_global
            DetailPrint "다른 WorksFree 앱이 있어 전역 설정은 유지합니다."
            Goto skip_global
        remove_global:
            DetailPrint "전역 설정을 제거합니다..."
            Delete "$PROFILE\\.wf_rpa\\wf_rpa_config.json"
            RMDir "$PROFILE\\.wf_rpa\\credentials"
            RMDir "$PROFILE\\.wf_rpa"
        skip_global:
        
        DetailPrint "✓ 사용자 데이터 제거 완료"
        Goto done_user_data
    skip_user_data:
        DetailPrint "사용자 데이터를 보존합니다."
    done_user_data:
    
    DetailPrint "✓ {APP_NAME} 제거 완료"
    MessageBox MB_OK "{APP_NAME}이 성공적으로 제거되었습니다."
SectionEnd
"""

    nsis_file = SPEC_DIR / f"{APP_NAME}_installer.nsi"
    with open(nsis_file, "w", encoding="utf-8-sig") as f:  # UTF-8 BOM 추가
        f.write(nsis_script)

    # 아이콘 파일 복사
    icon_source = SPEC_DIR / "res" / "KFN.ico"
    if icon_source.exists():
        # NSIS 스크립트와 같은 디렉토리에 res 폴더 생성 및 아이콘 복사
        res_dir = SPEC_DIR / "res"
        res_dir.mkdir(exist_ok=True)
        icon_target = res_dir / "KFN.ico"
        if not icon_target.exists() or icon_source.stat().st_mtime > icon_target.stat().st_mtime:
            shutil.copy2(icon_source, icon_target)
        print(f"✓ 아이콘 파일 준비: {icon_target}")

    print(f"✓ NSIS 스크립트 생성: {nsis_file}")
    return nsis_file


# ==================== 리소스 수집 ====================
def collect_essential_resources():
    """필수 리소스 파일들만 수집 (최적화됨)"""
    datas = []

    # 1. WorksFree 필수 공통 모듈만 (실제 사용되는 것만)
    essential_modules = [
        "wf_log.py",
        "wf_credit_manager.py",  # 크레딧 시스템 필수
        "wf_register.py",  # 등록/인증 필수
    ]

    for module in essential_modules:
        module_path = COMMON_DIR / module
        if module_path.exists():
            datas.append((str(module_path), "."))
            print(f"포함됨: {module}")
        else:
            print(f"누락됨: {module}")

    # 2. 로컬 앱 모듈들 (앱 디렉토리의 .py 파일들)
    local_modules = ["automation.py", "config.py", "ui_setting.py"]
    for module in local_modules:
        module_path = SPEC_DIR / module
        if module_path.exists():
            datas.append((str(module_path), "."))
            print(f"로컬 모듈 포함: {module}")

    # 3. 앱별 정책 파일: policy.json으로 통합됨 (credit_policy.json 제거)
    # policy.json은 prepare_user_configs에서 번들됨

    # 4. 사용자 홈 설정 파일들 (.wf_rpa 루트에 번들)
    user_home = prepare_user_configs()
    if user_home:
        wf_rpa_dir = user_home / ".wf_rpa"
        wf_rpa_config = wf_rpa_dir / "wf_rpa_config.json"
        if wf_rpa_config.exists():
            datas.append((str(wf_rpa_config), ".wf_rpa"))
            print(f"설정 파일 번들: {wf_rpa_config.name}")
        
        # settings.json과 policy.json을 .wf_rpa/korean_filename_normalizer/에 번들
        app_dir = wf_rpa_dir / APP_NAME
        app_settings = app_dir / "settings.json"
        if app_settings.exists():
            datas.append((str(app_settings), f".wf_rpa/{APP_NAME}"))
            print(f"설정 파일 번들: settings.json → .wf_rpa/{APP_NAME}/")
        
        policy_file = app_dir / "policy.json"
        if policy_file.exists():
            datas.append((str(policy_file), f".wf_rpa/{APP_NAME}"))
            print(f"설정 파일 번들: policy.json → .wf_rpa/{APP_NAME}/")

    # 6. 앱별 리소스
    app_res_dir = SPEC_DIR / "res"
    if app_res_dir.exists():
        for file_path in app_res_dir.rglob("*"):
            if file_path.is_file():
                rel_path = file_path.relative_to(app_res_dir)
                datas.append(
                    (
                        str(file_path),
                        f"res/{rel_path.parent}" if rel_path.parent != Path(".") else "res",
                    )
                )

    # 7. 인스톨러 리소스들
    installer_resources = ["license.txt", "icon.ico", "readme.txt"]

    for resource in installer_resources:
        resource_path = SPEC_DIR / resource
        if resource_path.exists():
            datas.append((str(resource_path), "."))

    # 8. Google Service Account 자격증명 파일 (.wf_rpa 루트에 배치)
    if user_home:
        wf_rpa_dir = user_home / ".wf_rpa"
        silver_files = list(wf_rpa_dir.glob(".silver-argon-*.json"))
        for silver_file in silver_files:
            datas.append((str(silver_file), ".wf_rpa"))
            print(f"자격증명 파일 번들: {silver_file.name}")

    # print(f"필수 리소스만 수집 완료: {len(datas)}개 파일")
    return datas


# ==================== 히든 임포트 정의 ====================
def get_optimized_hidden_imports():
    """최적화된 숨겨진 import 모듈들 - 필수만 포함"""
    # {APP_NAME}에 실제 필요한 모듈만
    essential_imports = [
        # WorksFree 핵심 (모든 wf_ 모듈 포함)
        "wf_log",
        "wf_credit_manager",
            "wf_credit_session_utils",
        "wf_app_init_helpers",
        "wf_register",
        "wf_email",
        "wf_gen_code",
        "wf_googlesheets_manager",
        "wf_hwinfo",
        "wf_license",
        # GUI 관련 (필수만)
        "tkinter",
        "tkinter.ttk",
        "tkinter.messagebox",
        "tkinter.filedialog",
        # pyautogui 계열 및 PIL 의존성은 이 앱에서 사용하지 않으므로 제외
        # 앱별 핵심 기능 (앱에 따라 조정)
        "unicodedata",  # 문자 처리
        "re",  # 정규식
        "os.path",
        "pathlib",
        "shutil",
        "argparse",
        "time",
        # PyInstaller 런타임 필수
        "zipfile",  # PyInstaller 런타임 훅 필요
        "multiprocessing",  # freeze_support 필요
        # 기본 시스템
        "json",
        "datetime",
        "threading",
        # 하드웨어 정보 (wf_hwinfo.py에서 필요)
        "cpuinfo.cpuinfo",   # CPU 정보
        "ntplib",            # 시간 동기화
        # Google Sheets 연동 (wf_googlesheets_manager.py에서 필요)
        "gspread",
        "google.auth",
        "google.auth.transport.requests",
        "google.oauth2.service_account",
        "google.auth.transport.urllib3",
        "google.auth.transport._http_client",
        "google.auth._helpers",
        "google.auth.exceptions",
        "google.oauth2.credentials",
        # pywin32 모듈 (Google API 사용 시 필수)
        "win32timezone",
        "win32api",
        "win32con",
        "pywintypes",
        "pythoncom",
        # 일부 버전에서는 _helpers 모듈이 존재하지 않을 수 있어 동적 포함 처리
        "requests",
        "requests.adapters",
        "requests.auth",
        "requests.cookies",
        "requests.exceptions",
        "requests.models",
        "requests.sessions",
        "requests.structures",
        "requests.utils",
        "urllib3",
        "urllib3.connection",
        "urllib3.connectionpool",
        "urllib3.exceptions",
        "urllib3.poolmanager",
        "urllib3.response",
        "urllib3.util",
        "urllib3.util.retry",
        "urllib3.util.ssl_",
        "certifi",
        "charset_normalizer",
    ]

    # 앱별 특화 imports
    app_specific = {
        "bom_exporter": [  # ← 수정: bom2excel → bom_exporter
            "pyautogui",
            "openpyxl",
            "openpyxl.utils",
            "openpyxl.styles",
            "keyboard",
            "pyperclip",
            "ntplib",
            "pywinauto",
            "pywinauto.application",
            "pywinauto.findwindows",
            "pywinauto.keyboard",
            "pywinauto.mouse",
            "pywinauto.timings",
            "pywinauto.controls",
            "pywinauto.controls.uiawrapper",
            "pywinauto.controls.win32_controls",
            "pywinauto.controls.common_controls",
            "pywinauto.base_wrapper",
            "pywinauto.element_info",
            "comtypes",
            "comtypes.client",
            "comtypes.gen",
            "win32timezone",
            "win32api",
            "win32con",
            "win32com",
            "win32com.client",
            "pywintypes",
            "pythoncom",
            "tqdm",
            "psutil",
            "pandas",
            "numpy",  # Excel 처리용
        ],
        "dwg_classifier": ["glob", "zipfile", "tempfile"],
        "conversion_verifier": ["difflib", "filecmp"],
        "korean_filename_normalizer": [
            "unicodedata",
            "re",
            "openpyxl",
            "openpyxl.utils",
            "openpyxl.styles",  # Excel 처리용
            "pandas",
            "numpy",  # openpyxl 의존성
        ],
        "file_list_check": ["csv", "xml.etree.ElementTree"],
        "spreadsheet_manager": ["xlrd", "xlwt", "xlutils"],
    }

    if APP_NAME in app_specific:
        essential_imports.extend(app_specific[APP_NAME])
    # google.oauth2._helpers 존재 시만 추가
    try:
        import importlib

        if importlib.util.find_spec("google.oauth2._helpers") is not None:
            essential_imports.append("google.oauth2._helpers")
    except Exception:
        pass

    return essential_imports


# ==================== 인스톨러 생성 여부 토글 ====================
def _should_build_installer() -> bool:
    """환경변수로 NSIS 인스톨러 생성을 건너뛸지 결정합니다.
    - WF_SKIP_INSTALLER in (1, true, yes, on)
    - 또는 WF_BUILD_INSTALLER in (0, false, no, off)
    기본값: 인스톨러 생성(True)
    """

    def _is_true(v: str) -> bool:
        return v.strip().lower() in ("1", "true", "yes", "y", "on")

    def _is_false(v: str) -> bool:
        return v.strip().lower() in ("0", "false", "no", "n", "off")

    skip = os.environ.get("WF_SKIP_INSTALLER")
    build = os.environ.get("WF_BUILD_INSTALLER")
    # 새로운 기본값: 인스톨러 생성을 건너뜀 (빠른 재빌드 목적)
    # WF_SKIP_INSTALLER=false 또는 WF_BUILD_INSTALLER=true 설정 시에만 생성
    if skip:
        if _is_true(skip):
            return False
        if _is_false(skip):
            return True
    if build:
        if _is_true(build):
            return True
        if _is_false(build):
            return False
    return False


# ==================== 빌드 후 처리 ====================
def post_build_automation():
    """빌드 완료 후 자동화 처리"""
    # 외부 패키저가 수행 중이면 내부 패키징을 건너뜁니다.
    if os.environ.get("WF_EXTERNAL_PACKAGER", "").strip().lower() in ("1", "true", "yes", "on"):
        print("⏭ WF_EXTERNAL_PACKAGER=1 감지: spec 내부 post_build_automation 생략")
        return True
    dist_dir = SPEC_DIR / "dist" / APP_NAME

    if not dist_dir.exists():
        print(f"❌ 빌드 결과물을 찾을 수 없습니다: {dist_dir}")
        return False

    print(f"\n🔧 빌드 후 자동화 처리 시작...")
    # 결과물 기본 경로(버전 기반) 정의: 폴더명에 버전만 사용 (타임스탬프 미사용)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")  # 메타데이터에만 사용
    version_tag = f"v{APP_VERSION}"
    portable_base_dir = BUILD_OUTPUT_DIR / f"{APP_NAME}_{version_tag}"
    portable_dir = portable_base_dir / f"{APP_NAME}_{version_tag}_portable"
    final_installer = None
    zip_file = None
    # 기존 폴더가 있으면 덮어쓰기 (삭제 후 재생성)
    if portable_base_dir.exists():
        print(f"📁 기존 폴더 발견: {portable_base_dir.name}")
        print(f"🔄 덮어쓰기 모드: 기존 내용 삭제 후 새 버전으로 교체")
        shutil.rmtree(portable_base_dir)
    
    portable_base_dir.mkdir(parents=True, exist_ok=True)

    # 1. NSIS 인스톨러 생성 (환경변수로 스킵 가능)
    if _should_build_installer():
        try:
            nsis_script = create_nsis_script()

            # makensis 실행 (전체 경로 사용)
            # CRITICAL FIX: NSIS 출력을 파일로 리다이렉트하여 파이프 버퍼 교착 상태 방지
            makensis_path = r"C:\Program Files (x86)\NSIS\makensis.exe"
            makensis_cmd = [makensis_path, "/V2", str(nsis_script)]
            nsis_log = SPEC_DIR / "nsis_build.log"

            with open(nsis_log, "w", encoding="utf-8") as log_file:
                result = subprocess.run(
                    makensis_cmd,
                    cwd=SPEC_DIR,
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    timeout=300,
                )  # 5분 타임아웃

            if result.returncode == 0:
                installer_file = SPEC_DIR / f"{APP_NAME}_{APP_VERSION}_installer.exe"
                if installer_file.exists():
                    print(f"✓ NSIS 인스톨러 생성 성공: {installer_file}")
                    # 인스톨러를 타임스탬프 폴더로 이동
                    final_installer = portable_base_dir / f"{APP_NAME}_{version_tag}_installer.exe"
                    shutil.move(str(installer_file), str(final_installer))
                    print(f"✓ 최종 인스톨러: {final_installer}")
                else:
                    print(f"❌ 인스톨러 파일 생성 실패")
            else:
                print(f"❌ NSIS 컴파일 실패 (로그: {nsis_log})")
                try:
                    with open(nsis_log, "r", encoding="utf-8") as f:
                        print(f.read()[-500:])  # 마지막 500자만 출력
                except:
                    pass

        except subprocess.TimeoutExpired:
            print(f"❌ NSIS 컴파일 타임아웃 (5분 초과)")
        except FileNotFoundError:
            print(f"❌ makensis를 찾을 수 없습니다. NSIS가 설치되어 있는지 확인하세요.")
        except Exception as e:
            print(f"❌ 인스톨러 생성 중 오류: {e}")
    else:
        print(
            "⏭  환경변수에 의해 NSIS 인스톨러 생성 단계를 건너뜁니다 (WF_SKIP_INSTALLER/WF_BUILD_INSTALLER)."
        )

    # 2. 포터블 버전 생성 (동일 타임스탬프 경로 사용)
    shutil.copytree(dist_dir, portable_dir)
    
    # .wf_rpa 폴더 제거 (포터블 버전에서는 불필요)
    wf_rpa_in_portable = portable_dir / ".wf_rpa"
    if wf_rpa_in_portable.exists():
        shutil.rmtree(wf_rpa_in_portable)
        print(f"✓ .wf_rpa 폴더 제거됨 (포터블 버전)")

    # 포터블 실행 배치 파일 생성
    bat_lines = [
        "@echo off",
        "chcp 65001 > nul",
        'cd /d "%~dp0"',
        "echo ========================================",
        "echo {APP_NAME} (포터블 버전)",
        "echo ========================================",
        "echo.",
        '"{APP_NAME}.exe"',
    ]

    with open(portable_dir / f"run_{APP_NAME}.bat", "w", encoding="cp949") as f:
        f.write("\n".join(bat_lines))

    print(f"✓ 포터블 버전 생성: {portable_dir}")

    # 3. 압축 파일 생성
    try:
        zip_file = portable_base_dir / f"{APP_NAME}_{version_tag}_portable.zip"
        shutil.make_archive(str(zip_file.with_suffix("")), "zip", portable_dir)
        print(f"✓ 포터블 압축 파일: {zip_file}")
    except Exception as e:
        print(f"⚠️ 압축 파일 생성 실패: {e}")

    # 메타데이터 및 체크섬 생성
    try:

        def sha256sum(p: Path) -> str:
            h = hashlib.sha256()
            with open(p, "rb") as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b""):
                    h.update(chunk)
            return h.hexdigest()

        metadata_dir = portable_base_dir / "metadata"
        metadata_dir.mkdir(parents=True, exist_ok=True)

        try:
            import PyInstaller as _PI

            pyinstaller_version = getattr(_PI, "__version__", None)
        except Exception:
            pyinstaller_version = None

        def _git_commit():
            try:
                r = subprocess.run(
                    ["git", "rev-parse", "--short", "HEAD"],
                    cwd=WORKSPACE_ROOT,
                    capture_output=True,
                    text=True,
                    timeout=3,
                )
                return r.stdout.strip() if r.returncode == 0 else None
            except Exception:
                return None

        build_info = {
            "app_name": APP_NAME,
            "app_display_name": APP_DISPLAY_NAME,
            "full_version": f"v{APP_VERSION}",
            "build_timestamp": timestamp,
            "python_version": sys.version,
            "pyinstaller_version": pyinstaller_version,
            "git_commit": _git_commit(),
            "artifacts": {},
        }

        checksums_lines = []

        if final_installer and Path(final_installer).exists():
            inst_sha = sha256sum(final_installer)
            build_info["artifacts"]["installer"] = {
                "path": str(final_installer),
                "size_bytes": final_installer.stat().st_size,
                "sha256": inst_sha,
            }
            checksums_lines.append(f"{inst_sha}  {final_installer.name}")

        if zip_file and Path(zip_file).exists():
            zip_sha = sha256sum(zip_file)
            build_info["artifacts"]["portable_zip"] = {
                "path": str(zip_file),
                "size_bytes": zip_file.stat().st_size,
                "sha256": zip_sha,
            }
            checksums_lines.append(f"{zip_sha}  {zip_file.name}")

        build_info["artifacts"]["portable_dir"] = str(portable_dir)

        with open(metadata_dir / "build_info.json", "w", encoding="utf-8") as f:
            json.dump(build_info, f, ensure_ascii=False, indent=2)

        with open(metadata_dir / "checksums.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(checksums_lines) + ("\n" if checksums_lines else ""))

        print(f"✓ 메타데이터 생성: {metadata_dir}")
    except Exception as e:
        print(f"⚠️ 메타데이터 생성 실패: {e}")

    # 4. 빌드 임시 파일 정리
    temp_dirs = [
        SPEC_DIR / "build",
        SPEC_DIR / "dist",
        SPEC_DIR / "__pycache__",
        SPEC_DIR / "installer_resources",
    ]

    for temp_dir in temp_dirs:
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)

    # 임시 파일들 정리
    temp_files = [SPEC_DIR / f"{APP_NAME}_installer.nsi"]

    for temp_file in temp_files:
        if temp_file.exists():
            temp_file.unlink()

    print(f"✓ 임시 파일 정리 완료")

    print(f"\\n🎉 빌드 및 패키징 완료!")
    print(f"📁 결과물 위치: {portable_base_dir}")
    print(f"📦 포터블 폴더: {portable_dir}")

    return True


# ==================== PyInstaller 설정 ====================
def collect_essential_resources():
    """필수 리소스 파일들 수집"""
    datas = []

    # 버전 정보는 config/korean_filename_normalizer/settings.json에 포함 (version.json 제거됨)

    # config 폴더
    config_dir = SPEC_DIR / "config"
    
    # Google Service Account 자격증명
    for silver_file in config_dir.glob(".silver-argon-*.json"):
        datas.append((str(silver_file), ".wf_rpa"))
        print(f"✓ 자격증명 파일 번들: {silver_file.name}")
    
    if config_dir.exists():
        datas.append((str(config_dir), "config"))
    
    # settings.json을 .wf_rpa/korean_filename_normalizer/ 위치로 번들링
    settings_src = config_dir / "korean_filename_normalizer" / "settings.json"
    if settings_src.exists():
        datas.append((str(settings_src), ".wf_rpa/korean_filename_normalizer"))
        print(f"✓ settings.json 번들링: .wf_rpa/korean_filename_normalizer/")

    # res 폴더
    res_dir = SPEC_DIR / "res"
    if res_dir.exists():
        datas.append((str(res_dir), "res"))

    # wf_rpa_config.json 번들링 (email_settings 포함)
    user_home = prepare_user_configs()
    wf_rpa_config_file = user_home / ".wf_rpa" / "wf_rpa_config.json"
    if wf_rpa_config_file.exists():
        datas.append((str(wf_rpa_config_file), ".wf_rpa"))
        print(f"✓ wf_rpa_config.json 번들링됨 (email_settings 포함)")

    return datas


# ==================== 라이브러리 직접 수집 ====================
def collect_missing_libraries():
    """PyInstaller가 수집하지 못하는 라이브러리들을 직접 복사"""
    import importlib.util
    
    datas = []
    binaries = []
    
    # 필수 라이브러리 목록
    required_libs = ['ntplib', 'gspread', 'requests', 'urllib3', 'google']
    app_libs = ['openpyxl']  # korean_filename_normalizer용
    
    all_libs = required_libs + app_libs
    
    for lib_name in all_libs:
        try:
            spec = importlib.util.find_spec(lib_name)
            if spec and spec.origin:
                lib_path = Path(spec.origin).parent
                if lib_path.exists():
                    datas.append((str(lib_path), lib_name))
                    print(f"✓ 라이브러리 직접 수집: {lib_name} from {lib_path}")
            else:
                print(f"⚠ 라이브러리 미설치: {lib_name}")
        except Exception as e:
            print(f"⚠ 라이브러리 수집 실패: {lib_name} - {e}")
    
    return datas, binaries


# collect_missing_libraries() 실행
# lib_datas, lib_binaries = collect_missing_libraries()  # DISABLED: 불필요한 중복 복사 (254MB 절약)

block_cipher = None

# 분석 단계
a = Analysis(
    [str(SPEC_DIR / "ui_main.py")],
    pathex=[str(SPEC_DIR), str(COMMON_DIR)],
    binaries=[],  # lib_binaries 제거
    datas=collect_essential_resources(),  # lib_datas 제거 - PyInstaller가 이미 모든 라이브러리 수집함
    hiddenimports=get_optimized_hidden_imports() + ["cpuinfo.cpuinfo", "ntplib", "google.auth.transport.urllib3"],
    hookspath=[str(SPEC_DIR)],  # hook 파일들 경로
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # GUI 프레임워크 제외 (Tkinter만 사용)
        "PyQt5",
        "PyQt5.QtCore",
        "PyQt5.QtGui",
        "PyQt5.QtWidgets",
        "PyQt6",
        "PySide2",
        "PySide6",
        "wx",
        # 이미지/CV 라이브러리 제외 (PyAutoGUI는 PIL 필요하므로 PIL 제외 제거)
        "cv2",
        "matplotlib",
        "scipy",
        "sklearn",
        "seaborn",
        "plotly",
        # ML/DL 프레임워크
        "tensorflow",
        "torch",
        "keras",
        # 개발 도구
        "jupyter",
        "IPython",
        "notebook",
        "jupyter_client",
        "jupyter_core",
        "jinja2",
        "sip",
        "bokeh",
        "altair",
        "statsmodels",
        "sympy",
        # 테스트 프레임워크
        "pytest",
        "unittest",
        "nose",
        "mock",
        # NOTE: pandas, numpy, openpyxl은 Excel 처리를 위해 포함됨
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# PYZ 압축
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# EXE 생성 (최적화된 onedir 방식 - 빠른 로딩)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=DEBUG_BUILD,  # 디버그 모드 플래그로 제어
    bootloader_ignore_signals=False,
    strip=False,  # Windows에서 strip 도구 없음으로 비활성화
    upx=False,  # UPX 비활성화로 로딩 시간 단축
    console=DEBUG_BUILD,  # 디버그 시 콘솔 출력, 릴리스 시 GUI 전용
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # 아이콘: 고정 KFN.ico (fallback 제거)
    # 아이콘 생성 보장 후 사용
    icon=str(ensure_b2e_icon()),
    version="version_info.txt" if Path("version_info.txt").exists() else None,
)

# COLLECT - 최적화된 onedir 버전 생성
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,  # Windows에서 strip 도구 없음으로 비활성화
    upx=False,  # UPX 비활성화로 빠른 로딩
    name=APP_NAME,
)

# ==================== 빌드 완료 후 자동 실행 ====================
# import atexit

# atexit.register(post_build_automation)  # DISABLED: 빌드 중단 문제 해결

print(f"\\n✅ {APP_NAME} 최적화 빌드 설정 완료")
print(
    f"🔧 INSTALLER_DECISION should_build_installer={_should_build_installer()} (WF_SKIP_INSTALLER={os.environ.get('WF_SKIP_INSTALLER')}, WF_BUILD_INSTALLER={os.environ.get('WF_BUILD_INSTALLER')})"
)
print(f"📋 히든 임포트: {len(get_optimized_hidden_imports())}개 (필수 모듈 포함)")
print(f"📦 리소스 파일: 수집 중...")
print(f"🎯 타겟: 빠른 로딩 onedir + 포터블 버전")
print(f"⚡ 최적화: UPX 비활성화, 대용량 라이브러리만 제외, 디버그 심볼 제거")
