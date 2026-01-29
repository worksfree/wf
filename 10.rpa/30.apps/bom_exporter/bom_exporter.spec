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
if sys.platform == 'win32':
    try:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except:
        pass  # 설정 실패 시 무시

# ==================== 유효한 기본 아이콘 생성 ====================
def ensure_b2e_icon():
    """res/B2E.ico를 생성(또는 교체)합니다. 16x16 32-bit BGRA BMP 기반 ICO.
    외부 라이브러리 없이 순수 바이트로 만듭니다."""
    res_dir = Path('res')
    res_dir.mkdir(exist_ok=True)
    ico_path = res_dir / 'B2E.ico'

    import struct
    width = 16
    height = 16
    biHeight = height * 2  # XOR + AND
    biSizeImage = width * height * 4

    # BITMAPINFOHEADER
    bih = struct.pack('<IIIHHIIIIII',
                      40,      # biSize
                      width,   # biWidth
                      biHeight,# biHeight
                      1,       # biPlanes
                      32,      # biBitCount
                      0,       # biCompression
                      biSizeImage,
                      0, 0, 0, 0)

    # Solid blue-ish (BGRA) pixels
    b, g, r, a = 0x8F, 0xA3, 0xFF, 0xFF
    xor_bitmap = bytes([b, g, r, a]) * (width * height)

    # AND mask (all opaque). Each row padded to 32 bits: 16 pixels -> 2 bytes, pad to 4 bytes per row
    and_row = b'\x00\x00\x00\x00'
    and_mask = and_row * height

    bmp_data = bih + xor_bitmap + and_mask

    bytes_in_res = len(bmp_data)
    icondir = struct.pack('<HHH', 0, 1, 1)
    entry = struct.pack('<BBBBHHII',
                        width if width < 256 else 0,
                        height if height < 256 else 0,
                        0, 0, 1, 32,
                        bytes_in_res,
                        6 + 16)

    ico_bytes = icondir + entry + bmp_data
    with open(ico_path, 'wb') as f:
        f.write(ico_bytes)
    return ico_path

# ==================== 경로 설정 (버전 함수보다 먼저 정의) ====================
try:
    SPEC_DIR = Path(__file__).resolve().parent
except NameError:
    SPEC_DIR = Path(os.getcwd())

# 작업 디렉토리를 spec 파일 위치로 강제 변경 (경로 문제 원천 차단)
os.chdir(str(SPEC_DIR))
print(f"[SPEC] Working directory set to: {SPEC_DIR}")

WORKSPACE_ROOT = SPEC_DIR.parent.parent
COMMON_DIR = WORKSPACE_ROOT / '10.common'
COMMON_CONFIG_DIR = COMMON_DIR / 'config'  # 공통 config 폴더

# ==================== 버전 관리 ====================
def load_and_increment_version():
    """settings.json에서 버전을 읽고 자동으로 증가시킴
    - 4자리 버전: v0.7.0.0 형식
    - 빌드마다 마지막 자리와 build_count 증가
    - 개발자/관리자용: 전체 버전 (0.7.0.1)
    - 사용자용: 앞 2자리만 (v0.7)
    """
    settings_file = COMMON_CONFIG_DIR / 'bom_exporter' / 'settings.json'
    default_version = [0, 7, 0, 0]
    
    # 기존 버전 읽기 (runtime_config에서만 읽기)
    if settings_file.exists():
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # runtime_config.full_version 사용
                full_version = data.get('runtime_config', {}).get('full_version', 'v0.7.0.0')
                # v0.9.1.2 -> [0, 9, 1, 2]
                version = [int(x) for x in full_version.lstrip('v').split('.')]
        except Exception:
            version = default_version
    else:
        version = default_version
    
    # 버전 증가 로직: 마지막 자리부터 증가, 9 넘으면 자리 올림
    version[3] += 1
    if version[3] > 9:
        version[3] = 0
        version[2] += 1
        if version[2] > 9:
            version[2] = 0
            version[1] += 1
            if version[1] > 9:
                version[1] = 0
                version[0] += 1

    # settings.json 전체 읽기
    if settings_file.exists():
        with open(settings_file, 'r', encoding='utf-8') as f:
            settings_data = json.load(f)
    else:
        settings_data = {'runtime_config': {}, 'ui_config': {}}
    
    # 버전 정보 업데이트 (runtime_config에만 저장)
    if 'runtime_config' not in settings_data:
        settings_data['runtime_config'] = {}
    
    new_version = f'v{version[0]}.{version[1]}.{version[2]}.{version[3]}'
    new_build_count = settings_data.get('runtime_config', {}).get('build_count', 0) + 1
    
    # runtime_config에 저장
    settings_data['runtime_config']['full_version'] = new_version
    settings_data['runtime_config']['build_count'] = new_build_count
    
    # 저장
    with open(settings_file, 'w', encoding='utf-8') as f:
        json.dump(settings_data, f, ensure_ascii=False, indent=2)
    
    version_data = {
        'full_version': f'{version[0]}.{version[1]}.{version[2]}.{version[3]}',
        'display_version': f'v{version[0]}.{version[1]}',
        'build_count': settings_data['runtime_config']['build_count']
    }
    
    print(f"✓ 버전 증가: {version_data['full_version']} (빌드 #{version_data['build_count']})")
    print(f"  - 전체 버전(개발자용): {version_data['full_version']}")
    print(f"  - 표시 버전(사용자용): {version_data['display_version']}")
    
    return version_data

# 버전 정보 로드
VERSION_INFO = load_and_increment_version()
APP_VERSION_FULL = VERSION_INFO['full_version'].lstrip('v')  # 4자리: 0.7.0.1 (v 제거)
APP_VERSION_DISPLAY = VERSION_INFO['display_version']  # 2자리: v0.7

