# JSON 필드 상세 분류 가이드

## 📊 5개 앱 수정 상태 확인

### ✅ 완료된 수정 사항 (5개 앱 모두)

| 앱 | app_info 제거 | app_config→runtime_config | spec 파일 수정 |
|----|--------------|---------------------------|---------------|
| bom_exporter | ✅ | ✅ | ✅ |
| dwg_batch_print | ✅ | ✅ | ✅ |
| conversion_verifier | ✅ | ✅ | ✅ |
| dwg_classifier | ✅ | ✅ | ✅ |
| korean_filename_normalizer | ✅ | ✅ | ✅ |

**결론**: 5개 앱 모두 JSON 구조 리팩토링 완료 ✅

---

## 📋 JSON 파일별 전체 필드 분류

### 1️⃣ policy.json (앱별 정책)

#### 📌 **유지할 값** (배포 시 그대로 복사)

| 필드 | 예시 값 | 설명 | 변경 금지 이유 |
|------|---------|------|---------------|
| `identity.app_name` | `"bom_exporter"` | 앱 내부 ID | 앱 식별자 |
| `identity.short_name` | `"be"` | 앱 단축명 | 코드에서 사용 |
| `identity.display_name` | `"BOM Exporter"` | UI 표시명 | 사용자 표시용 |
| `policy.icon_text` | `"B2E"` | 아이콘 텍스트 | UI 아이콘 |
| `policy.description` | `"도면 처리 앱"` | 앱 설명 | 메타데이터 |
| `policy.trial_credits` | `10000` / `50000` / `-1` | 체험판 크레딧 | **핵심 비즈니스 정책** |
| `policy.credit_per_work` | `100` | 작업당 차감 크레딧 | **핵심 비즈니스 정책** |
| `policy.credit_type` | `"per_file"` | 크레딧 차감 방식 | 정책 설정 |

**배포 처리**: 
```python
# spec 파일에서
shutil.copy2(policy_src, bundled_policy)  # 그대로 복사
```

#### 🚫 **제거할 값** (존재하면 안됨)

| 필드 | 제거 이유 |
|------|-----------|
| `app_config` | runtime_config로 이동 (구조 개선) |
| `build_count` | settings.json의 runtime_config에만 있어야 함 |
| `last_updated` | settings.json의 runtime_config에만 있어야 함 |
| `full_version` | settings.json의 runtime_config에만 있어야 함 |
| `version` | 중복, 제거됨 |
| `source` | 불필요, 제거됨 |

---

### 2️⃣ settings.json (앱별 런타임 설정)

#### 📌 A. **유지할 값** (배포 시 포함, 변경 안함)

##### **solidworks 섹션** (bom_exporter만 해당)

| 필드 | 예시 값 | 설명 | 비고 |
|------|---------|------|------|
| `solidworks.program_path` | `"C:\\Program Files\\SOLIDWORKS Corp\\SOLIDWORKS\\SLDWORKS.exe"` | SW 실행 경로 | 기본값 제공 |

##### **runtime_config 섹션** (기본값 유지)

| 필드 | 예시 값 | 설명 | 변경 여부 |
|------|---------|------|----------|
| `runtime_config.restart_count` | `20` | 재시작 횟수 | 🔄 정책 동기화로 변경 가능 |
| `runtime_config.topmost` | `true` | 최상위 창 | 🔄 사용자 설정으로 변경 |
| `runtime_config.auto_restart` | `true` | 자동 재시작 | 🔄 정책 동기화로 변경 |
| `runtime_config.speed_mode` | `"normal"` | 속도 모드 | 🔄 사용자 설정으로 변경 |
| `runtime_config.base_wait_time` | `60` | 기본 대기시간 | 🔄 정책 동기화로 변경 |
| `runtime_config.seconds_per_10mb` | `60` | 10MB당 초 | 🔄 정책 동기화로 변경 |
| `runtime_config.include_thumbnail` | `true` | 썸네일 포함 | 🔄 사용자 설정으로 변경 |
| `runtime_config.ui_scale` | `1.0` | UI 배율 | 🔄 사용자 설정으로 변경 |
| `runtime_config.language` | `"ko"` | 언어 설정 | 🔄 사용자 설정으로 변경 |
| `runtime_config.max_workers` | `4` | 최대 작업자 수 | 🔄 설정으로 변경 |
| `runtime_config.memory_limit_mb` | `1024` | 메모리 제한 | 🔄 설정으로 변경 |
| `runtime_config.admin_mode` | `false` | 관리자 모드 | 🔄 사용자 설정으로 변경 |

