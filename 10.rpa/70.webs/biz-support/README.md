# biz-support — 중소기업 지원제도 검색 (1단계 로컬 검증)

`D:\drive_files\30.사업자 및 지도사\학습자료` 의 지원제도 문서를 "지원제도 카드"로 가공하고,
로컬 임베딩 검색으로 자연어 질문에 맞는 제도를 찾아주는 파이프라인.

## 구조

```
biz-support/
├── extracted/        # PDF 텍스트 추출 결과 (.txt)
├── cards/            # 지원제도 카드 (Claude Code 세션에서 직접 가공)
│   ├── tax.json          # 조세지원 (2026 중소기업 조세지원)
│   ├── employment.json   # 고용지원금 (고용노동부·니즈환기)
│   ├── rnd_venture.json  # 연구소·벤처·정책자금
│   └── corp.json         # 법인전환·가지급금·가수금·승계
├── index.json        # 임베딩 인덱스 (build_index.py 산출물)
├── scripts/
│   ├── extract_text.py   # PDF → txt 추출
│   ├── build_index.py    # 카드 → 임베딩 인덱스
│   └── app.py            # 검색 서버 (Flask, localhost:8777)
└── web/index.html    # 테스트 페이지 (KO/EN)
```

## 실행

```powershell
cd d:\drive_files\10.worksfree\10.rpa\70.webs\biz-support
python scripts/app.py     # → http://localhost:8777
```

## 자료 갱신 절차 (비용 0원, API 키 불필요)

1. 새 PDF를 학습자료 폴더에 추가
2. `scripts/extract_text.py` 의 PRIORITY 목록에 추가 후 실행
3. **Claude Code 세션을 열고**: "extracted/새문서.txt 읽고 cards/에 카드 추가해줘"
4. `python scripts/build_index.py` 재실행

## 카드 스키마

| 필드 | 설명 |
|---|---|
| name / category | 제도명 / 분류 |
| level | `detail`(원문 기반 상세) / `catalog`(개요만, 상세는 원문 참조) |
| target / benefit / how / when | 대상 요건 / 혜택 / 신청 방법 / 시기 |
| purpose | 활용 목적 태그 (검색 가점에 사용) |
| summary | 임베딩용 요약문 — "어떤 상황에서 유용한지" 포함 |
| source | 출처 문서 |

## 기술 요약

- 임베딩: `intfloat/multilingual-e5-small` (로컬, 무료). query/passage 접두사 필수
- 검색: 정규화 벡터 내적(코사인) 브루트포스 + 제도명 키워드 가점 — 카드 수백 건 규모에선 벡터DB 불필요
- 2단계(허브 배포) 시: index.json을 정적 배포하고 질문 임베딩만 Cloudflare Workers AI 등 무료 수단으로 대체 예정

## 미가공 자료 (2차 대상)

- 2024년도 중소벤처기업 지원사업 중기부/유관기관 (각 725p/1103p — 개별 사업 카드화)
- 법인컨설팅 강의교재 Part 1~6 (173MB — 컨설팅 논리 보강용)
- 가지급금 컨설팅(원본).pptx, 벤처확인기업 우대지원제도 세부내용.pdf(인코딩 깨짐 → 원본 재추출 필요)
- 임금명세서+작성사례.hwp (HWP 파싱 필요)