# ==================== 앱 정보 설정 (각 앱별로 수정) ====================
APP_NAME = 'bom_exporter'  # 빌드할 앱 이름
APP_VERSION = APP_VERSION_FULL  # 내부적으로 전체 버전 사용
APP_DISPLAY_NAME = 'Bom Exporter'
APP_DESCRIPTION = 'BOM Excel 변환 도구'
APP_PUBLISHER = 'WorksFree Co., Ltd.'
APP_URL = 'https://worksfree.co.kr'
APP_CONTACT = 'support@worksfree.co.kr'

# ==================== 디버그 및 최적화 설정 ====================
DEBUG_BUILD = False       # False: 릴리스 모드 (console 숨김)
STARTUP_PROFILING = False # False: 프로파일링 비활성화 (성능 최적화)
TEMPLATES_DIR = WORKSPACE_ROOT / 'templates'
BUILD_OUTPUT_DIR = Path('D:/release/candidates')

# WorksFree 앱 목록 (NSIS 중복 설치 방지용)
WORKSFREE_APPS = [
    'bom_exporter',
    'dwg_classifier', 
    'conversion_verifier',
    'korean_filename_normalizer',
    'file_list_check',
    'spreadsheet_manager'
]

print(f"\\n{'='*80}")
print(f"WorksFree Bom Exporter v{APP_VERSION} 통합 빌드 시작")
print(f"{'='*80}")


# ==================== 숨김 파일 처리 ====================
def set_hidden_attribute(file_path):
    """Windows에서 파일을 숨김 처리합니다."""
    try:
        import platform
        if platform.system() == "Windows":
            import ctypes
            FILE_ATTRIBUTE_HIDDEN = 0x02
            attrs = ctypes.windll.kernel32.GetFileAttributesW(str(file_path))
            if attrs != -1:
                ctypes.windll.kernel32.SetFileAttributesW(
                    str(file_path), attrs | FILE_ATTRIBUTE_HIDDEN
                )
            else:
                ctypes.windll.kernel32.SetFileAttributesW(str(file_path), FILE_ATTRIBUTE_HIDDEN)
            print(f"  → 숨김 처리: {file_path.name}")
    except Exception as e:
        print(f"  ⚠️ 숨김 처리 실패: {file_path.name} - {e}")


# ==================== 사용자 홈 설정 파일 준비 ====================
def prepare_user_configs():
    """사용자 홈 디렉토리용 설정 파일들 준비
    config 폴더의 파일들을 빌드 시 번들링하기 위해 임시 폴더 생성
    """
    # config 폴더를 그대로 사용하되, 빌드용 임시 구조 생성
    home_dir = SPEC_DIR / 'build' / 'user_home_bundle'
    home_dir.mkdir(parents=True, exist_ok=True)
    
    wf_rpa_dir = home_dir / '.wf_rpa'
    app_dir = wf_rpa_dir / APP_NAME
    
    for directory in [wf_rpa_dir, app_dir]:
        directory.mkdir(parents=True, exist_ok=True)
    
    # 1. wf_rpa_config.json - 공통 config 폴더에서 복사 (관리자 이메일, Google Sheets 포함)
    source_config = COMMON_CONFIG_DIR / 'wf_rpa_config.json'
    
    if source_config.exists():
        target_file = wf_rpa_dir / 'wf_rpa_config.json'
        shutil.copy2(source_config, target_file)
        set_hidden_attribute(target_file)
        print(f"✓ wf_rpa_config.json 복사 완료 (email_settings, google_sheets 포함)")
    else:
        print(f"⚠️ wf_rpa_config.json을 찾을 수 없음: {source_config}")
    
    # 2. Google Credentials 복사 (.wf_rpa 루트에 직접 복사, wf_rpa_config와 동일 위치)
    google_creds_dev_found = False
    google_creds_release_found = False

    # 공통 config 폴더에서 실제 키 파일 찾기
    if COMMON_CONFIG_DIR.exists():
        # DEV용 자격증명 파일 (silver-argon)
        for json_file in COMMON_CONFIG_DIR.glob('silver-argon*.json'):
            target_file = wf_rpa_dir / json_file.name
            shutil.copy2(json_file, target_file)
            set_hidden_attribute(target_file)
            google_creds_dev_found = True
            print(f"✓ Google credentials (DEV) 포함 (.wf_rpa 루트): {json_file.name}")
            break
        
        # RELEASE용 자격증명 파일 (worksfree-b33a6b8f366b.json)
        for json_file in COMMON_CONFIG_DIR.glob('worksfree-*.json'):
            target_file = wf_rpa_dir / json_file.name
            shutil.copy2(json_file, target_file)
            set_hidden_attribute(target_file)
            google_creds_release_found = True
            print(f"✓ Google credentials (RELEASE) 포함 (.wf_rpa 루트): {json_file.name}")
            break
    
    if not google_creds_dev_found:
        print("⚠️ Google credentials (DEV)를 찾을 수 없습니다.")
    if not google_creds_release_found:
        print("⚠️ Google credentials (RELEASE)를 찾을 수 없습니다.")
    
    # 3. settings.json 처리: 버전 주입 + 사용자 경로 초기화
    source_settings = COMMON_CONFIG_DIR / 'bom_exporter' / 'settings.json'
    if source_settings.exists():
        with open(source_settings, 'r', encoding='utf-8') as f:
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
        bundled_settings = app_dir / 'settings.json'
        with open(bundled_settings, 'w', encoding='utf-8') as f:
            json.dump(settings_data, f, ensure_ascii=False, indent=2)
        
        set_hidden_attribute(bundled_settings)
        print(f"✓ settings.json 처리 완료 (.wf_rpa/{APP_NAME}/) - 버전: {APP_VERSION_FULL}, 빌드: #{VERSION_INFO['build_count']}")
    else:
        print(f"⚠️ settings.json을 찾을 수 없음: {source_settings}")
    
    # 4. policy.json 복사 (버전 정보는 settings.json의 runtime_config에만 있음)
    # policy.json은 identity + policy만 포함 (변하지 않는 값들)
    # 버전 정보는 settings.json의 runtime_config에만 있음
    # policy.json은 그대로 복사만 함 (버전 주입 안함)
    policy_src = COMMON_CONFIG_DIR / "bom_exporter" / "policy.json"
    if policy_src.exists():
        bundled_policy = app_dir / "policy.json"
        shutil.copy2(policy_src, bundled_policy)
        set_hidden_attribute(bundled_policy)
        print(f"✓ policy.json 복사 완료 (.wf_rpa/{APP_NAME}/)")
    
    print(f"✓ 사용자 설정 파일 준비 완료: {home_dir}")
    return home_dir

