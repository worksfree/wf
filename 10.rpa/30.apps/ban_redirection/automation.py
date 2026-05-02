# -*- coding: utf-8 -*-
"""
Ban Redirection — DNS change logic.
All functions are stateless; call run_fix() as the main entry point.
"""
import ctypes
import subprocess

_NO_WINDOW = subprocess.CREATE_NO_WINDOW


def is_admin() -> bool:
    """Return True if the current process has administrator privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def get_active_adapters() -> list:
    """Return names of all active network adapters (Status=Up)."""
    ps = (
        "Get-NetAdapter | Where-Object { $_.Status -eq 'Up' } | "
        "Select-Object -ExpandProperty Name"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
            capture_output=True, text=True, timeout=10,
            creationflags=_NO_WINDOW,
        )
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]
    except Exception:
        return []


def set_dns(adapter_name: str, dns_list: list) -> bool:
    """Set DNS servers for a named adapter. Returns True on success."""
    dns_str = ", ".join(f'"{d}"' for d in dns_list)
    ps = (
        f'Set-DnsClientServerAddress -InterfaceAlias "{adapter_name}" '
        f'-ServerAddresses ({dns_str})'
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
            capture_output=True, text=True, timeout=10,
            creationflags=_NO_WINDOW,
        )
        return result.returncode == 0
    except Exception:
        return False


def flush_dns_cache() -> bool:
    """Flush the Windows DNS resolver cache."""
    try:
        result = subprocess.run(
            "ipconfig /flushdns",
            capture_output=True, text=True, shell=True, timeout=10,
            creationflags=_NO_WINDOW,
        )
        return result.returncode == 0
    except Exception:
        return False


def run_fix(dns_primary: str, dns_secondary: str, progress_cb=None) -> dict:
    """Apply DNS to all active adapters and flush cache.

    progress_cb signature: (message: str, is_error: bool = False)
    Returns {"success": bool, "adapters_changed": list, "errors": list}
    """
    def cb(msg, is_err=False):
        if progress_cb:
            try:
                progress_cb(msg, is_err)
            except Exception:
                pass

    if not is_admin():
        cb("관리자 권한이 필요합니다.", True)
        return {"success": False, "adapters_changed": [], "errors": ["관리자 권한 없음"]}

    adapters = get_active_adapters()
    if not adapters:
        cb("활성 네트워크 인터페이스를 찾을 수 없습니다.", True)
        return {"success": False, "adapters_changed": [], "errors": ["활성 인터페이스 없음"]}

    cb(f"활성 인터페이스 {len(adapters)}개 발견: {', '.join(adapters)}")

    dns_list = [dns_primary, dns_secondary]
    changed, errors = [], []

    for adapter in adapters:
        cb(f"DNS 변경 중: {adapter}  →  {dns_primary}, {dns_secondary}")
        if set_dns(adapter, dns_list):
            changed.append(adapter)
            cb(f"  ✓ 완료: {adapter}")
        else:
            errors.append(adapter)
            cb(f"  ✗ 실패: {adapter}", True)

    cb("DNS 캐시 초기화 중...")
    if flush_dns_cache():
        cb("  ✓ DNS 캐시 초기화 완료")
    else:
        cb("  ✗ DNS 캐시 초기화 실패", True)

    success = bool(changed) and not errors
    if success:
        cb(f"\n완료! {len(changed)}개 인터페이스에 Google DNS가 적용되었습니다.")
        cb("브라우저를 재시작하면 변경사항이 적용됩니다.")
    elif changed:
        cb(f"\n부분 완료: {len(changed)}개 성공, {len(errors)}개 실패", True)
    else:
        cb("\nDNS 변경에 실패했습니다.", True)

    return {"success": success, "adapters_changed": changed, "errors": errors}
