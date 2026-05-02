# CMC 프로젝트 운영 기준

경영지도사 2차 생산관리분야 기출문제와 예시답안을 마크다운 기반으로 관리하고, 개별회차 출판본과 5개년 통합본을 생성하는 프로젝트다.  
이 문서는 프로젝트의 단일 기준 문서이며, 운영 규칙·작업 순서·스크립트 역할·향후 TODO를 함께 관리한다.

---

## 1. 프로젝트 범위

- 대상 회차: 현재 `36회` ~ `40회`
- 과목: `생산관리`, `품질경영`, `경영과학`
- 산출물
  - 소스 문제 파일: `20.기출문제/{회차}/{과목}/문제{1..6}.md`
  - 소스 예시답안 파일: `30.예시답안/{회차}/{과목}/예시답안{1..6}.md`
  - 개별회차 출판본: `40.출판물/개별회차/{회차}_경영지도사_생산관리분야_예시답안.md`
  - 5개년 통합본: `40.출판물/5개년통합/36-40회_경영지도사_생산관리분야_예시답안.md`

---

## 2. 폴더 구조

```text
cmc/
├── 10.스크립트/
│   ├── extract_questions_from_pdf.py
│   ├── merge_qqaa.py
│   ├── sync_back.py
│   ├── build_5years.py
│   ├── build_통합.py
│   └── ...
├── 20.기출문제/
│   └── {회차}/{과목}/문제{1..6}.md
├── 30.예시답안/
│   └── {회차}/{과목}/예시답안{1..6}.md
├── 40.출판물/
│   ├── 개별회차/
│   ├── 5개년통합/
│   ├── 기존출판물/
│   ├── new_candidates/
│   └── 서식/
├── CLAUDE.md
└── README.md
```

---

## 3. 베이스 룰

### 3-1. 테이블

- 표는 레이아웃 제어를 위해 반드시 HTML `<table>` 형식으로 작성한다.
- `<thead>`, `<tbody>`는 사용하지 않는다.
- `<tr>`, `<th>`, `<td>`만 사용한다.
- 첫 번째 행은 반드시 `<th>`로 작성한다.
- 가능한 한 `<tr>` 하나를 한 줄로 작성한다.

### 3-2. 수식

- 수식은 LaTeX 형식을 사용한다.
- 인라인 수식은 `$...$`
- 블록 수식은 `$$...$$`
- `\[...\]`, `\(...\)`는 사용하지 않는다.
- 수식 안의 천 단위 쉼표는 `{,}`로 표기한다.

예:

```markdown
$Q^* = \sqrt{\frac{2DC_s}{C_h}}$
$50{,}000{,}000 + 5{,}000Q$
```

### 3-3. 그림

- 네트워크/플로우차트는 Mermaid 우선 사용
- 좌표 그래프/곡선은 SVG 인라인 사용
- SVG 곡선은 3차 베지어 `C`를 우선 사용한다.
- 이미지 참조 경로는 상대경로를 기본으로 한다.
- 이미지 파일명 규칙: `{회차}_{과목}_{문제번호}_{설명}.png`
  - 예: `38_품질경영_2_분산분석표.png`
  - 저장 위치: `30.예시답안/{회차}회/res/`

### 3-4. 페이지 구분

- 소스 파일 말미 footer는 아래 형식을 유지한다.

```markdown
[목차 바로가기](#앵커)
----
<div class="page"></div>
----
```

- 중간 페이지 분리는 `<!-- pagebreak -->` 마커를 사용한다.
- `<!-- pagebreak -->`는 `merge_qqaa.py`에서 `<div class="page"></div>`로 변환된다.
- 레이아웃 최적화를 재머지 후에도 유지하려면 통합본이 아니라 소스 파일에 `<!-- pagebreak -->`를 넣는 것이 원칙이다.

### 3-5. 인코딩 및 표기

- 모든 md 파일은 UTF-8 저장
- 소수점 반올림은 문제 지시를 우선 따름
- 문제 지시가 없으면 일반적으로 소수점 첫째 자리까지 표기

### 3-6. 배점 규칙

- 대문항 총점은 기본적으로 과목별 `1번 30점`, `2번 30점`, `3~6번 각 10점`
- 예시답안 `##` 헤딩에는 대문항 총점을 표기한다.
- 예시답안 `###` 헤딩에는 소문항 배점을 표기한다.
- `###` 배점 합계는 반드시 해당 `##` 총점과 일치해야 한다.
- 가능하면 문제 본문의 번호별 배점과 예시답안 `###` 배점을 1:1 대응시킨다.

### 3-7. 헤딩 패턴