# ==================== NSIS 스크립트 생성 ====================
def create_nsis_script():
    """NSIS 인스톨러 스크립트 생성"""
    # 고정 아이콘: B2E.ico (요청에 따라 fallback 제거)
    # PyInstaller 단계에서 ensure_b2e_icon 수행되므로 바로 사용
    ensure_b2e_icon()
    icon_define = '!define MUI_ICON "res\\B2E.ico"\n!define MUI_UNICON "res\\B2E.ico"\n'

    nsis_script = f'''!include "MUI2.nsh"
!include "FileFunc.nsh"
!include "LogicLib.nsh"

; ==================== 기본 정보 ====================
Name "Bom Exporter v{APP_VERSION}"
OutFile "bom_exporter_{APP_VERSION}_installer.exe"
InstallDir "$PROGRAMFILES64\\WorksFree\\bom_exporter"
InstallDirRegKey HKLM "Software\\WorksFree\\bom_exporter" "InstallPath"
RequestExecutionLevel admin

; ==================== 버전 정보 ====================
VIProductVersion "{APP_VERSION}.0"
VIAddVersionKey "ProductName" "Bom Exporter"
VIAddVersionKey "CompanyName" "{APP_PUBLISHER}"
VIAddVersionKey "ProductVersion" "{APP_VERSION}"
VIAddVersionKey "FileVersion" "{APP_VERSION}.0"
VIAddVersionKey "FileDescription" "BOM Excel 변환 도구"
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
Var InstallDateStr
Var UpdateDateStr
Var ExistingInstallDate

; ==================== 사전 설치 검사 ====================
Function .onInit
    ; WorksFree 전역 설정 디렉토리 확인
    IfFileExists "$PROFILE\\.wf_rpa\\wf_rpa_config.json" 0 +3
        StrCpy $GlobalConfigExists "true"
        Goto +2
        StrCpy $GlobalConfigExists "false"
    
    ; Google Credentials 존재 확인 (실제 키 파일명으로 확인 - DEV 또는 RELEASE)
    IfFileExists "$PROFILE\\.wf_rpa\\silver-argon-445712-a0-7092493258f3.json" found_creds
    IfFileExists "$PROFILE\\.wf_rpa\\worksfree-b33a6b8f366b.json" found_creds not_found_creds
    found_creds:
        StrCpy $CredentialsExists "true"
        Goto check_first_app
    not_found_creds:
        StrCpy $CredentialsExists "false"
    
    check_first_app:
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
Section "!Bom Exporter (필수)" SecMain
    SectionIn RO ; 필수 섹션
    
    SetOutPath "$INSTDIR"
    
    ; 메인 앱 파일들 설치
    File /r "dist\\bom_exporter\\*.*"
    
    ; 레지스트리 등록
    ; InstallDate/LastUpdateDate = YYYYMMDD 형식 생성
    ${{GetTime}} "" "L" $0 $1 $2 $3 $4 $5 $6
    ; $0=Year, $1=Month, $2=Day (로컬)
    IntFmt $1 "%02d" $1
    IntFmt $2 "%02d" $2
    StrCpy $InstallDateStr "$0$1$2"
    StrCpy $UpdateDateStr "$InstallDateStr"

    ; 기존 InstallDate가 있으면 유지 (업데이트 시 덮어쓰지 않음)
    ReadRegStr $ExistingInstallDate HKLM "Software\\WorksFree\\bom_exporter" "InstallDate"
    StrCmp $ExistingInstallDate "" +2 0
        StrCpy $InstallDateStr "$ExistingInstallDate"
    WriteRegStr HKLM "Software\\WorksFree\\bom_exporter" "InstallPath" "$INSTDIR"
    WriteRegStr HKLM "Software\\WorksFree\\bom_exporter" "Version" "{APP_VERSION}"
    WriteRegStr HKLM "Software\\WorksFree\\bom_exporter" "DisplayName" "Bom Exporter v{APP_VERSION}"
    WriteRegStr HKLM "Software\\WorksFree\\bom_exporter" "Publisher" "{APP_PUBLISHER}"
    WriteRegStr HKLM "Software\\WorksFree\\bom_exporter" "InstallDate" "$InstallDateStr"
    WriteRegStr HKLM "Software\\WorksFree\\bom_exporter" "LastUpdateDate" "$UpdateDateStr"
    
    ; 프로그램 추가/제거 등록
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\bom_exporter" "DisplayName" "Bom Exporter v{APP_VERSION}"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\bom_exporter" "UninstallString" "$\\"$INSTDIR\\uninstall.exe$\\""
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\bom_exporter" "DisplayIcon" "$INSTDIR\\bom_exporter.exe"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\bom_exporter" "Publisher" "{APP_PUBLISHER}"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\bom_exporter" "DisplayVersion" "{APP_VERSION}"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\bom_exporter" "InstallLocation" "$INSTDIR"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\bom_exporter" "InstallDate" "$InstallDateStr"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\bom_exporter" "LastUpdateDate" "$UpdateDateStr"
    WriteRegDWORD HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\bom_exporter" "NoModify" 1
    WriteRegDWORD HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\bom_exporter" "NoRepair" 1
    
    ; 설치 크기 계산
    ${{GetSize}} "$INSTDIR" "/S=0K" $0 $1 $2
    IntFmt $0 "0x%08X" $0
    WriteRegDWORD HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\bom_exporter" "EstimatedSize" "$0"
    
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
        CreateDirectory "$PROFILE\\.wf_rpa\\bom_exporter"
        CreateDirectory "$PROFILE\\.wf_rpa\\credentials"
        CreateDirectory "$PROFILE\\.wf_rpa\\logs"
        
        ; 전역 설정 파일들 복사
        SetOutPath "$PROFILE\\.wf_rpa"
        File "build\\user_home_bundle\\.wf_rpa\\wf_rpa_config.json"
        
        ; 앱별 설정 파일 복사
        SetOutPath "$PROFILE\\.wf_rpa\\bom_exporter"
        File "build\\user_home_bundle\\.wf_rpa\\bom_exporter\\*.*"
        
        DetailPrint "✓ WorksFree 환경 설정 완료"
    ${{Else}}
        DetailPrint "기존 WorksFree 설정을 사용합니다."
        
        ; 앱별 설정 디렉토리만 생성
        CreateDirectory "$PROFILE\\.wf_rpa\\bom_exporter"
        SetOutPath "$PROFILE\\.wf_rpa\\bom_exporter"
        File "build\\user_home_bundle\\.wf_rpa\\bom_exporter\\*.*"
    ${{EndIf}}
SectionEnd

Section "Google Credentials" SecCredentials
    ; Credentials가 없을 때만 설치
    ${{If}} $CredentialsExists == "false"
        DetailPrint "Google Service Account 인증 정보를 설치합니다..."
        
        SetOutPath "$PROFILE\\.wf_rpa"
        File "build\\user_home_bundle\\.wf_rpa\\silver-argon-*.json"
        File "build\\user_home_bundle\\.wf_rpa\\worksfree-*.json"
        
        DetailPrint "✓ Google 인증 정보 설치 완료 (.wf_rpa 루트)"
    ${{Else}}
        DetailPrint "기존 Google 인증 정보를 사용합니다."
    ${{EndIf}}
SectionEnd

Section "바탕화면 바로가기" SecDesktopShortcut
    CreateShortCut "$DESKTOP\\Bom Exporter.lnk" "$INSTDIR\\bom_exporter.exe"
SectionEnd

Section "시작 메뉴 항목" SecStartMenu
    CreateDirectory "$SMPROGRAMS\\WorksFree"
    CreateShortCut "$SMPROGRAMS\\WorksFree\\Bom Exporter.lnk" "$INSTDIR\\bom_exporter.exe"
    CreateShortCut "$SMPROGRAMS\\WorksFree\\Bom Exporter 제거.lnk" "$INSTDIR\\uninstall.exe"
SectionEnd

; ==================== 컴포넌트 설명 ====================
!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
    !insertmacro MUI_DESCRIPTION_TEXT ${{SecMain}} "BOM Excel 변환 도구의 핵심 실행 파일들을 설치합니다."
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
    ExecWait '"$INSTDIR\\bom_exporter.exe" --register-install' $0
    
    DetailPrint "Bom Exporter 설치가 완료되었습니다."
FunctionEnd

; ==================== 제거 섹션 ====================
Section "Uninstall"
    DetailPrint "Bom Exporter를 제거합니다..."
    
    ; 실행 중인 프로세스 강제 종료 (오류 무시)
    nsExec::Exec 'taskkill /F /IM bom_exporter.exe /T'
    Sleep 1000
    
    ; 앱 파일들 제거
    DetailPrint "프로그램 파일을 제거합니다..."
    RMDir /r "$INSTDIR"
    
    ; 레지스트리 제거
    DetailPrint "레지스트리 정보를 제거합니다..."
    DeleteRegKey HKLM "Software\\WorksFree\\bom_exporter"
    DeleteRegKey HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\bom_exporter"
    
    ; 바로가기 제거
    DetailPrint "바로가기를 제거합니다..."
    Delete "$DESKTOP\\Bom Exporter.lnk"
    Delete "$SMPROGRAMS\\WorksFree\\Bom Exporter.lnk"
    Delete "$SMPROGRAMS\\WorksFree\\Bom Exporter 제거.lnk"
    
    ; WorksFree 폴더 정리 (다른 앱이 없으면)
    RMDir "$SMPROGRAMS\\WorksFree"
    
    ; 사용자 데이터 제거 옵션
    MessageBox MB_YESNO "사용자 설정, 크레딧, 로그를 함께 제거하시겠습니까?$\\n$\\n• 설정 파일: %USERPROFILE%\\.wf_rpa\\bom_exporter$\\n• 크레딧 정보 및 사용 기록$\\n• 로그 파일$\\n$\\n'아니오'를 선택하면 재설치시 기존 데이터를 유지할 수 있습니다." IDNO skip_user_data
        DetailPrint "사용자 데이터를 제거합니다..."
        RMDir /r "$PROFILE\\.wf_rpa\\bom_exporter"
        
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
    
    DetailPrint "✓ Bom Exporter 제거 완료"
    MessageBox MB_OK "Bom Exporter가 성공적으로 제거되었습니다."
SectionEnd
'''
    
    nsis_file = SPEC_DIR / f'bom_exporter_installer.nsi'
    with open(nsis_file, 'w', encoding='utf-8-sig') as f:  # UTF-8 BOM 추가
        f.write(nsis_script)
    
    # 아이콘 파일 복사
    icon_source = SPEC_DIR / 'res' / 'B2E.ico'
    if icon_source.exists():
        # NSIS 스크립트와 같은 디렉토리에 res 폴더 생성 및 아이콘 복사
        res_dir = SPEC_DIR / 'res'
        res_dir.mkdir(exist_ok=True)
        icon_target = res_dir / 'B2E.ico'
        if not icon_target.exists() or icon_source.stat().st_mtime > icon_target.stat().st_mtime:
            shutil.copy2(icon_source, icon_target)
        print(f"✓ 아이콘 파일 준비: {icon_target}")
    
    print(f"✓ NSIS 스크립트 생성: {nsis_file}")
    return nsis_file

