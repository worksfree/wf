# -*- coding: utf-8 -*-
"""
wf_i18n — WorksFree RPA 다국어 지원 모듈

## 사용법

    from wf_i18n import t, register_app, get_app_locale_dir

    # 앱 시작 시 1회 등록 (ui_main.py 상단)
    register_app("be", get_app_locale_dir(__file__, "be"))

    # 번역
    t("run_button")                     # → "실행"  (common 생략 가능)
    t("common.exit_button")             # → "종료"  (common 명시)
    t("be.title", ver="v1.0")           # → "BOM 엑셀 저장 v1.0"
    t("common.scan_error", e="오류")    # → "폴더 스캔 중 오류가 발생했습니다:\n오류"

## 키 규칙

    "키"           → common 네임스페이스 단축 형태
    "common.키"    → 전 앱 공통 문자열  (10.common/locales/{locale}.json)
    "be.키"        → 앱별 고유 문자열   ({app}/locales/{locale}.json)

## 파일 구조

    10.common/locales/
      ko.json    ← common 키 전체 (네임스페이스 접두어 없음)
      en.json

    {app}/locales/
      ko.json    ← 해당 앱 키만 (네임스페이스 접두어 없음)
      en.json

## 빌드(PyInstaller) 시 spec datas 예시

    # bom_exporter.spec
    datas += [(str(COMMON_DIR / "locales" / "ko.json"), "locales")]
    datas += [(str(SPEC_DIR  / "locales" / "ko.json"), "locales/be")]

## 로케일 결정 순서

    1. set_locale() 명시 호출
    2. ~/.wf_rpa/wf_rpa_config.json > ui.locale
    3. 시스템 locale (ko_KR → "ko",  en_US → "en")
    4. 기본값: "ko"
"""

import json
import locale as _locale_mod
import sys
import threading
from pathlib import Path

_COMMON_LOCALES_DIR = Path(__file__).parent / "locales"
_SUPPORTED = {"ko", "en"}
_DEFAULT_LOCALE = "ko"


class _I18n:
    def __init__(self):
        self._lock = threading.Lock()
        self._locale: str = ""
        self._strings: dict = {}    # {locale: {ns: {key: value}}}
        self._loaded: set = set()   # (locale, ns) 이미 로드된 조합
        self._app_dirs: dict = {}   # ns → Path

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def register_app(self, ns: str, locale_dir: Path) -> None:
        """앱 로케일 디렉터리 등록. ui_main.py 상단에서 1회 호출."""
        with self._lock:
            self._app_dirs[ns] = locale_dir
            # 이미 로케일이 결정되어 있으면 즉시 로드
            if self._locale:
                self._load_ns("ko", ns)       # fallback은 항상 먼저
                if self._locale != "ko":
                    self._load_ns(self._locale, ns)

    def t(self, key: str, **kwargs) -> str:
        """현재 로케일 기준으로 key를 번역. kwargs는 str.format_map() 치환."""
        locale = self._ensure_locale()
        ns, bare = _split_key(key)
        value = self._lookup(locale, ns, bare)
        if kwargs:
            try:
                value = value.format_map(kwargs)
            except (KeyError, ValueError):
                pass
        return value

    def set_locale(self, locale: str) -> None:
        """로케일 명시 변경. 앱 설정창에서 호출."""
        locale = locale.strip().lower()[:2]
        if locale not in _SUPPORTED:
            locale = _DEFAULT_LOCALE
        with self._lock:
            self._locale = locale
            # common 재로드
            self._load_ns("ko", "common")
            if locale != "ko":
                self._load_ns(locale, "common")
            # 등록된 모든 앱 ns 재로드
            for ns in list(self._app_dirs):
                self._load_ns("ko", ns)
                if locale != "ko":
                    self._load_ns(locale, ns)

    def get_locale(self) -> str:
        return self._ensure_locale()

    def reload(self) -> None:
        """locale 파일 전체 재로드 (개발 중 핫리로드용)."""
        with self._lock:
            self._strings.clear()
            self._loaded.clear()
            if self._locale:
                self._bootstrap(self._locale)

    # ------------------------------------------------------------------ #
    # Internal
    # ------------------------------------------------------------------ #

    def _ensure_locale(self) -> str:
        if not self._locale:
            with self._lock:
                if not self._locale:
                    detected = _detect_locale()
                    self._locale = detected
                    self._bootstrap(detected)
        return self._locale

    def _bootstrap(self, locale: str) -> None:
        """common 로케일 초기 로드 (lock 보유 상태에서 호출)."""
        self._load_ns("ko", "common")
        if locale != "ko":
            self._load_ns(locale, "common")

    def _load_ns(self, locale: str, ns: str) -> None:
        """한 (locale, ns) 조합을 파일에서 로드 (중복 방지)."""
        tag = (locale, ns)
        if tag in self._loaded:
            return

        if ns == "common":
            path = _COMMON_LOCALES_DIR / f"{locale}.json"
        else:
            app_dir = self._app_dirs.get(ns)
            if not app_dir:
                self._loaded.add(tag)   # 등록 안 됨 — 다시 시도 안 함
                return
            path = app_dir / f"{locale}.json"

        try:
            raw: dict = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            self._loaded.add(tag)
            return
        except Exception:
            self._loaded.add(tag)
            return

        bucket = self._strings.setdefault(locale, {}).setdefault(ns, {})
        bucket.update(raw)
        self._loaded.add(tag)

    def _lookup(self, locale: str, ns: str, key: str) -> str:
        """locale → ko → key 순으로 fallback."""
        # ns가 common이 아니면 앱 locale 로드 보장
        if ns != "common":
            self._load_ns("ko", ns)
            if locale != "ko":
                self._load_ns(locale, ns)

        val = self._strings.get(locale, {}).get(ns, {}).get(key)
        if val is not None:
            return val
        if locale != "ko":
            val = self._strings.get("ko", {}).get(ns, {}).get(key)
            if val is not None:
                return val
        # 미번역 키 → 키 자체 반환 (개발 중 즉시 식별)
        return key


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #

def _split_key(key: str):
    """"ns.key" → (ns, key),  "key" → ("common", key)."""
    if "." in key:
        ns, _, bare = key.partition(".")
        return ns.strip(), bare.strip()
    return "common", key.strip()


def _detect_locale() -> str:
    """로케일 자동 감지: wf_rpa_config → .locale 파일 → 시스템 → 기본값."""
    try:
        cfg = Path.home() / ".wf_rpa" / "wf_rpa_config.json"
        if cfg.exists():
            data = json.loads(cfg.read_text(encoding="utf-8"))
            val = str(data.get("ui", {}).get("locale", "") or "").strip().lower()[:2]
            if val in _SUPPORTED:
                return val
    except Exception:
        pass
    # 인스톨러가 기록한 언어 파일 (.locale)
    try:
        locale_file = Path.home() / ".wf_rpa" / ".locale"
        if locale_file.exists():
            val = locale_file.read_text(encoding="utf-8").strip().lower()[:2]
            if val in _SUPPORTED:
                return val
    except Exception:
        pass
    try:
        sys_locale = (_locale_mod.getdefaultlocale()[0] or "").lower()
        if sys_locale.startswith("ko"):
            return "ko"
        if sys_locale.startswith("en"):
            return "en"
    except Exception:
        pass
    return _DEFAULT_LOCALE


# ------------------------------------------------------------------ #
# Module-level singleton + public functions
# ------------------------------------------------------------------ #

_instance = _I18n()


def t(key: str, **kwargs) -> str:
    """현재 로케일로 key를 번역. kwargs는 문자열 치환에 사용."""
    return _instance.t(key, **kwargs)


def register_app(ns: str, locale_dir: Path) -> None:
    """앱 로케일 디렉터리 등록. ui_main.py 상단에서 1회 호출.

    Args:
        ns:         앱 약어 ("be", "dp", "ar", "dc", "cv", "kfn", "qr", "br")
        locale_dir: 앱의 locales/ 폴더 Path. get_app_locale_dir() 사용 권장.
    """
    _instance.register_app(ns, locale_dir)


def get_app_locale_dir(app_file: str, app_ns: str) -> Path:
    """dev/frozen 환경을 투명하게 처리하는 locale 디렉터리 경로 반환.

    Args:
        app_file: __file__ (ui_main.py 기준)
        app_ns:   앱 약어

    Usage:
        register_app("be", get_app_locale_dir(__file__, "be"))
    """
    if getattr(sys, "frozen", False):
        # PyInstaller onedir: sys._MEIPASS/_internal/ 아래에 번들됨
        # spec datas: (str(SPEC_DIR / "locales" / "ko.json"), "locales/{ns}")
        return Path(sys._MEIPASS) / "locales" / app_ns
    return Path(app_file).parent / "locales"


def set_locale(locale: str) -> None:
    """로케일 변경 (예: "ko", "en")."""
    _instance.set_locale(locale)


def get_locale() -> str:
    """현재 로케일 코드 반환."""
    return _instance.get_locale()


def reload() -> None:
    """locale 파일 재로드 (개발 중 핫리로드용)."""
    _instance.reload()