- 개별회차 문제 섹션
  - `# {회차}회 {과목} 문제`
  - `## {회차}회 {과목} 문제 {번호}`
  - `### 【문제 {번호}】 ... (30점)`
- 개별회차 예시답안 섹션
  - `# {회차}회 {과목} 예시답안`
  - `## {회차}회 {과목} 문제 {번호} 예시답안 (30점|10점)`
  - `### 【문제 {번호} - (1)】 ... (배점)`

- 예시답안 `###`는 과목명 접두 없이 `### 【문제 ...】` 패턴을 사용한다.

### 3-8. 내부 링크 규칙

- 현재 `예시답안 바로가기` 링크는 예시답안 `##` 제목의 자동 앵커를 따른다.
- 점수가 제목에 포함되므로 링크도 점수 포함 형식을 사용한다.

예:

```text
#36회-생산관리-문제-1-예시답안-30점
#36회-생산관리-문제-3-예시답안-10점
```

- 이 규칙은 현재 [merge_qqaa.py](d:\drive_files\10.worksfree\30.publish\cmc\10.스크립트\merge_qqaa.py)에 반영되어 있다.
- 추후 명시적 `<a id>` 방식으로 전환할 수 있으나, 레이아웃 영향 검증 전까지는 현 규칙을 유지한다.

---

## 4. 운영 워크플로우

현재 실무상 가장 잘 맞는 흐름은 아래와 같다.

### 4-1. 신규 회차 시작

1. 웹사이트에서 회차 PDF 수령
2. PDF에서 문제 텍스트 추출
3. 문제별 md로 분리 저장
4. 예시답안 md 작성
5. 개별회차 출판본 생성
6. PDF 확인 후 페이지 레이아웃 최적화
7. 최적화 내용을 소스로 역전개
8. 5개년 통합본 생성

### 4-2. 상세 절차

1. PDF 추출
   - 스크립트: [extract_questions_from_pdf.py](d:\drive_files\10.worksfree\30.publish\cmc\10.스크립트\extract_questions_from_pdf.py)
   - 결과: `20.기출문제/{회차}/{과목}/문제{1..6}.md`
   - 주의: 자동 파싱 결과는 반드시 수동 검수

2. 예시답안 작성
   - 위치: `30.예시답안/{회차}/{과목}/예시답안{1..6}.md`
   - 표/수식/배점/링크 규칙은 본 문서 기준

3. 개별회차 통합
   - 스크립트: [merge_qqaa.py](d:\drive_files\10.worksfree\30.publish\cmc\10.스크립트\merge_qqaa.py)
   - 예:

```bash
python 10.스크립트/merge_qqaa.py 40
```

4. PDF 변환 및 페이지 레이아웃 확인

```bash
python 10.스크립트/merge_qqaa.py 40 --pdf
```

   - playwright(Chromium) 기반 자동 변환
   - 헤더(`www.worksfree.com`) / 푸터(페이지 번호) 자동 포함
   - 내부 링크 PDF 어노테이션 자동 삽입
   - 개별회차 PDF를 보고 `문제`, `예시답안`, `표`, `이미지`가 어색하게 잘리는 지점 확인

5. 페이지 레이아웃 최적화 반영
   - 원칙: 소스 파일에 `<!-- pagebreak -->` 삽입
   - 실무 흐름: 통합 MD 수동 편집 후 `--pdf-only`로 PDF 확인, 이후 `sync_back.py`로 역전개

```bash
python 10.스크립트/merge_qqaa.py 40 --pdf-only   # 편집한 MD로 PDF 재확인
```

6. 역전개 (통합 MD 편집 내용 → 소스 파일)
   - 스크립트: [sync_back.py](d:\drive_files\10.worksfree\30.publish\cmc\10.스크립트\sync_back.py)

```bash
python 10.스크립트/sync_back.py 40 --dry   # 변경 내용 확인
python 10.스크립트/sync_back.py 40         # 실제 적용
```

7. 북마크 삽입

```bash
python 10.스크립트/add_bookmarks.py 40
```

8. 5개년 통합본 생성
   - 스크립트: [build_5years.py](d:\drive_files\10.worksfree\30.publish\cmc\10.스크립트\build_5years.py)

```bash
python 10.스크립트/build_5years.py
```

---

## 5. 스크립트 역할 정리

### 5-1. `extract_questions_from_pdf.py`

- 역할: PDF → 문제 md 초안 생성
- 현재 상태
  - 경로 하드코딩이 현재 프로젝트 구조와 어긋나 있음
  - 과목/문제 분리 로직이 회차별 서식 변화에 취약
  - OCR 및 텍스트 추출은 지원하지만 결과 검수가 필수