# ==================== 라이브러리 직접 복사 ====================
def collect_missing_libraries():
    """PyInstaller가 수집하지 못하는 라이브러리들을 직접 복사"""
    import importlib.util
    import site
    
    datas = []
    binaries = []
    
    # 필수 라이브러리 목록
    required_libs = ['ntplib', 'gspread', 'requests', 'urllib3', 'google']
    app_libs = ['keyboard', 'pyautogui', 'pywinauto', 'openpyxl']
    
    all_libs = required_libs + app_libs
    
    for lib_name in all_libs:
        try:
            # 라이브러리의 실제 경로 찾기
            spec = importlib.util.find_spec(lib_name)
            if spec and spec.origin:
                lib_path = Path(spec.origin).parent
                if lib_path.exists():
                    # 라이브러리 전체를 datas로 추가
                    datas.append((str(lib_path), lib_name))
                    print(f"✓ 라이브러리 직접 수집: {lib_name} from {lib_path}")
            else:
                print(f"⚠ 라이브러리 미설치: {lib_name}")
        except Exception as e:
            print(f"⚠ 라이브러리 수집 실패: {lib_name} - {e}")
    
    return datas, binaries

# ==================== 리소스 수집 ====================
def collect_essential_resources():
    """필수 리소스 파일들만 수집 (최적화됨)"""
    datas = []
    
    # 1. WorksFree 필수 공통 모듈만 (실제 사용되는 것만)
    essential_modules = [
        'wf_log.py',
        'wf_credit_manager.py',  # 크레딧 시스템 필수
        'wf_register.py',        # 등록/인증 필수
        'wf_ui_adaptive.py',     # 적응형 UI 통합 모듈
    ]
    
    for module in essential_modules:
        module_path = COMMON_DIR / module
        if module_path.exists():
            datas.append((str(module_path), '.'))
            print(f"포함됨: {module}")
        else:
            print(f"누락됨: {module}")
    
    # 2. 로컬 앱 모듈들 (앱 디렉토리의 .py 파일들)
    local_modules = ['automation.py', 'config.py', 'ui_setting.py']
    for module in local_modules:
        module_path = SPEC_DIR / module
        if module_path.exists():
            datas.append((str(module_path), '.'))
            print(f"로컬 모듈 포함: {module}")
    
    # 3. 앱별 정책 파일: policy.json으로 통합됨 (credit_policy.json 제거)
    # policy.json은 앱 실행 시 자동 생성됨
    
    # 3.5. 버전 정보는 settings.json에 포함되어 있음 (version.json 제거됨)
    
    # 4. 사용자 홈 설정 파일들 (.wf_rpa 루트에 배치)
    user_home = prepare_user_configs()
    # wf_rpa_config.json을 .wf_rpa 루트에 번들
    if user_home:
        wf_rpa_dir = user_home / '.wf_rpa'
        wf_rpa_config = wf_rpa_dir / 'wf_rpa_config.json'
        if wf_rpa_config.exists():
            datas.append((str(wf_rpa_config), '.wf_rpa'))
            print(f"설정 파일 번들: {wf_rpa_config.name}")
        
        # settings.json을 .wf_rpa/bom_exporter/에 번들
        app_dir = wf_rpa_dir / APP_NAME
        app_settings = app_dir / 'settings.json'
        if app_settings.exists():
            datas.append((str(app_settings), f'.wf_rpa/{APP_NAME}'))
            print(f"설정 파일 번들: settings.json → .wf_rpa/{APP_NAME}/")
        
        # policy.json을 .wf_rpa/bom_exporter/에 번들
        policy_file = app_dir / 'policy.json'
        if policy_file.exists():
            datas.append((str(policy_file), f'.wf_rpa/{APP_NAME}'))
            print(f"설정 파일 번들: policy.json → .wf_rpa/{APP_NAME}/")
    
    # 4.5. config 폴더 구조로도 번들 (wf_credit_manager가 config 경로에서 검색)
    config_app_dir = SPEC_DIR / 'config' / APP_NAME
    if config_app_dir.exists():
        policy_source = config_app_dir / 'policy.json'
        if policy_source.exists():
            datas.append((str(policy_source), f'config/{APP_NAME}'))
            print(f"설정 파일 번들: policy.json → config/{APP_NAME}/")
    
    # 5. Google Service Account 자격증명 파일 (.wf_rpa 루트에 배치)
    # DEV용 자격증명 (silver-argon-*.json) - backup 파일 제외
    for silver_file in COMMON_CONFIG_DIR.glob("silver-argon-*.json"):
        if 'backup' not in silver_file.name.lower():
            datas.append((str(silver_file), '.wf_rpa'))
            print(f"자격증명 파일 번들 (DEV): {silver_file.name}")
    
    # RELEASE용 자격증명 (worksfree-*.json) - backup 파일 제외
    for worksfree_file in COMMON_CONFIG_DIR.glob("worksfree-*.json"):
        if 'backup' not in worksfree_file.name.lower():
            datas.append((str(worksfree_file), '.wf_rpa'))
            print(f"자격증명 파일 번들 (RELEASE): {worksfree_file.name}")
    
    # 6. 앱별 리소스 (SVG 파일 제외 - 소스용이므로 패키징 불필요)
    app_res_dir = SPEC_DIR / 'res'
    if app_res_dir.exists():
        for file_path in app_res_dir.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() != '.svg':
                rel_path = file_path.relative_to(app_res_dir)
                datas.append((str(file_path), f'res/{rel_path.parent}' if rel_path.parent != Path('.') else 'res'))
    
    # 7. 인스톨러 리소스들  
    installer_resources = [
        'license.txt',
        'icon.ico',
        'readme.txt'
    ]
    
    for resource in installer_resources:
        resource_path = SPEC_DIR / resource
        if resource_path.exists():
            datas.append((str(resource_path), '.'))
    
    # 8. policy.json은 사용자 홈 번들(.wf_rpa)에 포함됨 - 여기서는 제외
    # (prepare_home_config 함수에서 .wf_rpa/bom_exporter/policy.json로 복사됨)

    # 9. MANUAL.pdf 포함 (있는 경우에만)
    manual_patterns = [
        f'{APP_NAME.upper()}_USER_MANUAL.pdf',
        f'{APP_DISPLAY_NAME.upper().replace(" ", "_")}_USER_MANUAL.pdf',
        'MANUAL.pdf',
        '*USER_MANUAL.pdf'
    ]
    for pattern in manual_patterns:
        manual_files = list(SPEC_DIR.glob(pattern))
        if manual_files:
            manual_pdf = manual_files[0]
            datas.append((str(manual_pdf), '.'))
            print(f"매뉴얼 포함: {manual_pdf.name}")
            break

    # print(f"필수 리소스만 수집 완료: {len(datas)}개 파일")
    return datas

