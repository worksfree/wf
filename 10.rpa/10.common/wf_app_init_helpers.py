"""
WorksFree 앱 초기화 공통 헬퍼 함수
4개 앱(bom_exporter, dwg_classifier, conversion_verifier, korean_filename_normalizer)에서
중복되는 크레딧/정책 초기화 및 단일 인스턴스 체크 패턴을 통합
"""

import sys
import os
import json
import threading
import logging
from pathlib import Path
from typing import Optional, Any
import shutil

try:
    from wf_credit_manager import CreditManager, WorksFreeManager
except ImportError:
    CreditManager = None
    WorksFreeManager = None


def init_credit_and_policy_managers(
    app_name: str,
    wf_manager: Optional[Any],
    master: Any,
    logger: Optional[logging.Logger] = None,
    recovery_delay_ms: int = 700,
    policy_delay_ms: int = 400,
) -> Optional[Any]:
    """크레딧 및 정책 매니저 초기화 + 백그라운드 동기화 스케줄
    
    Args:
        app_name: 앱 이름 (예: "bom_exporter", "dwg_classifier")
        wf_manager: WorksFreeManager 인스턴스 (None이면 크레딧 매니저 생성 안 함)
        master: tkinter 루트/마스터 윈도우 (after 스케줄링용)
        logger: 로거 인스턴스 (선택)
        recovery_delay_ms: 복구 동기화 지연 시간(ms), 기본 700
        policy_delay_ms: 정책 동기화 지연 시간(ms), 기본 400
    
    Returns:
        CreditManager 인스턴스 또는 None
    """
    if not CreditManager or not wf_manager:
        return None
    
    try:
        # 사용자 이메일 추출
        user_email = None
        try:
            user_info = wf_manager.get_user_info()
            user_email = user_info.get("user_mail") if user_info else None
        except Exception:
            pass
        
        # CreditManager 생성
        credit_manager = CreditManager(app_name, user_email)
        
        # 복구 동기화 스케줄러
        def _schedule_recovery():
            def _worker():
                try:
                    if credit_manager:
                        status = credit_manager.get_sync_status()
                        if status.get("needs_sync"):
                            if logger:
                                logger.info("🔄 백그라운드 복구 동기화 실행...")
                            result = credit_manager.check_and_sync_credits()
                            if logger:
                                logger.info(f"[STARTUP-RECOVERY] {result}")
                        else:
                            if logger:
                                logger.info("🔄 동기화 불필요")
                except Exception as e:
                    if logger:
                        logger.warning(f"[STARTUP-RECOVERY] 오류: {e}")
            
            threading.Thread(target=_worker, daemon=True, name="Recovery-Sync").start()
        
        # 정책 동기화 스케줄러 (앱 객체 메서드 참조 필요 시 람다로 전달)
        def _schedule_policy_sync(app_obj):
            """app_obj._async_refresh_policies 메서드가 있으면 호출"""
            def _worker():
                try:
                    if hasattr(app_obj, '_async_refresh_policies'):
                        app_obj._async_refresh_policies()
                except Exception as e:
                    if logger:
                        logger.warning(f"[POLICY-SYNC] 오류: {e}")
            
            threading.Thread(target=_worker, daemon=True, name="Policy-Sync").start()
        
        # 스케줄 등록
        try:
            master.after(recovery_delay_ms, _schedule_recovery)
            # 정책 동기화는 앱 객체 컨텍스트가 필요하므로 여기서는 스케줄만 등록
            # 실제 호출은 각 앱의 __init__에서 master.after(policy_delay_ms, self._async_refresh_policies) 형태로 유지
        except Exception:
            # after 사용 불가 시 즉시 실행
            threading.Thread(target=_schedule_recovery, daemon=True).start()
        
        return credit_manager
    
    except Exception as e:
        if logger:
            logger.error(f"크레딧 매니저 초기화 실패: {e}")
        return None


