# -*- mode: python ; coding: utf-8 -*-

import os
import sys
import json
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
import hashlib

# Windows 콘솔 인코딩 설정
if sys.platform == "win32":
    try:
        import io

        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except:
        pass


# ==================== 버전 관리 ====================
def load_and_increment_version():
    """settings.json에서 버전을 읽고 자동으로 증가시킴"""
    try:
        SPEC_DIR_LOCAL = Path(__file__).resolve().parent
    except NameError:
        SPEC_DIR_LOCAL = Path(os.getcwd())

    settings_file = SPEC_DIR_LOCAL / "config" / "conversion_verifier" / "settings.json"
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

# ==================== 앱 정보 ====================
APP_NAME = "conversion_verifier"
APP_VERSION = APP_VERSION_FULL
APP_DISPLAY_NAME = "Conversion Verifier"
APP_DESCRIPTION = "변환 검증 도구"
APP_PUBLISHER = "WorksFree Co., Ltd."

# ==================== 경로 설정 ====================
try:
    SPEC_DIR = Path(__file__).resolve().parent  # spec 파일 위치 기준 (CWD 무관)
except NameError:
    SPEC_DIR = Path(os.getcwd())
WORKSPACE_ROOT = SPEC_DIR.parent.parent
COMMON_DIR = WORKSPACE_ROOT / "10.common"
BUILD_OUTPUT_DIR = Path("D:/release/candidates")

print(f"\n{'='*80}")
print(f"WorksFree {APP_DISPLAY_NAME} v{APP_VERSION} 빌드 시작")
print(f"{'='*80}")


