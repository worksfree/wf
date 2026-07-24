# -*- coding: utf-8 -*-
"""
DWG(AutoCAD 도면) 표제란·BOM(부품표) 추출 핵심 로직.

배경: OCR로 CAD 도면을 다시 "읽어내는" 건 원본보다 정확도가 떨어지는 우회로다
(DWG 안 텍스트는 원래 벡터 데이터로 정확히 들어있음). 그래서 이미지 변환 없이
DWG 파일 자체를 파싱해서 텍스트를 직접 뽑는다 — 2026-07-24 실측 검증 완료
(D:\\test_data\\셈플\\초기\\ 아래 실제 도면 2건, 표제란+BOM 24행 전부 정확히 일치).

사용 도구: GNU LibreDWG(GPL, 완전 오픈소스)의 dwgread.exe.
   - 처음엔 ODA File Converter(무료지만 60일 체험판/윈도우 직접배포 링크 없음)를
     시도했으나 라이선스가 불명확해 제외.
   - dwg2dxf(DXF 변환) 경로는 "minimal" 옵션 없이는 ezdxf가 OBJECTS 섹션 파싱
     오류로 크래시하고, minimal 옵션을 쓰면 MTEXT가 87개만 남고(원본 374개)
     INSERT(블록 참조)가 통째로 유실되는 대량 데이터 손실이 실측 확인됨 —
     BOM처럼 블록 안에 들어있는 데이터는 이 경로로 아예 못 본다.
   - 대신 dwgread.exe -O JSON으로 DWG를 직접 JSON 덤프하면 전체 엔티티가
     보존된다. 이 모듈은 그 JSON을 직접 파싱한다(DXF/ezdxf 미사용).

핵심 발견 두 가지 (실측, 2026-07-24):
   1) 표제란(설계자/일자/승인 등)은 블록 속성(ATTRIB)이 아니라 modelspace에
      직접 놓인 MTEXT였다 — 라벨("DESIGN" 등)과 값("이재훈" 등)이 이름으로
      연결된 게 아니라 라벨 바로 아래(Y좌표 근접)에 값이 배치된 방식.
      → "라벨 텍스트로 앵커를 찾고, 그 아래 가장 가까운 MTEXT를 값으로 채택"
      하는 위치기반 알고리즘으로 추출한다.
   2) BOM(품번/품명/수량/재질 등 표)은 modelspace 최상위가 아니라 SolidWorks가
      DWG로 내보낼 때 자동 생성하는 "SW_TABLEANNOTATION_N" 블록 안에 MTEXT
      226개로 들어있었다 — modelspace만 훑으면 통째로 놓친다.
      → "MTEXT 자식이 가장 많은 블록 = BOM 테이블"로 찾아내 Y좌표로 행,
      헤더 행의 X좌표를 기준 열 경계로 삼아 셀을 재구성한다(줄바꿈으로 쪼개진
      셀도 같은 행·같은 열로 자동 병합됨).

주의: 표제란 라벨 목록(TITLE_BLOCK_LABELS)은 실측 검증된 회사 표준(엠디텍)
템플릿 기준이다. 다른 회사 도면은 라벨 문구가 다를 수 있으니, 새 라벨이
발견되면 이 목록에 추가하면 된다 — 완전히 다른 표제란 레이아웃이면
NEAREST-BELOW 알고리즘 자체가 안 맞을 수 있음(그 경우 좌표오프셋 방식으로
재조정 필요).
"""
import json
import subprocess
from pathlib import Path
from collections import defaultdict


# 실측 검증된 표제란 라벨 목록(라벨 자신은 값에서 제외됨)
TITLE_BLOCK_LABELS = [
    "DESIGN", "CHECK", "APPROVE", "PJT. NAME", "UNIT NAME", "PART NAME",
    "DWG NO.", "MATERIAL", "TREATMENT", "SCALE", "REMARKS", "Q'TY",
    "PROJECTION",
]