##### **ui_config 섹션** (기본값 유지)

| 필드 | 예시 값 | 설명 | 변경 여부 |
|------|---------|------|----------|
| `ui_config.topmost` | `true` | 최상위 창 | 🔄 사용자 설정 |
| `ui_config.show_log` | `false` | 로그 표시 | 🔄 사용자 설정 |
| `ui_config.auto_scroll` | `true` | 자동 스크롤 | 🔄 사용자 설정 |
| `ui_config.show_progress` | `true` | 진행률 표시 | 🔄 사용자 설정 |
| `ui_config.window_width` | `580` | 창 너비 | 🔄 사용자 설정 |
| `ui_config.window_height` | `180` | 창 높이 | 🔄 사용자 설정 |
| `ui_config.theme` | `"system"` | 테마 | 🔄 사용자 설정 |
| `ui_config.minimize_to_tray` | `false` | 트레이 최소화 | 🔄 사용자 설정 |

##### **logging_config 섹션** (기본값 유지)

| 필드 | 예시 값 | 설명 | 변경 여부 |
|------|---------|------|----------|
| `logging_config.log_level` | `"INFO"` | 로그 레벨 | 🔄 사용자 설정 |
| `logging_config.log_to_file` | `true` | 파일 로깅 | 🔄 사용자 설정 |
| `logging_config.max_log_size_mb` | `10` | 최대 로그 크기 | 🔄 사용자 설정 |
| `logging_config.rotate_logs` | `true` | 로그 로테이션 | 🔄 사용자 설정 |
| `logging_config.backup_count` | `5` | 백업 개수 | 🔄 사용자 설정 |

##### **앱별 특수 섹션** (기본값 유지)

**bom_exporter**: 없음 (solidworks만)

**dwg_batch_print**: 
- `print_settings.default_input_dir`: `""` (빈 문자열 유지)
- `print_settings.default_output_dir`: `""` (빈 문자열 유지)

**conversion_verifier**: 없음

**dwg_classifier**:
- `classification_config.*`: 분류 설정 (기본값 유지)
- `classifier_settings.*`: 분류기 설정 (기본값 유지)

**korean_filename_normalizer**:
- `normalizer_settings.*`: 정규화 설정 (기본값 유지)

#### 🔄 **변경할 값** (빌드 시 자동 주입)

##### **runtime_config 섹션** (빌드 시 주입)

| 필드 | 예시 값 | 설명 | 주입 시점 |
|------|---------|------|----------|
| `runtime_config.run_mode` | `"release"` | 실행 모드 | ⚙️ **spec 파일이 강제로 "release" 설정** |
| `runtime_config.full_version` | `"v0.9.1.2"` | 전체 버전 | ⚙️ **spec 파일이 빌드 시 주입** |
| `runtime_config.build_count` | `212` | 빌드 횟수 | ⚙️ **spec 파일이 빌드 시 주입** |
| `runtime_config.last_updated` | `"2026-01-05 21:17:43"` | 마지막 업데이트 | ⚙️ **spec 파일이 빌드 시 주입** |

**배포 처리**:
```python
# spec 파일에서 자동 처리
settings_data['runtime_config']['run_mode'] = 'release'  # 강제 설정
settings_data['runtime_config']['full_version'] = f"v{APP_VERSION_FULL}"
settings_data['runtime_config']['build_count'] = VERSION_INFO['build_count']
settings_data['runtime_config']['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
```

#### ⚠️ **초기화할 값** (배포 시 빈 값으로)

##### **ui_config 섹션** (사용자 경로 초기화)

| 필드 | 초기화 값 | 이유 | 배포 시 처리 |
|------|----------|------|-------------|
| `ui_config.last_selected_folder` | `""` | 개발자 경로 유출 방지 | ⚠️ **spec 파일이 빈 문자열로 초기화** |
| `ui_config.window_geometry_override` | `""` | 개발PC 창 위치 유출 방지 | ⚠️ **spec 파일이 빈 문자열로 초기화** |

**배포 처리**:
```python
# spec 파일에서 자동 처리
settings_data['ui_config']['last_selected_folder'] = ""
settings_data['ui_config']['window_geometry_override'] = ""
```