# ==================== 히든 임포트 정의 ====================
def get_optimized_hidden_imports():
    """최적화된 숨겨진 import 모듈들 - 필수만 포함"""
    # bom_exporter에 실제 필요한 모듈만
    essential_imports = [
        # WorksFree 핵심 (모든 wf_ 모듈 포함)
        'wf_log',
        'wf_credit_manager',
            'wf_credit_session_utils',
        'wf_app_init_helpers',
        'wf_register',
        'wf_ui_adaptive',        # 적응형 UI 통합 모듈
        'wf_email',
        'wf_gen_code',
        'wf_googlesheets_manager',
        'wf_hwinfo',
        'wf_license',
        
        # WF-ACT 테스트 인프라
        'test_server',  # IPC test server for certification
        
        # GUI 관련 (필수만)
        'tkinter', 
        'tkinter.ttk', 
        'tkinter.messagebox', 
        'tkinter.filedialog',
        'pyautogui',         # UI 자동화 (필요시)
        'pyscreeze',         # pyautogui 의존성
        'pymsgbox',          # pyautogui 의존성
        'pytweening',        # pyautogui 의존성
        
        # PIL/Pillow (pyscreeze 의존성)
        'PIL',
        'PIL.Image',
        'PIL.ImageGrab',
        'PIL.ImageDraw',
        'PIL.ImageFont',
        
        # 앱별 핵심 기능 (앱에 따라 조정)
        'unicodedata',       # 문자 처리
        're',               # 정규식
        'os.path',
        'pathlib',
        'shutil',
        'argparse',
        'time',
        
        # PyInstaller 런타임 필수
        'zipfile',           # PyInstaller 런타임 훅 필요
        'multiprocessing',   # freeze_support 필요
        
        # Python 3.14 호환성 (collections.abc 명시적 포함)
        'collections',
        'collections.abc',
        
        # 기본 시스템
        'json',
        'datetime',
        'threading',
        
        # 하드웨어 정보 (wf_hwinfo.py에서 필요)
        'cpuinfo.cpuinfo',   # CPU 정보
        'ntplib',            # 시간 동기화
        
        # Automation 모듈 (automation.py에서 필요)
        'keyboard',          # 키보드 이벤트 (Caps Lock 토글)
        'psutil',            # 프로세스/메모리 모니터링
        'tqdm',              # 진행률 표시
        
        # Google Sheets 연동 (wf_googlesheets_manager.py에서 필요)
        'gspread',
        'google.auth',
        'google.auth.transport.requests',
        'google.oauth2.service_account',
        'google.auth.transport.urllib3',
        'google.auth.transport._http_client',
        'google.auth._helpers',
        'google.auth.exceptions',
        'google.oauth2.credentials',
    # 일부 버전에서는 _helpers 모듈이 존재하지 않을 수 있어 동적 포함 처리
        'requests',
        'requests.adapters',
        'requests.auth',
        'requests.cookies', 
        'requests.exceptions',
        'requests.models',
        'requests.sessions',
        'requests.structures',
        'requests.utils',
        'urllib3',
        'urllib3.connection',
        'urllib3.connectionpool',
        'urllib3.exceptions',
        'urllib3.poolmanager',
        'urllib3.response',
        'urllib3.util',
        'urllib3.util.retry',
        'urllib3.util.ssl_',
        'certifi',
        'charset_normalizer'
    ]
    
    # 앱별 특화 imports
    app_specific = {
        'bom_exporter': [  # ← 수정: bom2excel → bom_exporter
            'pyautogui', 
            'openpyxl', 'openpyxl.utils', 'openpyxl.styles', 
            'keyboard', 
            'pyperclip', 
            'ntplib',
            'pywinauto', 'pywinauto.application', 'pywinauto.findwindows', 
            'pywinauto.keyboard', 'pywinauto.mouse', 'pywinauto.timings',
            'pywinauto.controls', 'pywinauto.controls.uiawrapper', 
            'pywinauto.controls.win32_controls', 'pywinauto.controls.common_controls',
            'pywinauto.base_wrapper', 'pywinauto.element_info',
            'comtypes', 'comtypes.client', 'comtypes.gen',
            'win32timezone', 'win32api', 'win32con', 'win32com', 'win32com.client',
            'pywintypes', 'pythoncom',
            'tqdm', 
            'psutil'
        ],
        'dwg_classifier': ['glob', 'zipfile', 'tempfile'],
        'conversion_verifier': ['difflib', 'filecmp'],
        'korean_filename_normalizer': ['unicodedata', 're'],
        'file_list_check': ['csv', 'xml.etree.ElementTree'],
        'spreadsheet_manager': ['xlrd', 'xlwt', 'xlutils']
    }
    
    if APP_NAME in app_specific:
        essential_imports.extend(app_specific[APP_NAME])
    # google.oauth2._helpers 존재 시만 추가
    try:
        import importlib
        if importlib.util.find_spec('google.oauth2._helpers') is not None:
            essential_imports.append('google.oauth2._helpers')
    except Exception:
        pass
    
    # 🔧 hook-*.py 파일들이 하던 작업을 직접 처리 (collect_all로 자동 수집)
    from PyInstaller.utils.hooks import collect_all
    
    additional_imports = []
    hook_modules = ['gspread', 'google.auth', 'ntplib', 'requests', 'urllib3']
    for module in hook_modules:
        try:
            datas, binaries, hiddenimports = collect_all(module)
            if hiddenimports:
                additional_imports.extend(hiddenimports)
        except Exception as e:
            print(f"⚠️ Warning: Could not collect imports for {module}: {e}")
    
    # 중복 제거하고 반환
    return list(set(essential_imports + additional_imports))

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
    skip = os.environ.get('WF_SKIP_INSTALLER')
    build = os.environ.get('WF_BUILD_INSTALLER')
    # 기본값: 인스톨러 생성을 건너뜀. (WF_SKIP_INSTALLER=false 또는 WF_BUILD_INSTALLER=true 로만 생성)
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
    if os.environ.get('WF_EXTERNAL_PACKAGER', '').strip().lower() in ('1','true','yes','on'):
        print('⏭ WF_EXTERNAL_PACKAGER=1 감지: spec 내부 post_build_automation 생략')
        return True
    dist_dir = SPEC_DIR / 'dist' / APP_NAME
    
    if not dist_dir.exists():
        print(f"❌ 빌드 결과물을 찾을 수 없습니다: {dist_dir}")
        return False
    
    print(f"\n🔧 빌드 후 자동화 처리 시작...")
    # 결과물 기본 경로(버전 기반) 정의: 폴더명에 버전만 사용 (타임스탬프 미사용)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")  # 메타데이터에만 사용
    version_tag = f"v{APP_VERSION}"
    portable_base_dir = BUILD_OUTPUT_DIR / f'{APP_NAME}_{version_tag}'
    portable_dir = portable_base_dir / f'{APP_NAME}_{version_tag}_portable'
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
            makensis_path = r'C:\Program Files (x86)\NSIS\makensis.exe'
            makensis_cmd = [makensis_path, '/V2', str(nsis_script)]
            nsis_log = SPEC_DIR / 'nsis_build.log'
            
            with open(nsis_log, 'w', encoding='utf-8') as log_file:
                result = subprocess.run(makensis_cmd, 
                                      cwd=SPEC_DIR,
                                      stdout=log_file,
                                      stderr=subprocess.STDOUT,
                                      timeout=300)  # 5분 타임아웃
            
            if result.returncode == 0:
                installer_file = SPEC_DIR / f'{APP_NAME}_{APP_VERSION}_installer.exe'
                if installer_file.exists():
                    print(f"✓ NSIS 인스톨러 생성 성공: {installer_file}")
                    # 인스톨러를 타임스탬프 폴더로 이동
                    final_installer = portable_base_dir / f'{APP_NAME}_{version_tag}_installer.exe'
                    shutil.move(str(installer_file), str(final_installer))
                    print(f"✓ 최종 인스톨러: {final_installer}")
                else:
                    print(f"❌ 인스톨러 파일 생성 실패")
            else:
                print(f"❌ NSIS 컴파일 실패 (로그: {nsis_log})")
                try:
                    with open(nsis_log, 'r', encoding='utf-8') as f:
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
        print("⏭  환경변수에 의해 NSIS 인스톨러 생성 단계를 건너뜁니다 (WF_SKIP_INSTALLER/WF_BUILD_INSTALLER).")
    
    # 2. 포터블 버전 생성 (동일 타임스탬프 경로 사용)
    shutil.copytree(dist_dir, portable_dir)
    
    # 포터블 실행 배치 파일 생성
    bat_lines = [
        '@echo off',
        'chcp 65001 > nul',
        'cd /d "%~dp0"',
        'echo ========================================',
        'echo BOM2Excel (포터블 버전)',
        'echo ========================================',
        'echo.',
        '"bom2excel.exe"'
    ]
    
    with open(portable_dir / f'run_bom2excel.bat', 'w', encoding='cp949') as f:
        f.write('\n'.join(bat_lines))
    
    print(f"✓ 포터블 버전 생성: {portable_dir}")
    
    # 3. 압축 파일 생성
    try:
        zip_file = portable_base_dir / f'{APP_NAME}_{version_tag}_portable.zip'
        shutil.make_archive(str(zip_file.with_suffix('')), 'zip', portable_dir)
        print(f"✓ 포터블 압축 파일: {zip_file}")
    except Exception as e:
        print(f"⚠️ 압축 파일 생성 실패: {e}")

    # 메타데이터 및 체크섬 생성
    try:
        def sha256sum(p: Path) -> str:
            h = hashlib.sha256()
            with open(p, 'rb') as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b''):
                    h.update(chunk)
            return h.hexdigest()

        metadata_dir = portable_base_dir / 'metadata'
        metadata_dir.mkdir(parents=True, exist_ok=True)

        try:
            import PyInstaller as _PI
            pyinstaller_version = getattr(_PI, '__version__', None)
        except Exception:
            pyinstaller_version = None

        def _git_commit():
            try:
                r = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], cwd=WORKSPACE_ROOT, capture_output=True, text=True, timeout=3)
                return r.stdout.strip() if r.returncode == 0 else None
            except Exception:
                return None

        build_info = {
            'app_name': APP_NAME,
            'app_display_name': APP_DISPLAY_NAME,
            'app_version': APP_VERSION,
            'build_timestamp': timestamp,
            'python_version': sys.version,
            'pyinstaller_version': pyinstaller_version,
            'git_commit': _git_commit(),
            'artifacts': {}
        }

        checksums_lines = []

        if final_installer and Path(final_installer).exists():
            inst_sha = sha256sum(final_installer)
            build_info['artifacts']['installer'] = {
                'path': str(final_installer),
                'size_bytes': final_installer.stat().st_size,
                'sha256': inst_sha
            }
            checksums_lines.append(f"{inst_sha}  {final_installer.name}")

        if zip_file and Path(zip_file).exists():
            zip_sha = sha256sum(zip_file)
            build_info['artifacts']['portable_zip'] = {
                'path': str(zip_file),
                'size_bytes': zip_file.stat().st_size,
                'sha256': zip_sha
            }
            checksums_lines.append(f"{zip_sha}  {zip_file.name}")

        build_info['artifacts']['portable_dir'] = str(portable_dir)

        with open(metadata_dir / 'build_info.json', 'w', encoding='utf-8') as f:
            json.dump(build_info, f, ensure_ascii=False, indent=2)

        with open(metadata_dir / 'checksums.txt', 'w', encoding='utf-8') as f:
            f.write('\n'.join(checksums_lines) + ('\n' if checksums_lines else ''))

        print(f"✓ 메타데이터 생성: {metadata_dir}")
    except Exception as e:
        print(f"⚠️ 메타데이터 생성 실패: {e}")
    
    # 4. 빌드 임시 파일 정리
    temp_dirs = [
        SPEC_DIR / 'build',
        SPEC_DIR / 'dist',
        SPEC_DIR / '__pycache__',
        SPEC_DIR / 'installer_resources'
    ]
    
    for temp_dir in temp_dirs:
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    # 임시 파일들 정리
    temp_files = [
        SPEC_DIR / f'bom2excel_installer.nsi',
        SPEC_DIR / 'global_policies.json'
    ]
    
    for temp_file in temp_files:
        if temp_file.exists():
            temp_file.unlink()
    
    print(f"✓ 임시 파일 정리 완료")
    
    print(f"\\n🎉 빌드 및 패키징 완료!")
    print(f"📁 결과물 위치: {portable_base_dir}")
    print(f"📦 포터블 폴더: {portable_dir}")
    
    return True