def fix_kr(s):
    """CP949 원본이 Latin-1 경유로 잘못 유니코드화된 문자열을 복원한다.
    LibreDWG가 DWG 안 한글(CP949)을 코드페이지 정보 없이 그대로 내보내면서
    실제로 재현된 문제(2026-07-24 실측) — 원본 바이트가 그대로 cp1252
    코드포인트로 통과된 흔적을 역으로 되짚어 원래 CP949 바이트로 복원한다."""
    if not isinstance(s, str):
        return s
    try:
        return s.encode("cp1252").decode("cp949")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s


def _handle(handle_field):
    """dwgread JSON의 handle 필드는 [code, size, value, ...] 형태 — 마지막 값이 실제 handle."""
    if isinstance(handle_field, list) and handle_field:
        return handle_field[-1]
    return handle_field


def run_dwgread_json(dwg_path: str, dwgread_exe: str) -> dict:
    """dwgread.exe -O JSON 실행 후 파싱된 dict 반환."""
    dwg_path = str(Path(dwg_path).resolve())
    proc = subprocess.run(
        [dwgread_exe, "-O", "JSON", dwg_path],
        capture_output=True,
        timeout=60,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"dwgread 실패(exit={proc.returncode}): {proc.stderr.decode('utf-8', 'replace')[:500]}")
    return json.loads(proc.stdout.decode("utf-8", "replace"))


def _iter_entities(objs, entity_type):
    for o in objs:
        if o.get("entity") == entity_type:
            yield o


def extract_title_block(objs, labels=None) -> dict:
    """modelspace 최상위 MTEXT 중, 알려진 라벨 텍스트를 앵커로 삼아 그 바로
    아래(Y가 작고 X가 근접한) MTEXT를 값으로 채택한다."""
    labels = labels or TITLE_BLOCK_LABELS

    # BOM 블록 등 "블록 안" 텍스트는 표제란 후보에서 제외 — modelspace 직속만.
    # dwgread JSON은 modelspace 소속 엔티티의 ownerhandle이 BLOCK_HEADER 중
    # *Model_Space를 가리키므로, "가장 많은 자식을 가진 큰 블록" 소속이 아닌
    # 것만 후보로 쓴다(간단히: owner별 개수 상위 1개 블록을 제외).
    mtexts = list(_iter_entities(objs, "MTEXT"))
    owner_counts = defaultdict(int)
    for m in mtexts:
        owner_counts[_handle(m.get("ownerhandle"))] += 1
    # 가장 큰 덩어리(대개 BOM 테이블 블록)는 표제란 후보에서 제외
    big_owner = max(owner_counts, key=owner_counts.get) if owner_counts else None
    if owner_counts.get(big_owner, 0) < 20:
        big_owner = None  # 20개 미만이면 "테이블"로 보기 어려움 — 제외하지 않음

    candidates = []
    for m in mtexts:
        if big_owner is not None and _handle(m.get("ownerhandle")) == big_owner:
            continue
        x, y, _ = m.get("ins_pt", [0, 0, 0])
        candidates.append((x, y, fix_kr(m.get("text", ""))))

    # 도면 테두리의 구역 참조 그리드(위/아래 가장자리에 1,2,3...로, 좌/우
    # 가장자리에 A,B,C...로 붙는 표준 표기)를 값 후보에서 제외한다 — 짧은
    # 숫자/알파벳 하나짜리 텍스트가 같은 Y(가로줄) 또는 같은 X(세로줄)에
    # 5개 이상 반복되면 그리드로 간주한다. 이걸 안 걸러내면 실제 값(예:
    # TREATMENT의 "CHROME")보다 우연히 더 가까운 그리드 숫자가 잘못 뽑히는
    # 사례가 실측 확인됨(2026-07-25).
    def _is_short_token(t):
        t = t.strip()
        return bool(t) and len(t) <= 2 and (t.isdigit() or t.isalpha())

    from collections import Counter
    y_counts = Counter(round(y, 0) for x, y, t in candidates if _is_short_token(t))
    x_counts = Counter(round(x, 0) for x, y, t in candidates if _is_short_token(t))
    grid_ys = {y for y, n in y_counts.items() if n >= 5}
    grid_xs = {x for x, n in x_counts.items() if n >= 5}
    candidates = [
        c for c in candidates
        if not (_is_short_token(c[2]) and (round(c[1], 0) in grid_ys or round(c[0], 0) in grid_xs))
    ]

    label_set = {lb.strip() for lb in labels}
    result = {}
    for label in labels:
        anchor = next((c for c in candidates if c[2].strip() == label), None)
        if not anchor:
            continue
        ax, ay, _ = anchor
        # 방향(위/아래)을 미리 정하지 않는다 — 같은 표제란 안에서도 열마다
        # 관례가 다르다(실측 확인): DESIGN/CHECK/APPROVE 열은 라벨 "아래"에
        # 값이 있지만, PJT. NAME/UNIT NAME/PART NAME/DWG NO. 열은 라벨보다
        # 값이 살짝 "위"에 있다. 방향을 아래로만 제한하면 진짜 값을 놓치고
        # 그 아래의 다른 필드 값을 잘못 주워오는 연쇄 오류가 발생했다.
        # 자기 자신과 다른 라벨 텍스트만 후보에서 제외하고 순수 최근접으로 찾는다.
        others = [
            c for c in candidates
            if c[2].strip() not in label_set and (c[0], c[1]) != (ax, ay)
        ]
        if not others:
            continue
        others.sort(key=lambda c: (ax - c[0]) ** 2 + (ay - c[1]) ** 2)
        result[label] = others[0][2]
    return result


