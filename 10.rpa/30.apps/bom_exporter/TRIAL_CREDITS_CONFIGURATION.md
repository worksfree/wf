# 체험판 크레딧 설정 구조

## 📋 개요

체험판 크레딧은 **설정 파일 기반**으로 관리되며, 코드 수정 없이 배포 후에도 정책 변경이 가능합니다.

## 🏗️ 설정 구조

### 1. 앱별 설정 파일
**위치**: `config/{app_name}/app_config.json`

```json
{
  "identity": {
    "app_name": "bom_exporter",
    "short_name": "be",
    "display_name": "Bom Exporter"
  },
  "policy": {
    "trial_credits": 10000,        // ⭐ 체험판 크레딧 설정
    "credit_per_work": 100,
    "available_work": 100,
    "credit_type": "per_file"
  }
}
```

### 2. 사용자별 로컬 설정
**위치**: `~/.wf_rpa/wf_rpa_config.json`

```json
{
  "user_info": {
    "email": "user@example.com",
    "license_type": "trial",
    "trial_credits": 10000,        // ⭐ 등록 시점의 크레딧
    "used_credits": 0
  }
}
```

### 3. 앱별 크레딧 파일
**위치**: `~/.wf_rpa/{app_name}/credit_history.json`

```json
{
  "app_policy": {
    "trial_credits": 10000         // ⭐ 앱별 정책 (app_config.json에서 로드)
  },
  "trial_credits": 10000,          // 현재 체험판 잔액
  "purchased_credits": 0,
  "usage_history": []
}
```

## 🔄 크레딧 로드 우선순위

```
1. config/{app_name}/app_config.json (번들 정책)
   ↓
2. ~/.wf_rpa/{app_name}/app_config.json (로컬 정책 오버라이드)
   ↓
3. WorksFreeManager.policy['trial_credits']
   ↓
4. 기본값: 10000 (fallback)
```

## 📝 코드 구현

### wf_credit_manager.py
```python
def _initialize_credits(self):
    """크레딧 파일이 없을 경우 체험판으로 초기화"""
    if not self.credit_file.exists():
        # app_config.json에서 trial_credits 로드 (기본값 10000)
        trial_amount = self.policy.get("trial_credits", 10000)
        
        initial_data = {
            "app_policy": self.policy,
            "trial_credits": trial_amount,  # ⭐ 설정 파일에서 로드
            "purchased_credits": 0,
            ...
        }
```

### wf_license.py
```python
def register_trial_license_with_hwid(user_email, verification_code, hw_info):
    """하드웨어 정보 기반 체험판 라이선스 등록"""
    
    # 체험판 크레딧은 설정에서 로드 (기본값 10000)
    # 주의: 이 함수는 app_name을 모르므로 기본값만 사용
    # 실제 크레딧은 각 앱의 WorksFreeManager가 app_config.json에서 로드
    trial_credits = 10000  # 기본값 (각 앱은 자체 app_config.json 참조)
    
    config["user_info"] = {
        "trial_credits": trial_credits,  # ⭐ 각 앱은 app_config.json에서 실제 값 로드
        ...
    }
```

## ✅ 장점

### 1. **유연한 정책 관리**
- 앱별로 다른 크레딧 정책 적용 가능
- 배포 후 설정 파일만 수정하여 정책 변경
- 코드 재빌드 불필요

### 2. **계층적 구조**
```
번들 설정 (config/app_config.json)
  ↓ 오버라이드
로컬 설정 (~/.wf_rpa/app_config.json)
  ↓ 적용
사용자 크레딧 (credit_history.json)
```

### 3. **앱별 독립성**
- BOM Exporter: 10000 크레딧
- DWG Batch Print: 5000 크레딧 (예시)
- Korean Filename Normalizer: 무제한 (예시)

### 4. **디버깅 용이**
- 설정 파일 확인만으로 정책 파악 가능
- 로그에 policy 정보 출력

## 🔧 설정 변경 방법

### 앱 배포 전 (번들 정책 변경)
```bash
# config/bom_exporter/app_config.json 편집
{
  "policy": {
    "trial_credits": 20000  # 10000 → 20000으로 변경
  }
}
```

### 앱 배포 후 (로컬 정책 오버라이드)
```bash
# ~/.wf_rpa/bom_exporter/app_config.json 생성/편집
{
  "policy": {
    "trial_credits": 15000  # 특정 사용자만 15000으로 변경
  }
}
```

## 📊 앱별 크레딧 정책 현황

| 앱 | trial_credits | credit_per_work | 가용 작업 수 |
|----|---------------|-----------------|-------------|
| **BOM Exporter** | 10,000 | 100 | 100회 |
| DWG Batch Print | (확인 필요) | (확인 필요) | (확인 필요) |
| DWG Classifier | (확인 필요) | (확인 필요) | (확인 필요) |

## 🎯 권장사항

1. **앱별 적절한 크레딧 설정**
   - 작업 복잡도에 따라 차등 적용
   - BOM Exporter: 파일 처리 복잡 → 크레딧 높게

2. **정책 변경 시**
   - app_config.json 수정
   - 빌드 스크립트가 자동으로 배포 패키지에 포함
   - 기존 사용자는 앱 업데이트 시 새 정책 적용

3. **테스트 시**
   - 개발 환경: app_config.json 직접 수정
   - 프로덕션: Google Sheets 동기화로 중앙 관리

## 📖 관련 파일

- `config/bom_exporter/app_config.json` - 번들 정책
- `wf_credit_manager.py` - 크레딧 관리 로직
- `wf_license.py` - 라이선스 등록 로직
- `bom_exporter.spec` - 빌드 시 설정 파일 포함

---

**마지막 업데이트**: 2026-01-06  
**변경 사항**: 하드코딩 제거, 설정 파일 기반 구조로 전환
