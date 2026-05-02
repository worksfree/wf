#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
통합 MD → 소스 파일 역방향 동기화 스크립트

통합 MD 파일에서 수동으로 수정한 모든 내용
(페이지 구분, 테이블 너비, 텍스트 줄바꿈, 수식 등)을
소스 파일에 반영합니다.

사용법:
    python sync_back.py 40          # 40회차 소스 파일 업데이트
    python sync_back.py 40 --dry    # 변경 내용 확인만 (파일 저장 안 함)

워크플로우:
    1. merge_qqaa.py 40              → 통합 MD 생성 (SRC 마커 포함)
    2. 통합 MD 수동 편집              → 페이지 구분, 레이아웃 조정
    3. sync_back.py 40               → 소스 파일에 변경사항 반영
    4. merge_qqaa.py 40 (재실행)     → 이후에도 변경사항 유지

[레이아웃 최적화 역전개 방식]
pagebreak 위치는 두 가지 방식으로 감지됩니다:

① SRC 영역 내부 pagebreak (기존 방식)
   통합 파일의 <!-- SRC:path --> ... <!-- /SRC:path --> 안에 있는
   <div class="page"></div> 를 <!-- pagebreak --> 로 변환하여
   소스 파일 body 에 반영합니다.

② SRC 영역 바깥 trailing pagebreak (신규 방식)
   <!-- /SRC:path --> 종료 이후, 다음 ## 헤딩이나 <!-- SRC: --> 이전
   구간에서 발견되는 <div class="page"></div> 는 사용자가 nav-bar 뒤에
   수동 삽입한 레이아웃 최적화 구분자입니다.
   이를 감지해 해당 소스 파일 body 끝에 <!-- pagebreak --> 를 추가합니다.
   (다음 merge_qqaa.py 실행 시 SRC 영역 내부 마지막 줄로 재생성됩니다.)
