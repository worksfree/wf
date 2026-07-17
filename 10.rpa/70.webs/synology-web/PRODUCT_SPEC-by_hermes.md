# [기능 명세서] WorkFree Hub & Asset Management System

**버전:** 1.0.0
**작성일:** 2024-05-22 (자동생성)
**상태:** Draft (Project Analysis Output)

---

## 1. 프로젝트 개요
본 프로젝트는 **B2B 마케팅 자동화 플랫폼(WorkFree Hub)**과 **자산 통합 관리 시스템**이 결합된 통합 서비스입니다. 
- **WorkFree Hub**: DART 공시 기반의 기업 정보 수집부터 이메일 마케팅 발송까지의 전체 파이프라인을 자동화합니다.
- **Asset Management**: 복잡한 개인/법인 자산의 실시간 시세 조회, 수익률 분석(요소별 분리), 그리고 월배당 캘린더 등을 제공합니다.

## 2. 주요 기능 요구사항 (Feature Requirements)

### 2.1 B2B 마케팅 및 고객 관리
- **B2B 데이터 수집**: DART 공시 시스템과 연동하여 기업의 기초 정보(상호, 대표자, 이메일 등)를 자동으로 크롤링하고 DB화합니다.
- **이메일 발송 엔진**: 
  - 단건/대량 발송 기능 제공 (Resend API 기반).
  - 자동 청크 분할 및 수신거부(Opt-out) 리스트 필터링 적용.
  - 다양한 마케팅 템플릿(전단지) 선택 및 머지 대량 전송 지원.
- **분석 및 관리**: 기업별 성향 파악, 발송 이력 트래킹, 수신거부 대응 자동화.

### 2.2 자산 분석 및 시세 정보 (Asset Core)
- **종목 통합 조회**: 여러 증권사 계좌를 하나로 모아 전체 포트폴리오의 평가액과 수익률을 시각화합니다.
- **실시간 데이터 처리**: Cloudflare Worker와 캐싱 시스템을 활용하여 변동성이 큰 시세 정보를 안정적으로 제공받습니다.
- **수익성 기반 분석**: 
  - 단순 수익률뿐만 아니라, 원금 대비 배당 비율(YoC)과 기간별(월/분기/연) 분배 현황을 추적합니다.
  - 투자 조건별로 자산 및 부채를 구분하여 실질적인 순자산을 계산합니다.

### 2.3 사용자 권한 시스템 (Auth & RBAC)
- **Multi-Layer 접근 제어**: 
  - 유저 수준: 일반(General), 컨설턴트(Consultant), 파트너(GFC), 관리자(Admin).
  - 데이터 보호: Supabase RLS를 통해 각 사용자는 본인의 정보 외에 접근할 수 없도록 강화된 보안 정책을 적용합니다.

## 3. 기술 스택 및 시스템 아키텍처
- **Frontend**: Vanilla JS/HTML 기반 SPA (빠른 성능과 가벼운 배포 지향).
- **Backend & Middleware**: Cloudflare Workers, Supabase Edge Functions.
- **Infrastructure**: Synology NAS(Local Storage), Cloudflare Tunnel(Secure Connection).
- **Database**: PostgreSQL (Supabase 플랫폼 활용).

## 4. 데이터베이스 모델링 (Data Schema)
- `biz_contacts`: B2B 고객/기업 정보 DB.
- `biz_send_log`: 마케팅 발송 내역 및 이력 기록.
- `instruments`: 종목 정보(코드, 이름, 기초정보).
- `holdings`: 사용자별 자산 보유 현황 및 평균 단가.
- `site_config`: 페이지 접근 권한 및 서비스 설정 값.

## 5. 자동화 시스템 (Automation)
- **Data Sync**: 일일 단위로 종목 마스터 정보를 동기화하여 데이터 정확성 유지.
- **Reporter**: 매일 새벽 정해진 시간에 시황 보고서(Daily Report)를 생성하고 이메일로 발송하는 봇 기능 포함.

---
*본 문서는 시스템 분석을 통해 자동 생성된 파일이며, 상세 사양은 각 모듈별 전문 명세서를 참조하십시오.*