### 5-2. `merge_qqaa.py`

- 역할: 개별회차 출판용 md 생성 및 PDF 변환
- 현재 운영의 중심 스크립트
- 특징
  - 문제 전체 후 예시답안 전체 배치 (QQAA 방식)
  - 목차 생성 (`목차.md` 파일 우선, 없으면 자동 추출)
  - `SRC` 마커 삽입 (sync_back 역전개용)
  - `nav-bar` 생성 (예시답안 바로가기 / 목차 바로가기)
  - 명시적 `<a id>` 앵커 삽입으로 내부 링크 안정화
  - playwright(Chromium) 기반 PDF 자동 생성 (`--pdf` 옵션)
  - 헤더(`www.worksfree.com`) / 푸터(페이지 번호) 자동 삽입
  - pdfplumber 기반 내부 링크 PDF 어노테이션 자동 삽입
  - 수식 보호: `$...$` 플레이스홀더 방식으로 markdown 라이브러리 오염 방지

옵션:
```bash
python merge_qqaa.py 38              # MD만 재생성
python merge_qqaa.py 38 --pdf        # MD 재생성 + PDF 생성
python merge_qqaa.py 38 --pdf-only   # 기존 MD 유지, PDF만 재생성
python merge_qqaa.py 38 --init-toc   # 목차.md 초안 생성
```

### 5-3. `sync_back.py`

- 역할: 통합 개별회차 md의 수동 수정 내용을 소스 파일로 역전개
- 강점
  - `SRC` 영역 내부 수정 반영
  - trailing pagebreak 감지
  - 페이지 최적화 역전개에 실무적으로 매우 유용
- 주의
  - SRC 내용 전체를 소스 파일 body에 덮어쓰는 방식
  - 이중 주석(`<!-- <!-- pagebreak --> -->`) 자동 정리 로직 포함

### 5-4. `add_bookmarks.py`

- 역할: 기존 PDF에 북마크(개요) 삽입
- pdfplumber + pypdf 조합으로 `목차.md` 기반 북마크 자동 삽입
- 개별 회차 및 5개년 통합본 모두 지원

```bash
python add_bookmarks.py 38           # 38회 북마크 삽입
python add_bookmarks.py all          # 전 회차 개별 처리
python add_bookmarks.py combined     # 5개년 통합본
```

### 5-5. `build_5years.py`

- 역할: 개별회차 5개를 5개년 통합본으로 병합
- 현재 상태
  - 36~40회 고정
  - 운영에는 충분히 사용 가능
  - 향후 회차 추가 시 일반화 필요

### 5-6. deprecated 스크립트

- `deprecated_build_통합.py` — 기존 호환용 래퍼, 사용 불필요
- `deprecated_merge_QnA.py` — 구 병합 방식 (문답 스타일)
- `deprecated_merge_qqaa2.py` — 구 버전
- `deprecated_md_to_pdf.py` — 구 PDF 변환 (weasyprint 기반)
- `deprecated_convert_math_format.py` — 수식 형식 변환 유틸
- `merge_qaqa.py` — 문답문답(QAQA) 스타일 병합, 현재 미사용

---

## 6. 현재 확정된 운영 방식

문서상 원칙은 “소스 먼저 수정 후 재머지”지만, 실제 운영은 아래 방식도 허용한다.

1. 개별회차 통합본을 먼저 수정
2. 페이지 레이아웃/배점/문구 등을 다듬음
3. `sync_back.py`로 소스 파일에 역전개
4. 필요 시 `merge_qqaa.py` 재실행

즉 현재 프로젝트는 아래 두 흐름을 모두 지원한다.

- 원칙 흐름: 소스 수정 → 머지
- 실무 흐름: 통합본 수정 → 역전개 → 재머지

레이아웃 최적화 작업에서는 후자가 특히 유용하다.

---

## 7. 자주 쓰는 명령

```bash
# MD 재생성
python 10.스크립트/merge_qqaa.py 40

# MD + PDF 재생성
python 10.스크립트/merge_qqaa.py 40 --pdf

# 기존 MD로 PDF만 재생성 (페이지 구분 최적화 후 사용)
python 10.스크립트/merge_qqaa.py 40 --pdf-only

# 소스 파일 역전개 (통합 MD 수동 편집 후 사용)
python 10.스크립트/sync_back.py 40
python 10.스크립트/sync_back.py 40 --dry  # 변경 내용 확인만

# 북마크 삽입
python 10.스크립트/add_bookmarks.py 40
python 10.스크립트/add_bookmarks.py combined

# 5개년 통합본
python 10.스크립트/build_5years.py

# 기출문제 추출
python 10.스크립트/extract_questions_from_pdf.py 40
python 10.스크립트/extract_questions_from_pdf.py 40 --ocr
```