# ==================== 사용자 홈 설정 파일 준비 ====================
def prepare_user_configs():
    """사용자 홈 디렉토리용 설정 파일들 준비 (NSIS 인스톨러용)"""
    # config 폴더를 빌드용 임시 구조로 복사
    home_dir = SPEC_DIR / "build" / "user_home_bundle"
    home_dir.mkdir(parents=True, exist_ok=True)

    wf_rpa_dir = home_dir / ".wf_rpa"
    app_dir = wf_rpa_dir / APP_NAME

    for directory in [wf_rpa_dir, app_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    # 1. wf_rpa_config.json - 실제 config 파일에서 복사
    app_config_dir = SPEC_DIR / "config"
    source_wf_config = app_config_dir / "wf_rpa_config.json"
    
    if source_wf_config.exists():
        shutil.copy2(source_wf_config, wf_rpa_dir / "wf_rpa_config.json")
        print(f"✓ wf_rpa_config.json 복사 완료 (email_settings, google_sheets 포함)")
    else:
        print(f"⚠️ wf_rpa_config.json을 찾을 수 없음: {source_wf_config}")

    # 2. Google Credentials 복사 (.wf_rpa 루트에 직접 복사)
    google_creds_found = False
    if app_config_dir.exists():
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
    settings_src = app_config_dir / "conversion_verifier" / "settings.json"
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
        app_settings_dir = wf_rpa_dir / "conversion_verifier"
        app_settings_dir.mkdir(parents=True, exist_ok=True)
        bundled_settings = app_settings_dir / "settings.json"
        with open(bundled_settings, 'w', encoding='utf-8') as f:
            json.dump(settings_data, f, ensure_ascii=False, indent=2)
        
        print(f"✓ settings.json 처리 완료 (.wf_rpa/conversion_verifier/) - 버전: {APP_VERSION_FULL}, 빌드: #{VERSION_INFO['build_count']}")
    else:
        print(f"⚠️ settings.json을 찾을 수 없음: {settings_src}")

    return home_dir


# ==================== 설정 파일 번들링 ====================
def bundle_config_files():
    """필수 설정 파일을 .wf_rpa 루트에 번들링"""
    datas = []
    # 임시 설정 파일 생성 위치
    # 루트 installer_resources 대신 앱 로컬 빌드 폴더 사용
    temp_config_base = SPEC_DIR / "build" / "user_home_bundle" / ".wf_rpa"
    temp_config_base.mkdir(parents=True, exist_ok=True)
    
    # 실제 자격증명 파일 위치
    source_config_dir = SPEC_DIR / "config"

    # wf_rpa_config.json - 실제 config 파일에서 복사 (관리자 이메일, Google Sheets 포함)
    source_wf_config = source_config_dir / "wf_rpa_config.json"
    if source_wf_config.exists():
        import shutil
        target_config = temp_config_base / "wf_rpa_config.json"
        shutil.copy2(source_wf_config, target_config)
        datas.append((str(target_config), ".wf_rpa"))
        print(f"✓ wf_rpa_config.json 번들링됨 (email_settings, google_sheets 포함)")
    else:
        print(f"⚠️ wf_rpa_config.json을 찾을 수 없음: {source_wf_config}")

    # Google Service Account 자격증명 (실제 소스 config 폴더에서 복사)
    for silver_file in source_config_dir.glob(".silver-argon-*.json"):
        datas.append((str(silver_file), ".wf_rpa"))
        print(f"✓ 자격증명 파일 번들: {silver_file.name}")
    
    # settings.json을 .wf_rpa/conversion_verifier/ 위치로 번들링
    settings_src = source_config_dir / "conversion_verifier" / "settings.json"
    if settings_src.exists():
        datas.append((str(settings_src), ".wf_rpa/conversion_verifier"))
        print(f"설정 파일 번들: settings.json → .wf_rpa/conversion_verifier/")

    # policy.json은 identity + policy만 포함 (변하지 않는 값들)
    # 버전 정보는 settings.json의 runtime_config에만 있음
    # policy.json은 그대로 복사만 함 (버전 주입 안함)
    policy_src = source_config_dir / "conversion_verifier" / "policy.json"
    if policy_src.exists():
        datas.append((str(policy_src), ".wf_rpa/conversion_verifier"))
        print(f"✓ policy.json 번들링됨 (.wf_rpa/conversion_verifier/)")

    return datas


# ==================== 라이브러리 직접 수집 ====================
def collect_missing_libraries():
    """PyInstaller가 수집하지 못하는 라이브러리들을 직접 복사"""
    import importlib.util
    
    datas = []
    binaries = []
    
    # 필수 라이브러리 목록
    required_libs = ['ntplib', 'gspread', 'requests', 'urllib3', 'google']
    
    for lib_name in required_libs:
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


# SPEC_DIR 정의 확인
try:
    SPEC_DIR
except NameError:
    try:
        SPEC_DIR = Path(__file__).resolve().parent
    except NameError:
        SPEC_DIR = Path(os.getcwd())

# collect_missing_libraries() 실행
# lib_datas, lib_binaries = collect_missing_libraries()  # DISABLED: 불필요한 중복 복사 (254MB 절약)

block_cipher = None

a = Analysis(
    ["ui_main.py"],
    pathex=[".", r"d:\drive_files\10.worksfree\10.rpa\10.common"],
    binaries=[],  # lib_binaries 제거
    datas=[
        ("config/*", "config"),
        ("res/*", "res"),
        *bundle_config_files(),
    ],  # lib_datas 제거 - PyInstaller가 이미 모든 라이브러리 수집함
    hiddenimports=[
        # WorksFree 공통 모듈 (필수)
        "wf_log",
        "wf_credit_manager",
            "wf_credit_session_utils",
        "wf_app_init_helpers",
        "wf_license",
        "wf_hwinfo",
        # 하드웨어 정보 (wf_hwinfo.py에서 필요)
        "cpuinfo.cpuinfo",
        "ntplib",
        # Google API (필요시)
        "google.auth",
        "google.auth.transport.requests",
        "google.auth.transport.urllib3",
        "google.oauth2.credentials",
        "google.oauth2.service_account",
        "googleapiclient.discovery",
        # Google Sheets
        "gspread",
        # Requests
        "requests",
        "requests.adapters",
        "requests.exceptions",
        "urllib3",
        "urllib3.exceptions",
        "certifi",
        "charset_normalizer",
        # pywin32 모듈 (Google API 사용 시 필수)
        "win32timezone",
        "win32api",
        "win32con",
        "pywintypes",
        "pythoncom",
    ],
    hookspath=[str(SPEC_DIR)],  # hook 파일들 경로
    runtime_hooks=[],
    excludes=[
        # 불필요한 무거운 라이브러리 제외
        "PyQt5",
        "PyQt6",
        "PySide2",
        "PySide6",  # Qt 라이브러리 (사용 안 함)
        "cv2",
        "opencv",  # OpenCV (사용 안 함)
        "matplotlib",
        "scipy",  # 과학 계산 라이브러리
        "pytest",
        "unittest",
        "test",  # 테스트 프레임워크
        "IPython",
        "jupyter",  # Jupyter 관련
        "pygments",  # 코드 하이라이팅
        "pandas",
        "numpy",  # 데이터 분석 라이브러리 (사용 안 함)
        "openpyxl",
        "xlrd",
        "xlwt",  # Excel 라이브러리 (사용 안 함)
        "lxml",
        "html5lib",  # XML/HTML 파서 (미사용)
        "jinja2",
        "mako",  # 템플릿 엔진
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="conversion_verifier",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon="res/CV.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="conversion_verifier",
)


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
    # 기본값: 인스톨러 스킵. WF_SKIP_INSTALLER=false 또는 WF_BUILD_INSTALLER=true 로만 생성.
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


# ==================== NSIS 스크립트 생성 ====================
def create_nsis_script():
    """NSIS 인스톨러 스크립트 생성 (사용자 홈 설정 파일 포함)"""
    # 사용자 홈 설정 파일 준비
    user_home = prepare_user_configs()
    
    nsis_script = f"""!include "MUI2.nsh"

Name "{APP_DISPLAY_NAME}"
OutFile "{APP_NAME}_{APP_VERSION}_installer.exe"
InstallDir "$PROGRAMFILES64\\WorksFree\\{APP_NAME}"
RequestExecutionLevel admin

!define MUI_ABORTWARNING
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "Korean"

Section "Install"
    ; 프로그램 파일 설치
    SetOutPath "$INSTDIR"
    File /r "dist\\{APP_NAME}\\*.*"
    
    ; .wf_rpa 디렉토리 생성
    CreateDirectory "$PROFILE\\.wf_rpa"
    CreateDirectory "$PROFILE\\.wf_rpa\\{APP_NAME}"
    
    ; 사용자 홈 설정 파일 설치
    IfFileExists "$PROFILE\\.wf_rpa\\wf_rpa_config.json" 0 +3
        DetailPrint "기존 wf_rpa_config.json 유지"
        Goto skip_wf_config
    SetOutPath "$PROFILE\\.wf_rpa"
    File "build\\user_home_bundle\\.wf_rpa\\wf_rpa_config.json"
    skip_wf_config:
    
    ; Google Credentials 설치 (덮어쓰기)
    IfFileExists "$PROFILE\\.wf_rpa\\.silver-argon-445712-a0-4ce021aa64be.json" 0 +3
        DetailPrint "기존 credentials 유지"
        Goto skip_creds
    File "build\\user_home_bundle\\.wf_rpa\\.silver-argon-*.json"
    skip_creds:
    
    ; settings.json 설치 (항상 최신 버전으로 업데이트)
    CreateDirectory "$PROFILE\\.wf_rpa\\{APP_NAME}"
    SetOutPath "$PROFILE\\.wf_rpa\\{APP_NAME}"
    File "build\\user_home_bundle\\.wf_rpa\\{APP_NAME}\\*.*"
    
    ; 바로가기 생성
    CreateShortcut "$DESKTOP\\{APP_DISPLAY_NAME}.lnk" "$INSTDIR\\{APP_NAME}.exe"
    WriteUninstaller "$INSTDIR\\Uninstall.exe"
SectionEnd

Section "Uninstall"
    Delete "$DESKTOP\\{APP_DISPLAY_NAME}.lnk"
    RMDir /r "$INSTDIR"
    ; 사용자 데이터는 유지 (선택적 삭제)
SectionEnd
"""

    nsi_file = SPEC_DIR / f"{APP_NAME}_installer.nsi"
    with open(nsi_file, "w", encoding="utf-8") as f:
        f.write(nsis_script)

    return nsi_file


# ==================== 빌드 후 자동화 ====================
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
                )

            if result.returncode == 0:
                installer_file = SPEC_DIR / f"{APP_NAME}_{APP_VERSION}_installer.exe"
                if installer_file.exists():
                    final_installer = portable_base_dir / f"{APP_NAME}_{version_tag}_installer.exe"
                    shutil.move(str(installer_file), str(final_installer))
                    print(f"✓ NSIS 인스톨러 생성: {final_installer}")
            else:
                print(f"❌ NSIS 컴파일 실패 (로그: {nsis_log})")
        except subprocess.TimeoutExpired:
            print(f"❌ NSIS 컴파일 타임아웃 (5분 초과)")
        except Exception as e:
            print(f"⚠️ 인스톨러 생성 중 오류: {e}")
    else:
        print(
            "⏭  환경변수에 의해 NSIS 인스톨러 생성 단계를 건너뜁니다 (WF_SKIP_INSTALLER/WF_BUILD_INSTALLER)."
        )

    # 2. 포터블 버전 생성
    shutil.copytree(dist_dir, portable_dir)
    print(f"✓ 포터블 버전 생성: {portable_dir}")

    # 3. 압축 파일 생성
    try:
        zip_file = portable_base_dir / f"{APP_NAME}_{version_tag}_portable.zip"
        shutil.make_archive(str(zip_file.with_suffix("")), "zip", portable_dir)
        print(f"✓ 포터블 압축 파일: {zip_file}")
    except Exception as e:
        print(f"⚠️ 압축 파일 생성 실패: {e}")

    # 4. 메타데이터 생성
    try:
        metadata_dir = portable_base_dir / "metadata"
        metadata_dir.mkdir(exist_ok=True)

        # NOTE: 이전 버전에서 실수로 {{ }} 사용 → set({dict}) 시도하며
        # TypeError: unhashable type: 'dict' 발생. 단일 dict 로 수정.
        build_info = {
            "app_name": APP_NAME,
            "app_display_name": APP_DISPLAY_NAME,
            "full_version": f"v{APP_VERSION}",
            "build_timestamp": timestamp,
            "python_version": sys.version,
        }

        with open(metadata_dir / "build_info.json", "w", encoding="utf-8") as f:
            json.dump(build_info, f, ensure_ascii=False, indent=2)

        print(f"✓ 메타데이터 생성: {metadata_dir}")
    except Exception as e:
        print(f"⚠️ 메타데이터 생성 실패: {e}")

    # 5. 임시 파일 정리
    temp_dirs = [SPEC_DIR / "build", SPEC_DIR / "dist", SPEC_DIR / "__pycache__"]
    for temp_dir in temp_dirs:
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)

    temp_files = [SPEC_DIR / f"{APP_NAME}_installer.nsi"]
    for temp_file in temp_files:
        if temp_file.exists():
            temp_file.unlink()

    print(f"✓ 임시 파일 정리 완료")
    print(f"\n🎉 빌드 및 패키징 완료!")
    print(f"📁 결과물 위치: {portable_base_dir}")

    return True


# import atexit

# atexit.register(post_build_automation)  # DISABLED: 빌드 중단 문제 해결

print(f"\n✅ {APP_DISPLAY_NAME} 빌드 설정 완료")
print(
    f"🔧 INSTALLER_DECISION should_build_installer={_should_build_installer()} (WF_SKIP_INSTALLER={os.environ.get('WF_SKIP_INSTALLER')}, WF_BUILD_INSTALLER={os.environ.get('WF_BUILD_INSTALLER')})"
)