# BOM 헤더에 흔히 쓰이는 단어들 — find_bom_block이 고른 "가장 큰 블록"이
# 진짜 부품표인지 확인하는 용도. 실측(2026-07-25) 확인: 단품 도면에
# BOM은 없어도 이보다 더 큰 홀/가공 치수표(헤더: "태그"/"크기"/"수량")가
# 있으면 그게 잘못 선택되는 사례가 나왔다 — 개수만으로는 표 종류를
# 구분할 수 없어서 헤더 어휘로 한 번 더 검증한다.
# "수량"/"qty"는 일부러 뺐다 — 홀 치수표에도 흔히 쓰여서 구분력이 없다는 게
# 바로 이 실측 사례로 확인됨. 구매/가공 부품에만 의미 있는 단어(제조사·
# 재질·표면처리 등)로 좁혀야 홀 치수표 같은 다른 표와 구분된다.
BOM_HEADER_KEYWORDS = [
    "part name", "partname", "품명", "품번", "부품", "material", "재질",
    "maker", "제조사", "표면처리", "열처리", "description",
]


def find_bom_block(objs, min_children: int = 10):
    """MTEXT 자식이 많은 "블록"(owner handle) 중, 헤더 어휘가 BOM처럼 보이는
    첫 번째 것을 BOM 테이블로 간주해 (owner_handle, [(x, y, text), ...]) 반환.
    없으면 (None, []).

    owner=None(= modelspace 직속, 블록 소속 아님)은 후보에서 반드시 제외한다 —
    표제란·테두리 구역참조 격자·공차표·주기 등이 전부 modelspace 직속 MTEXT라
    개수가 많으면(실측 86개) 진짜 BOM 블록(실측 18개)보다 커져서, 제외하지
    않으면 이 잡동사니 뭉치를 BOM으로 잘못 고르는 사례가 실측 확인됨
    (2026-07-25, 부품 1개짜리 최상위 조립도). 우연히 owner 값이 파이썬 None과
    겹쳐 "못 찾음" 판정으로 흡수되긴 했지만, 그건 결과가 맞았을 뿐 원인은
    잘못된 로직이었다 — modelspace 직속에 우연히 20개 미만 텍스트만 있는
    도면이었다면 쓰레기 표가 그대로 나갔을 것.

    min_children도 20 → 10으로 낮췄다 — 실측된 가장 작은 진짜 BOM(9열×2행=18개)
    보다는 작고, BOM이 없는 도면에서 관찰된 가장 큰 "가짜" 블록(7개, 실측)보다는
    커서 둘 다 안전하게 걸러진다.

    "가장 큰 블록 = BOM"이라는 가정만으로는 부족하다는 것도 실측으로 확인됨
    (2026-07-25) — 단품 도면 중 하나가 BOM 대신 더 큰 홀 가공 치수표
    (태그/크기/수량 헤더)를 갖고 있어서 그게 잘못 선택됐다. 그래서 큰 블록
    순서대로 훑으면서 BOM_HEADER_KEYWORDS와 매칭되는 첫 번째만 채택한다.
    """
    mtexts = list(_iter_entities(objs, "MTEXT"))
    by_owner = defaultdict(list)
    for m in mtexts:
        owner = _handle(m.get("ownerhandle"))
        if owner is None:
            continue  # modelspace 직속 — 블록이 아니므로 BOM 후보에서 제외
        x, y, _ = m.get("ins_pt", [0, 0, 0])
        by_owner[owner].append((x, y, fix_kr(m.get("text", ""))))

    candidates = sorted(by_owner.items(), key=lambda kv: -len(kv[1]))
    for owner, items in candidates:
        if len(items) < min_children:
            break  # 크기순 정렬이라 이후 후보는 전부 더 작음 — 더 볼 필요 없음
        joined = " ".join(t.lower() for _, _, t in items)
        if any(kw in joined for kw in BOM_HEADER_KEYWORDS):
            return owner, items
    return None, []


