# 안내

프로젝트 운영 규칙, 라이프사이클, 스크립트 사용법, 41회 준비 TODO는 루트 [README.md](d:\drive_files\10.worksfree\30.publish\cmc\README.md)를 기준으로 관리한다.

이 파일은 중복 관리를 피하기 위한 안내용 파일이다.

---

## Claude 작업 시 필수 규칙

1. **통합 MD 또는 소스 파일을 재생성하기 전에 반드시 사용자 승인을 받는다.**
   - `merge_qqaa.py`, `sync_back.py` 실행은 파일을 덮어쓴다.

2. **스크립트 수정 시 기존 동작을 바꾸지 않는다.**
   - 옵션 추가는 기존 동작에 영향 없이 추가하는 방식으로만 한다.

3. **수식 플레이스홀더 형식은 `ZZMINL{n}ZZ` / `ZZMBLN{n}ZZ`를 사용한다.**
   - `__MATH_INLINE_n__` 형식은 markdown 라이브러리가 `<strong>`으로 변환하므로 사용 금지.

4. **pagebreak 마커는 소스 파일에서 `<!-- pagebreak -->`만 사용한다.**
   - `<div class="page"></div>`는 통합 MD에서만 사용하는 형식이다.
   - 이중 주석(`<!-- <!-- pagebreak --> -->`) 발견 시 즉시 정리한다.

5. **PDF 내부 링크는 pdfplumber 기반 좌표 탐색 방식을 사용한다.**
   - JS offsetTop 방식은 Chromium PDF 페이지 브레이크와 불일치하므로 사용 금지.