---

## 8. 41회 작업 전 TODO

### 필수

- [ ] [extract_questions_from_pdf.py](d:\drive_files\10.worksfree\30.publish\cmc\10.스크립트\extract_questions_from_pdf.py) 경로를 현재 프로젝트 구조에 맞게 수정
  - `70.publish` → `30.publish`
  - `20_기출문제` → `20.기출문제`
- [ ] PDF 추출 결과가 실제로 `20.기출문제/{회차}/{과목}/문제{1..6}.md`로 저장되는지 확인
- [ ] 41회 PDF 서식으로 과목/문제 정규식이 그대로 먹는지 검증
- [ ] 목차 생성과 문제 제목 추출이 41회 문장형 제목에도 잘 동작하는지 확인

### 권장

- [ ] [build_5years.py](d:\drive_files\10.worksfree\30.publish\cmc\10.스크립트\build_5years.py)를 회차 가변형으로 일반화
  - 예: `python build_5years.py 37 41`
- [ ] 5개년 통합 대상 회차를 자동 계산하는 옵션 검토
- [ ] `merge_qqaa.py`의 내부 링크를 명시적 `<a id>` 방식으로 바꿀지 검토
  - 단, 레이아웃 영향 검증 후 진행
- [ ] README 기준으로 실제 작업 절차와 스크립트 동작이 계속 일치하는지 유지보수

### 선택

- [ ] PDF 레이아웃 반자동 최적화 도구 검토
  - 브라우저 렌더 결과 기반 pagebreak 후보 탐지
- [ ] 배점 검증 스크립트 별도 분리
  - 문제 본문 배점 ↔ 예시답안 `##`/`###` 정합성 자동 점검

---

## 9. 링크/배점/레이아웃 관련 운영 메모

- 예시답안 `예시답안 바로가기` 링크 깨짐은 제목에 점수가 들어가면서 자동 앵커가 바뀌어 발생했다.
- 현재는 수정 범위를 최소화하기 위해 “링크 쪽이 점수 포함 앵커를 따라가도록” 처리했다.
- 이 방식은 레이아웃 변경 가능성이 가장 낮은 보수적 해결책이다.
- 페이지 레이아웃은 아직 완전 자동화되지 않았다.
- 따라서 PDF 최종본은 사람이 반드시 확인해야 한다.

---

## 10. 문서 유지관리 원칙

- 이 파일을 프로젝트의 단일 기준 문서로 유지한다.
- [CLAUDE.md](d:\drive_files\10.worksfree\30.publish\cmc\CLAUDE.md)와 [10.스크립트/README.md](d:\drive_files\10.worksfree\30.publish\cmc\10.스크립트\README.md)는 안내용으로 최소화한다.
- 실제 규칙 추가/변경은 이 파일에 먼저 반영한다.

---

---

## 11. PDF 변환 필수 환경

`--pdf` 옵션 사용 시 아래 패키지가 모두 설치되어 있어야 한다.

```bash
pip install playwright pypdf pdfplumber markdown
playwright install chromium
```

| 패키지 | 용도 |
|--------|------|
| `playwright` | Chromium 기반 HTML → PDF 변환 |
| `pypdf` | PDF 내부 링크 어노테이션 삽입 |
| `pdfplumber` | PDF 텍스트/좌표 추출 (링크 위치 탐색, 북마크) |
| `markdown` | MD → HTML 변환 (수식 보호 포함) |

---

## 12. 알려진 주의사항

### sync_back.py 실행 후 재merge 시 이중 주석 오염

- 과거 38회에서 `<!-- <!-- pagebreak --> -->` 형태로 손상된 사례 발생
- `merge_qqaa.py`와 `sync_back.py` 모두 이중 주석 자동 정리 로직이 포함되어 있음
- 소스 파일에 이중 주석이 의심될 경우 아래 패턴으로 검색:

```bash
grep -r "<!-- <!-- pagebreak" 30.예시답안/
```

### merge_qqaa.py 수식 보호

- `$...$` 수식은 markdown 라이브러리의 `__text__` → `<strong>` 변환 오염을 막기 위해
  내부적으로 `ZZMINL{n}ZZ` / `ZZMBLN{n}ZZ` 플레이스홀더로 치환 후 복원한다.
- 소스 파일에 `ZZMINL` 또는 `ZZMBLN` 문자열이 나타나면 버그 신호다.

---

최종 업데이트: 2026년 04월 04일