##### **앱별 특수 필드** (경로 초기화)

**dwg_classifier**:
- `classifier_settings.output_folder`: `""` (개발 경로 제거)

**korean_filename_normalizer**:
- `normalizer_settings.default_folder_path`: `""` (개발 경로 제거)

**conversion_verifier**:
- `ui_config.last_selected_folder`: `""` (개발 경로 제거)

#### 🚫 **제거할 값** (존재하면 안됨)

| 필드 | 제거 이유 | 원래 위치 |
|------|-----------|----------|
| `app_info` | 전체 섹션 제거 | settings.json |
| `app_info.last_updated` | runtime_config.last_updated로 이동 | app_info |
| `app_info.name` | 불필요 (identity에 있음) | app_info |
| `app_config` | runtime_config로 이름 변경 | settings.json |
| `processed_files` | 런타임 데이터 (빈 객체로 유지) | settings.json |
| `user_settings` | 런타임 데이터 (빈 객체로 유지) | settings.json |

---

### 3️⃣ credit_history.json (사용자별 크레딧 이력)

#### 🚫 **배포 제외** (파일 자체를 번들에 포함하지 않음)

이 파일은 사용자가 앱을 처음 등록할 때 자동으로 생성됩니다.

##### **생성 시점**: 사용자 등록 시 `wf_credit_manager.py`가 자동 생성

##### **파일에 포함되는 모든 필드** (참고용)

| 필드 | 예시 값 | 생성 시점 | 변경 여부 |
|------|---------|----------|----------|
| `user_email` | `"user@example.com"` | 등록 시 | ✅ 사용자 입력 |
| `verification_code` | `"ABC123"` | 등록 시 | ✅ 서버 발급 |
| `hardware_fingerprint` | `"ABC123..."` | 등록 시 | ✅ **자동 생성 (매번 새로 계산)** |
| `cpu_id` | `"BFEBFBFF..."` | 등록 시 | ✅ **자동 생성 (하드웨어)** |
| `mainboard_id` | `"BASE123..."` | 등록 시 | ✅ **자동 생성 (하드웨어)** |
| `registration_date` | `"2026-01-05T10:30:00"` | 등록 시 | ✅ 등록 시각 |
| `license_type` | `"trial"` | 등록 시 | 🔄 구매 시 `"paid"` |
| `trial_credits_remaining` | `10000` | 등록 시 | 🔄 사용할 때마다 감소 |
| `used_credits` | `0` | 등록 시 | 🔄 사용할 때마다 증가 |
| `status` | `"active"` | 등록 시 | 🔄 라이센스 상태 |
| `purchase_date` | `null` | 등록 시 | 🔄 구매 시 설정 |
| `expiry_date` | `null` | 등록 시 | 🔄 구매 시 설정 |
| `history` | `[]` | 등록 시 | 🔄 사용할 때마다 추가 |
| `history[].timestamp` | `"2026-01-05T10:35:00"` | 사용 시 | - |
| `history[].credits_used` | `100` | 사용 시 | - |
| `history[].work_type` | `"bom_export"` | 사용 시 | - |
| `history[].remaining` | `9900` | 사용 시 | - |

**배포 시 처리**: 
- ❌ 번들에 포함하지 않음
- ❌ 템플릿 파일도 필요 없음
- ✅ 사용자 등록 시 `wf_credit_manager.py`가 자동 생성

---

### 4️⃣ wf_rpa_config.json (전역 설정)

#### 📌 **유지할 값** (배포 시 그대로 복사)

##### **email_settings 섹션**

| 필드 | 예시 값 | 설명 | 변경 금지 이유 |
|------|---------|------|---------------|
| `email_settings.smtp_server` | `"smtp.gmail.com"` | SMTP 서버 | 서비스 설정 |
| `email_settings.smtp_port` | `587` | SMTP 포트 | 서비스 설정 |
| `email_settings.sender_email` | `"noreply@worksfree.com"` | 발신 이메일 | 서비스 설정 |
| `email_settings.sender_password` | `"encrypted_password"` | 발신 비밀번호 | 서비스 설정 |
| `email_settings.use_tls` | `true` | TLS 사용 | 서비스 설정 |

##### **google_sheets 섹션**