def seed_res_if_missing(target_res_dir: Path, bundle_candidates: list[Path], logger: Optional[logging.Logger] = None) -> bool:
    """Ensure res assets exist at target_res_dir.

    - If target_res_dir already has files, do nothing.
    - Otherwise, copy the first existing bundle_candidates directory into target_res_dir.
    - Missing candidates are ignored safely.
    Returns True if a copy occurred, False otherwise.
    """
    try:
        target_res_dir.mkdir(parents=True, exist_ok=True)
        has_files = any(target_res_dir.iterdir())
        if has_files:
            return False

        source = next((p for p in bundle_candidates if p and p.exists()), None)
        if not source:
            if logger:
                logger.debug(f"[res-seed] no source found; skip (target={target_res_dir})")
            return False

        shutil.copytree(source, target_res_dir, dirs_exist_ok=True)
        if logger:
            logger.info(f"[res-seed] seeded resources from {source} -> {target_res_dir}")
        return True
    except Exception as e:
        if logger:
            logger.warning(f"[res-seed] failed: {e}")
        return False


def init_credit_manager_only(
    app_name: str,
    wf_manager: Optional[Any],
    logger: Optional[logging.Logger] = None,
) -> Optional[Any]:
    """크레딧 매니저만 생성 (동기화 스케줄 없이)
    
    Args:
        app_name: 앱 이름
        wf_manager: WorksFreeManager 인스턴스
        logger: 로거 인스턴스 (선택)
    
    Returns:
        CreditManager 인스턴스 또는 None
    """
    if not CreditManager or not wf_manager:
        return None
    
    try:
        user_email = None
        try:
            user_info = wf_manager.get_user_info()
            user_email = user_info.get("user_mail") if user_info else None
        except Exception:
            pass
        
        return CreditManager(app_name, user_email)
    except Exception as e:
        if logger:
            logger.error(f"크레딧 매니저 생성 실패: {e}")
        return None


# ==================== 단일 인스턴스 체크 (Cross-App Guard) ====================

def check_cross_app_running_and_exit(app_name: str) -> None:
    """다른 WorksFree 앱이 실행 중이면 메시지 표시하고 대기/재확인
    
    사용자가 다른 앱을 닫고 다시 시도할 수 있도록 반복 체크합니다.
    
    Args:
        app_name: 현재 앱 이름 (예: "bom_exporter", "dwg_classifier")
    
    Note:
        - 다른 앱 실행 중: 메시지 박스 표시 → 사용자가 "확인" 클릭 → 재확인
        - 다른 앱이 닫혔으면: 정상 진행 (return)
        - 다른 앱이 여전히 실행 중이면: 종료 (sys.exit)
    """
    try:
        import psutil  # type: ignore
        psutil_available = True
    except Exception:
        psutil_available = False
    
    def _check_other_app_running():
        """다른 앱이 실행 중인지 확인. (running, app_name) 반환"""
        try:
            cfg = Path.home() / ".wf_rpa" / "wf_rpa_config.json"
            if not cfg.exists():
                return False, None
            
            with open(cfg, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            es = data.get("execution_status", {})
            if not es.get("is_running", False):
                return False, None
            
            pid = es.get("pid")
            if not pid or not psutil_available:
                return False, None
            
            # psutil로 프로세스 실제 실행 확인
            try:
                alive = psutil.pid_exists(pid) and psutil.Process(pid).is_running()
            except Exception:
                alive = False
            
            if alive:
                other_app = es.get("current_app", "알 수 없는 앱")
                return True, other_app
            
            return False, None
        except Exception:
            return False, None
    
    # 첫 번째 체크
    is_running, other_app = _check_other_app_running()
    
    if is_running:
        import tkinter as tk
        from tkinter import messagebox
        
        tmp = tk.Tk()
        tmp.withdraw()  # 창이 화면에 표시되기 전에 즉시 숨김
        tmp.attributes("-topmost", True)
        
        # 메시지 박스 표시
        messagebox.showwarning(
            "실행 제한",
            f"'{other_app}'이(가) 실행 중입니다.\n\n"
            f"한 번에 하나의 웍스프리 앱만 실행할 수 있습니다.\n\n"
            f"'{other_app}'을(를) 종료한 후 '확인'을 클릭하면\n"
            f"'{app_name}'이(가) 실행됩니다."
        )
        
        # 사용자가 확인을 클릭한 후 재확인
        is_still_running, _ = _check_other_app_running()
        
        tmp.destroy()
        
        if is_still_running:
            # 여전히 실행 중이면 조용히 종료 (추가 메시지 없음)
            sys.exit(0)
        else:
            # 다른 앱이 닫혔으면 계속 진행
            return
    
    # 다른 앱이 실행 중이지 않으면 정상 진행
    return