"""

import sys
import re
import io
import difflib
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

BASE_DIR    = Path(r"D:\drive_files\10.worksfree\30.publish\cmc")
ANSWERS_DIR = BASE_DIR / "30.예시답안"
QUESTIONS_DIR = BASE_DIR / "20.기출문제"
OUTPUT_DIR  = BASE_DIR / "40.출판물"

PAGE_DIV         = '<div class="page"></div>'
PAGEBREAK_MARKER = '<!-- pagebreak -->'

SRC_OPEN  = re.compile(r'^<!-- SRC:(.+?) -->$')
SRC_CLOSE = re.compile(r'^<!-- /SRC:(.+?) -->$')

# 말미 푸터 패턴 (예시답안/문제 파일 공통)
FOOTER_PAT = re.compile(
    r'(\n+\[목차 바로가기\][^\n]*\n-{3,}\n<div class="page"></div>\n-{3,}\s*)$'
)


# ─────────────────────────────────────────────
# SRC 영역 추출
# ─────────────────────────────────────────────

def extract_src_regions(merged_text):
    """통합 파일에서 {rel_path: content_str} 를 반환한다.
    같은 rel_path 가 두 번 나오는 경우는 없으므로 dict 로 관리.
    """
    regions = {}
    lines   = merged_text.splitlines()
    stack   = []

    for i, line in enumerate(lines):
        m_open  = SRC_OPEN.match(line.strip())
        m_close = SRC_CLOSE.match(line.strip())

        if m_open:
            stack.append((m_open.group(1), i + 1))
        elif m_close and stack:
            rel_path, start = stack.pop()
            content = '\n'.join(lines[start:i])
            regions[rel_path] = content   # 마지막 값으로 덮어쓰기 (정상적으로는 1회)

    return regions


# ─────────────────────────────────────────────
# Trailing pagebreak 감지 (SRC 영역 바깥)
# ─────────────────────────────────────────────

def find_trailing_pagebreaks(merged_text):
    """
    각 <!-- /SRC:path --> 종료 이후, 다음 ## 헤딩 또는 <!-- SRC: --> 이전 구간에서
    <div class="page"></div> 가 있으면 해당 rel_path 를 True 로 반환한다.

    이는 사용자가 통합 파일에서 SRC 영역 바깥(nav-bar 이후)에 직접 삽입한
    레이아웃 최적화 페이지 구분자를 감지한다.

    Returns: {rel_path: bool}
    """
    result = {}
    lines  = merged_text.splitlines()

    for i, line in enumerate(lines):
        m_close = SRC_CLOSE.match(line.strip())
        if not m_close:
            continue
        rel_path = m_close.group(1)

        # 종료 마커 이후를 스캔: 다음 SRC 마커 또는 헤딩(#) 이전까지 PAGE_DIV 탐색
        has_pb = False
        for j in range(i + 1, len(lines)):
            stripped = lines[j].strip()
            if stripped == PAGE_DIV:
                # PAGE_DIV 발견 → 그 다음 비공백 줄 확인
                # merge_qqaa.py 자동 생성분(섹션 구분자): 단일 # 헤딩 또는 비SRC 구조 요소 앞
                # 사용자 추가분: 다음 SRC 마커 또는 ## 이상 헤딩 앞
                for k in range(j + 1, len(lines)):
                    next_stripped = lines[k].strip()
                    if not next_stripped:
                        continue
                    # <a id="..."> 앵커 태그는 건너뜀 (merge_qqaa가 ## 앞에 자동 삽입)
                    if re.match(r'^<a\s+id=', next_stripped):
                        continue
                    # 다음이 SRC 마커 → 사용자 추가분 → 역전개
                    if SRC_OPEN.match(next_stripped):
                        has_pb = True
                    # 다음이 ## 이상 헤딩 → 사용자 추가분 → 역전개
                    elif re.match(r'^#{2,}', next_stripped):
                        has_pb = True
                    # 그 외 (단일 # 헤딩, <table> 등) → merge_qqaa 자동 생성분 → 스킵
                    break
                break
            # 다음 SRC 마커 또는 섹션 헤딩에서 탐색 종료
            if SRC_OPEN.match(stripped) or SRC_CLOSE.match(stripped):
                break
            if stripped.startswith('#'):   # ## 또는 # 헤딩
                break

        result[rel_path] = has_pb

    return result


# ─────────────────────────────────────────────
# 소스 파일 재구성
# ─────────────────────────────────────────────

def split_source(original):
    """소스 파일을 (header, body, footer) 세 부분으로 분리한다."""
    # 헤더: 첫 번째 ## 줄 + 그 다음 빈줄까지
    header_match = re.match(r'^(##[^\n]+\n)', original)
    header = header_match.group(1) if header_match else ''

    # 푸터: 말미 [목차 바로가기] + ---- + <div> + ---- 패턴
    footer_match = FOOTER_PAT.search(original)
    footer = footer_match.group(1) if footer_match else ''

    # 바디: 헤더와 푸터 사이
    body_start = len(header)
    body_end   = len(original) - len(footer)
    body = original[body_start:body_end].strip()

    return header, body, footer


def reconstruct_source(header, new_body, footer):
    """header + new_body + footer 를 합쳐 완성된 소스 파일 텍스트를 반환한다."""
    return header + '\n' + new_body.strip() + footer


# ─────────────────────────────────────────────
# 변경 요약 출력
# ─────────────────────────────────────────────

def summarize_diff(original, new_text, rel_path):
    orig_lines = original.splitlines()
    new_lines  = new_text.splitlines()
    diff = list(difflib.unified_diff(orig_lines, new_lines, lineterm=''))
    added   = sum(1 for l in diff if l.startswith('+') and not l.startswith('+++'))
    removed = sum(1 for l in diff if l.startswith('-') and not l.startswith('---'))
    print(f"  {rel_path}: +{added} / -{removed} 줄")
    # 변경된 줄 미리보기 (최대 5개)
    shown = 0
    for line in diff:
        if (line.startswith('+') and not line.startswith('+++')) or \
           (line.startswith('-') and not line.startswith('---')):
            print(f"    {line[:100]}")
            shown += 1
            if shown >= 5:
                remaining = (added + removed) - shown
                if remaining > 0:
                    print(f"    ... 외 {remaining}줄")
                break


# ─────────────────────────────────────────────
# 메인 동기화 로직
# ─────────────────────────────────────────────

def get_source_path(session, rel_path):
    if '예시답안' in rel_path:
        return ANSWERS_DIR / f"{session}회" / rel_path
    else:
        return QUESTIONS_DIR / f"{session}회" / rel_path


def sync_session(session, dry_run=False):
    merged_file = OUTPUT_DIR / f"{session}회_경영지도사_생산관리분야_예시답안.md"
    if not merged_file.exists():
        print(f"오류: {merged_file} 없음 — 먼저 merge_qqaa.py {session} 를 실행하세요.")
        return

    with open(merged_file, 'r', encoding='utf-8') as f:
        merged_text = f.read()

    if '<!-- SRC:' not in merged_text:
        print("SRC 마커를 찾지 못했습니다.")
        print("→ merge_qqaa.py 를 최신 버전으로 재실행하세요.")
        return

    regions      = extract_src_regions(merged_text)
    trailing_pbs = find_trailing_pagebreaks(merged_text)

    trailing_count = sum(1 for v in trailing_pbs.values() if v)
    print(f"\n{session}회 역방향 동기화 {'[dry-run]' if dry_run else ''}")
    print(f"  통합 파일 : {merged_file.name}")
    print(f"  SRC 영역  : {len(regions)}개")
    print(f"  trailing pagebreak 감지: {trailing_count}개\n")

    updated = 0
    skipped = 0

    for rel_path, src_content in regions.items():
        src_file = get_source_path(session, rel_path)
        if not src_file.exists():
            print(f"  경고: {rel_path} → 소스 파일 없음 ({src_file})")
            continue

        with open(src_file, 'r', encoding='utf-8') as f:
            original = f.read()

        # ① SRC 영역 내부 pagebreak: <div class="page"></div> → <!-- pagebreak -->
        new_body = src_content.strip().replace(PAGE_DIV, PAGEBREAK_MARKER)

        # 이중 주석 오염 자동 정리 (<!-- <!-- pagebreak --> --> 형태 복구)
        new_body = re.sub(r'<!--\s*<!--\s*pagebreak\s*-->\s*-->', PAGEBREAK_MARKER, new_body)
        new_body = re.sub(r'<!--\s*<!--\s*pagebreak\s*-->[\s\S]*?-->', PAGEBREAK_MARKER, new_body)

        # ② SRC 영역 바깥 trailing pagebreak: body 끝에 <!-- pagebreak --> 추가
        if trailing_pbs.get(rel_path, False):
            body_stripped = new_body.rstrip()
            if not body_stripped.endswith(PAGEBREAK_MARKER):
                new_body = body_stripped + '\n\n' + PAGEBREAK_MARKER

        # 원본 소스 파일의 헤더 / 푸터 보존
        header, _old_body, footer = split_source(original)
        new_source = reconstruct_source(header, new_body, footer)

        # 변경 없으면 스킵
        if new_source == original:
            skipped += 1
            continue

        summarize_diff(original, new_source, rel_path)

        if not dry_run:
            with open(src_file, 'w', encoding='utf-8') as f:
                f.write(new_source)
        updated += 1

    # 결과 요약
    print(f"\n{'[dry-run] ' if dry_run else ''}결과: {updated}개 업데이트, {skipped}개 변경 없음")
    if dry_run and updated > 0:
        print("→ --dry 없이 재실행하면 소스 파일에 저장됩니다.")
    elif updated > 0:
        print("→ merge_qqaa.py 를 재실행하면 변경사항이 통합 파일에도 반영됩니다.")


# ─────────────────────────────────────────────
# 진입점
# ─────────────────────────────────────────────

def main():
    args    = sys.argv[1:]
    dry_run = '--dry' in args
    args    = [a for a in args if a != '--dry']

    if not args:
        print(__doc__)
        sys.exit(1)

    try:
        session = int(args[0])
    except ValueError:
        print(f"오류: 회차는 숫자여야 합니다. (입력: {args[0]})")
        sys.exit(1)

    sync_session(session, dry_run)


if __name__ == '__main__':
    main()