| 필드 | 예시 값 | 설명 | 변경 금지 이유 |
|------|---------|------|---------------|
| `google_sheets.spreadsheet_id` | `"1A2B3C..."` | 스프레드시트 ID | 서비스 설정 |
| `google_sheets.policy_sheet_name` | `"app_policies"` | 정책 시트명 | 서비스 설정 |
| `google_sheets.user_sheet_name` | `"users"` | 사용자 시트명 | 서비스 설정 |
| `google_sheets.sync_interval_hours` | `24` | 동기화 간격 | 서비스 설정 |

**배포 처리**: 
```python
# spec 파일에서
shutil.copy2(source_config, wf_rpa_dir / 'wf_rpa_config.json')
```

#### 🚫 **제거할 값** (존재하면 안됨)

| 필드 | 제거 이유 |
|------|-----------|
| `version` | 불필요, 제거됨 |
| `last_updated` | 불필요, 제거됨 |

---

## 📊 필드 분류 요약표

### 카테고리별 통계

| 파일 | 유지 | 초기화 | 변경 (빌드) | 제거 | 배포 제외 |
|------|------|--------|------------|------|----------|
| **policy.json** | 8 | 0 | 0 | 6 | - |
| **settings.json** | ~30 | 2-5 | 4 | 6 | - |
| **credit_history.json** | - | - | - | - | 전체 |
| **wf_rpa_config.json** | 11 | 0 | 0 | 2 | - |
| **Google credentials** | 1 | 0 | 0 | 0 | - |

---

## 🔐 보안 체크리스트

### ✅ 배포 시 자동 보장되는 사항 (spec 파일)

1. **개발자 정보 유출 방지**
   - `ui_config.last_selected_folder`: 빈 문자열로 초기화
   - `ui_config.window_geometry_override`: 빈 문자열로 초기화
   - 앱별 경로 필드: 빈 문자열로 초기화

2. **하드웨어 정보 유출 방지**
   - `credit_history.json`: 번들에 미포함
   - `hardware_fingerprint`: 번들에 미포함
   - `cpu_id`: 번들에 미포함
   - `mainboard_id`: 번들에 미포함

3. **배포 모드 보장**
   - `runtime_config.run_mode`: 강제로 "release"
   - 소스가 "demo"여도 배포는 "release"

4. **버전 정보 자동화**
   - `runtime_config.full_version`: 빌드 시 자동 주입
   - `runtime_config.build_count`: 빌드 시 자동 증가
   - `runtime_config.last_updated`: 빌드 시각 자동 기록

---

## 🎯 실무 활용 가이드

### 개발 시
- `run_mode`: `"demo"` 사용 가능 (배포 시 자동 변경)
- `last_selected_folder`: 개발 경로 사용 가능 (배포 시 자동 초기화)
- `window_geometry_override`: 개발PC 위치 사용 가능 (배포 시 자동 초기화)

### 배포 전
```bash
# 소스 검증 (run_mode=demo, 경로 포함 상태여도 OK)
python scripts/verify_bundle.py source bom_exporter
```

### 빌드 시
- spec 파일이 모든 값을 자동으로 처리
- 개발자 개입 불필요

### 배포 후
```bash
# 번들 검증 (run_mode=release, 경로 초기화 확인)
python scripts/verify_bundle.py bundle bom_exporter
```

---

## 📝 참고 사항

### trial_credits 앱별 정책

현재 앱마다 다른 체험판 크레딧을 사용 중:

| 앱 | trial_credits | 의미 |
|----|---------------|------|
| bom_exporter | 10,000 | 표준 (100회) |
| dwg_batch_print | 50,000 | 확장 (500회) |
| conversion_verifier | -1 | 무제한 |
| dwg_classifier | 50,000 | 확장 (500회) |
| korean_filename_normalizer | -1 | 무제한 |

이것은 **의도된 설계**로 보이며, 앱별로 다른 정책을 적용하는 것이 가능합니다.

### run_mode 소스 vs 배포

| 상태 | 소스 | 배포 |
|------|------|------|
| bom_exporter | release | release ✅ |
| dwg_batch_print | **demo** | release ✅ (자동 변경) |
| conversion_verifier | **demo** | release ✅ (자동 변경) |
| dwg_classifier | **demo** | release ✅ (자동 변경) |
| korean_filename_normalizer | **demo** | release ✅ (자동 변경) |

**결론**: 소스가 demo여도 배포는 항상 release로 보장됩니다. ✅
