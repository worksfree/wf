# archive/ — 레거시 SQL 파일 보관

이 폴더의 파일들은 **더 이상 사용하지 않습니다**.  
현재 DB 스키마는 상위 폴더의 파일들로 관리됩니다.

## 현재 사용 파일 (상위 폴더)

| 파일 | 용도 |
|------|------|
| `schema.sql` | ✅ 완전 마스터 스키마 (신규 DB 생성용, 단일 파일) |
| `70_seed_dev.sql` | ✅ 개발 환경 시드 데이터 (프로덕션 금지) |
| `migration_*.sql` | ✅ 증분 마이그레이션 기록 (이미 schema.sql에 통합됨) |

## 아카이브된 파일 목록

| 파일 | 폐기 이유 |
|------|---------|
| `temp_complete_db_setup_v3_legacy.sql` | schema.sql로 대체됨 |
| `temp_master_db_setup.sql` | schema.sql로 대체됨 |
| `temp_phase1_*.sql` | 단계별 설치 방식 폐기 |
| `temp_phase2_*.sql` | 단계별 설치 방식 폐기 |
| `temp_phase3_*.sql` | 단계별 설치 방식 폐기 |
| `temp_email_log.sql` | 10_extensions_tables.sql에 통합됨 |
| `temp_tracking_tables.sql` | 10_extensions_tables.sql에 통합됨 |
| `temp_admin_functions.sql` | 40_functions.sql에 통합됨 |
| `temp_fix_*.sql` | 당시 임시 수정용, 현재 스키마에 반영됨 |
| `temp_quick_fix_stats.sql` | 임시 수정, 반영 완료 |
| `temp_update_env_filter.sql` | 40_functions.sql에 통합됨 |
| `temp_setup_page_views_complete.sql` | 10_extensions_tables.sql에 통합됨 |
| `temp_add_sender_user_id.sql` | 10_extensions_tables.sql에 통합됨 |
| `temp_fix_profiles_name_sync.sql` | 30_triggers.sql에 통합됨 |