# ==================== PyInstaller 설정 ====================
block_cipher = None

# Get hidden imports and print for debugging
hidden_imports_list = get_optimized_hidden_imports()
print(f"\n🔍 DEBUG: Total hidden imports: {len(hidden_imports_list)}")
print(f"🔍 DEBUG: ntplib in list: {'ntplib' in hidden_imports_list}")
print(f"🔍 DEBUG: gspread in list: {'gspread' in hidden_imports_list}")
print(f"🔍 DEBUG: First 10 imports: {hidden_imports_list[:10]}")

# Collect missing libraries directly
# lib_datas, lib_binaries = collect_missing_libraries()  # DISABLED: 불필요한 중복 복사 (254MB 절약)
resource_datas = collect_essential_resources()

# 분석 단계
a = Analysis(
    [str(SPEC_DIR / 'ui_main.py')],
    pathex=[str(SPEC_DIR), str(COMMON_DIR)],
    binaries=[],  # lib_binaries 제거
    datas=resource_datas,  # lib_datas 제거 - PyInstaller가 이미 모든 라이브러리 수집함
    hiddenimports=hidden_imports_list,
    hookspath=[],  # hook 파일 불필요 (get_optimized_hidden_imports에서 직접 처리)
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # GUI 프레임워크 제외 (Tkinter만 사용)
        'PyQt5', 'PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets',
        'PyQt6', 'PySide2', 'PySide6', 'wx',
        # 이미지/CV 라이브러리 제외 (PyAutoGUI는 PIL 필요하므로 PIL 제외 제거)
        'cv2', 'matplotlib', 'scipy', 'sklearn', 'seaborn', 'plotly',
        # ML/DL 프레임워크
        'tensorflow', 'torch', 'keras',
        # 개발 도구
        'jupyter', 'IPython', 'notebook', 'jupyter_client', 'jupyter_core',
        'jinja2', 'sip', 'bokeh', 'altair', 'statsmodels', 'sympy',
        # 테스트 프레임워크
        'pytest', 'unittest', 'nose', 'mock'
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
    debug=DEBUG_BUILD,       # 디버그 모드 플래그로 제어
    bootloader_ignore_signals=False,
    strip=False,             # Windows에서 strip 도구 없음으로 비활성화
    upx=False,               # UPX 비활성화로 로딩 시간 단축
    console=DEBUG_BUILD,     # 디버그 시 콘솔 출력, 릴리스 시 GUI 전용
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # 아이콘: 새 아이콘 (16, 32, 48, 256 멀티사이즈)
    # icon=str(ensure_b2e_icon()),  # Old: B2E.ico (16x16 only)
    icon=["res\\01_BOM_Exporter.ico"],
    version='version_info.txt' if Path('version_info.txt').exists() else None
)

# COLLECT - 최적화된 onedir 버전 생성
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,             # Windows에서 strip 도구 없음으로 비활성화
    upx=False,               # UPX 비활성화로 빠른 로딩
    name=APP_NAME,
)

# ==================== 빌드 완료 후 자동 실행 ====================
# import atexit
# atexit.register(post_build_automation)  # DISABLED: 빌드 중단 문제 해결

print(f"\\n✅ {APP_NAME} 최적화 빌드 설정 완료")
print(f"🔧 INSTALLER_DECISION should_build_installer={_should_build_installer()} (WF_SKIP_INSTALLER={os.environ.get('WF_SKIP_INSTALLER')}, WF_BUILD_INSTALLER={os.environ.get('WF_BUILD_INSTALLER')})")
print(f"📋 히든 임포트: {len(get_optimized_hidden_imports())}개 (필수 모듈 포함)")
print(f"📦 리소스 파일: 수집 중...")
print(f"🎯 타겟: 빠른 로딩 onedir + 포터블 버전")
print(f"⚡ 최적화: UPX 비활성화, 대용량 라이브러리만 제외, 디버그 심볼 제거")