def reconstruct_table(cells, row_gap_ratio: float = 0.5):
    """(x, y, text) 리스트를 표(헤더 행 + 데이터 행 리스트)로 재구성한다.
    - Y좌표로 행을 클러스터링(줄바꿈으로 쪼개진 셀도 같은 행으로 병합)
    - 열 경계는 전체 셀 X값의 최대 간격(gap) 기준으로 정함(헤더 X 기준이 아님 —
      이유는 assign_col 근처 주석 참고)
    - 같은 행·같은 열에 셀이 여러 개면 텍스트를 공백으로 이어붙임(줄바꿈 셀 대응)
    """
    if not cells:
        return [], []

    ys = sorted({round(y, 1) for _, y, _ in cells}, reverse=True)
    # 기본 행 간격 추정(연속 Y 차이의 중앙값)
    gaps = [ys[i] - ys[i + 1] for i in range(len(ys) - 1)]
    gaps = [g for g in gaps if g > 0.5]
    row_spacing = sorted(gaps)[len(gaps) // 2] if gaps else 10.0
    threshold = row_spacing * row_gap_ratio

    # 1) 헤더/주요 행 밴드 결정: 인접 Y가 threshold 이내면 같은 밴드로 병합
    bands = []
    for y in ys:
        if bands and (bands[-1][0] - y) <= threshold:
            bands[-1] = (min(bands[-1][0], y), bands[-1][1] + [y])
        else:
            bands.append((y, [y]))
    band_centers = [sum(b[1]) / len(b[1]) for b in bands]

    # 2) 각 셀을 가장 가까운 밴드에 배정
    rows = defaultdict(list)
    for x, y, text in cells:
        idx = min(range(len(band_centers)), key=lambda i: abs(band_centers[i] - y))
        rows[idx].append((x, text))

    row_order = sorted(rows.keys(), key=lambda i: -band_centers[i])
    if not row_order:
        return [], []

    header_idx = row_order[0]
    header_cells = sorted(rows[header_idx], key=lambda c: c[0])
    header_texts = [t for _, t in header_cells]
    n_cols = len(header_texts)

    # 열 배정은 헤더 X를 기준으로 하지 않는다 — 헤더 라벨은 넓은 열 안에서
    # 가운데/오른쪽에 배치되는 반면 데이터는 왼쪽 정렬되는 경우가 실측
    # 확인됨(예: "PART NAME" 헤더는 x=88.78인데 실제 값은 x=27~30에서 시작).
    # 전체 표의 X 분포로 전역 경계를 잡는 방식도 시도했으나, 열마다 값의
    # 밀도가 크게 달라(빈 칸이 많은 열 vs 긴 텍스트가 많은 열) 큰 간격이
    # 엉뚱한 열 사이에 몰리는 문제가 실측 확인됨.
    #
    # 대신 "행 안에서" 판단한다: 빈 칸도 SolidWorks 표 내보내기에서 빈
    # 문자열 MTEXT로 자리 하나씩 차지하는 것으로 실측 확인됐으므로, 줄바꿈
    # 없는 보통 행은 셀 개수가 항상 헤더 개수와 정확히 일치한다 — 그러면
    # X순 정렬 후 그대로 순서대로 배정하면 된다. 줄바꿈으로 셀이 쪼개져
    # 개수가 더 많은 행은, 그 행 내부에서 가장 작은 간격부터 순서대로
    # 합쳐 개수를 헤더 개수까지 줄인다(같은 칸 안의 줄바꿈 조각이 서로
    # 가장 가까이 붙어있다는 전제 — 실측 데이터와 일치).
    def group_row_cells(row_cells):
        groups = [[c] for c in sorted(row_cells, key=lambda c: c[0])]
        while len(groups) > n_cols:
            local_gaps = [groups[i + 1][0][0] - groups[i][-1][0] for i in range(len(groups) - 1)]
            merge_at = local_gaps.index(min(local_gaps))
            groups[merge_at] = groups[merge_at] + groups[merge_at + 1]
            del groups[merge_at + 1]
        return groups

    # 1차: 모든 데이터 행의 그룹 계산(줄바꿈 병합까지) — 이 시점엔 아직
    # 열을 배정하지 않는다. 실측(2026-07-25) 확인: 일부 행은 특정 열의
    # MTEXT가 아예 없다(빈 문자열 자리조차 없음) — 예를 들어 MATERIAL·
    # 표면처리·열처리 3칸이 통째로 빠져서 그 행의 실제 셀 개수가 6개뿐인
    # 경우가 있었다. 이런 행에 순서대로(왼쪽부터) 배정하면 MAKER 값이
    # MATERIAL 칸으로 밀려 들어가는 오배정이 생긴다.
    row_groups = {idx: group_row_cells(rows[idx]) for idx in row_order[1:]}

    # 2차: "완전한" 행(그룹 수가 정확히 n_cols인 행)들의 열별 X좌표 중앙값을
    # 뽑아 열 기준 위치(reference_x)로 삼는다. 헤더 X 대신 이걸 쓰는 이유는
    # 위 주석에서 설명한 대로 헤더 라벨 위치가 데이터 위치와 어긋나기 때문.
    complete_rows = [g for g in row_groups.values() if len(g) == n_cols]

    def group_x(g):
        return sum(c[0] for c in g) / len(g)

    if complete_rows:
        col_xs_samples = [[group_x(row[col]) for row in complete_rows] for col in range(n_cols)]
        reference_x = [sorted(s)[len(s) // 2] for s in col_xs_samples]  # 열별 중앙값
    else:
        # "완전한" 행이 하나도 없는 극단적인 경우엔 헤더 X로 대체(최선의 대안).
        reference_x = [x for x, _ in header_cells]

    def assign_col(x):
        return min(range(n_cols), key=lambda i: abs(reference_x[i] - x))

    data_rows = []
    for idx in row_order[1:]:
        groups = row_groups[idx]
        row_out = ["" for _ in range(n_cols)]
        for g in groups:
            col = assign_col(group_x(g))
            texts = [t for _, t in g if t]
            merged = " ".join(texts).strip()
            row_out[col] = (row_out[col] + " " + merged).strip() if row_out[col] else merged
        data_rows.append(row_out)

    return header_texts, data_rows


def extract_dwg(dwg_path: str, dwgread_exe: str) -> dict:
    """DWG 파일 하나에서 표제란 + BOM을 추출해 dict로 반환."""
    data = run_dwgread_json(dwg_path, dwgread_exe)
    objs = data.get("OBJECTS", [])

    title_block = extract_title_block(objs)
    bom_owner, bom_cells = find_bom_block(objs)
    bom_headers, bom_rows = reconstruct_table(bom_cells) if bom_cells else ([], [])

    return {
        "title_block": title_block,
        "bom_headers": bom_headers,
        "bom_rows": bom_rows,
        "bom_found": bom_owner is not None,
    }
