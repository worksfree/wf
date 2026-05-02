# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 역할

웹 자동화 및 웹 관련 스크립트 모음.

## 폴더 목록

| 폴더 | 내용 |
|------|------|
| `kstartup-web/` | K-Startup 웹사이트 자동화 (Selenium 기반) |
| `learn_investment/` | 투자 학습 관련 웹 스크립트 |
| `시연/` | 데모/시연용 웹 스크립트 |

## kstartup-web

K-Startup 포털 웹 자동화 스크립트. 주요 문서:
- `README.md` — 프로젝트 개요 및 실행 방법
- `ELEMENT_CLICK_INTERCEPTED_FIX.md` — `ElementClickInterceptedException` 해결 가이드
- `ELEMENT_FINDING_DIAGNOSTIC_GUIDE.md` — 요소 탐색 진단 가이드
- `IMAGE_CLICK_WEB_SCENARIOS.md` — 이미지 기반 클릭 시나리오

Selenium WebDriver 기반. 요소 탐색 실패 및 클릭 인터셉트 이슈가 빈번하므로 위 가이드 문서를 참고.
