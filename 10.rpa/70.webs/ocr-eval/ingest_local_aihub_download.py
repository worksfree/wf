"""
D:\\test_data\\ocr_test\\ 에 실제로 받아둔 AI-Hub 원본(중첩 zip 구조)을 읽어서,
각 데이터셋에서 일부만 샘플링 + 정답 텍스트를 뽑아 aihub_samples/{category}/에
채워 넣는 어댑터. 이후 `ingest_aihub_samples.py`를 그대로 실행하면 스윕+리포트가
자동으로 나온다(그 스크립트는 이 폴더 구조를 이미 기대하도록 만들어져 있음).

2026-07-24 실측 확인한 사실:
- 데이터셋마다 라벨 JSON 스키마가 전부 다르다(4가지 확인, 아래 EXTRACTORS 참고).
- 각 데이터셋은 TS_*.zip(원천/이미지) ↔ TL_*.zip(라벨) 페어가 파일명 접두사만
  TS_/TL_로 다르고 나머지는 동일 — 이 대응으로 라벨을 찾는다.
- 239(건축 도면)는 원천데이터 폴더에 OBJ/OCR/SPA/STR 4종류가 섞여 있는데, 텍스트가
  있는 건 TS_OCR_*.zip/TL_OCR*.zip 뿐이다(나머지는 문·창·벽 등 객체 탐지용, 텍스트 없음).
- 055(금융업 특화 문서 OCR)는 이번에 받은 파일(TS1.zip/TS2.zip)이 둘 다 0바이트 —
  다운로드가 실패한 상태. 이 스크립트는 자동으로 건너뛰고 경고만 낸다 — 재다운로드 필요.

카테고리 매핑(AIHub_샘플_다운로드_가이드.md와 동일):
  023(공공) · 239(건축도면) → manufacturing
  025(금융및물류)           → retail
  055(금융업특화)·056(의약품화장품) → fnb
"""
import glob, json, os, random, re, shutil, sys, tempfile, zipfile

# Windows에서 stdout이 cp949로 인코딩을 시도해 em-dash(—) 등에서 죽는 문제 방지
# (2026-07-23 sweep_contrast_sharpen.py 야간 크래시와 동일 원인 — 재발 방지 메모 참고)
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE = os.path.dirname(__file__)
ROOT = r"D:\test_data\ocr_test"
OUT_DIR = os.path.join(BASE, "aihub_samples")
ZIPS_PER_DATASET = 3   # 데이터셋당 샘플링할 TS 압축(shard) 개수
IMAGES_PER_ZIP = 3     # 압축 하나당 뽑을 이미지 수 → 데이터셋당 최대 9장

random.seed(42)  # 재현 가능하도록 고정


def find_ts_tl_pairs(source_dir, label_dir, ts_prefix_filter=None):
    """TS_*.zip 목록과, 이름을 TL_로 바꿔 매칭되는 라벨 zip 경로를 함께 반환.
    239(건축도면)처럼 이미지는 TS_OCR_1.zip/TS_OCR_2.zip으로 나뉘어 있는데 라벨은
    TL_OCR.zip 하나로 합쳐진 경우가 있어 — 정확한 이름 치환이 실패하면, 같은
    접두어(TL_OCR*)로 시작하는 라벨 zip이 정확히 1개일 때 그걸 공용으로 사용한다."""
    pairs = []
    for ts in glob.glob(os.path.join(source_dir, "**", "*.zip"), recursive=True):
        name = os.path.basename(ts)
        if not name.startswith("TS"):
            continue
        if ts_prefix_filter and not name.startswith(ts_prefix_filter):
            continue
        tl_name = "TL" + name[2:]
        tl_candidates = glob.glob(os.path.join(label_dir, "**", tl_name), recursive=True)
        if not tl_candidates and ts_prefix_filter:
            fallback_pattern = "TL" + ts_prefix_filter[2:] + "*.zip"
            fallback = glob.glob(os.path.join(label_dir, "**", fallback_pattern), recursive=True)
            if len(fallback) == 1:
                tl_candidates = fallback
        if tl_candidates:
            pairs.append((ts, tl_candidates[0]))
    return pairs


def read_json_from_zip(zf, member_name):
    with zf.open(member_name) as f:
        return json.load(f)


# ── 스키마별 정답 텍스트 추출기 (읽기 순서 대략 재현: y먼저, 그 안에서 x) ──

def extract_bbox_style(data, key_names=("Bbox", "bbox")):
    """023/025: {..., 'Bbox'|'bbox': [{'data':str,'x':[4],'y':[4]}, ...]}"""
    boxes = None
    for k in key_names:
        if k in data:
            boxes = data[k]
            break
    if not boxes:
        return None
    items = []
    for b in boxes:
        text = (b.get("data") or "").strip()
        if not text:
            continue
        yc = sum(b["y"]) / len(b["y"])
        xc = sum(b["x"]) / len(b["x"])
        items.append((yc, xc, text))
    if not items:
        return None
    items.sort(key=lambda t: (round(t[0] / 40), t[1]))
    return "\n".join(t[2] for t in items)


def extract_polygons_style(data):
    """056: {..., 'annotations': [{'polygons': [{'text':str,'points':[[x,y]x4]}, ...]}]}"""
    anns = data.get("annotations")
    if not anns:
        return None
    items = []
    for ann in anns:
        for poly in ann.get("polygons", []):
            text = (poly.get("text") or "").strip()
            pts = poly.get("points")
            if not text or not pts:
                continue
            yc = sum(p[1] for p in pts) / len(pts)
            xc = sum(p[0] for p in pts) / len(pts)
            items.append((yc, xc, text))
    if not items:
        return None
    items.sort(key=lambda t: (round(t[0] / 40), t[1]))
    return "\n".join(t[2] for t in items)


def extract_coco_ocr_attr(data):
    """239(TS_OCR/TL_OCR): COCO 스타일. annotations[].attributes.OCR 에 텍스트,
    annotations[].bbox = [x,y,w,h]. 여러 이미지가 한 JSON에 섞여 있을 수 있어
    image_id별로 묶어서 반환: {image_id: text}"""
    images = {img["id"]: img.get("file_name") for img in data.get("images", [])}
    per_image = {}
    for ann in data.get("annotations", []):
        text = (ann.get("attributes", {}) or {}).get("OCR", "").strip()
        if not text:
            continue
        x, y = ann["bbox"][0], ann["bbox"][1]
        img_id = ann["image_id"]
        per_image.setdefault(img_id, []).append((y, x, text))
    result = {}
    for img_id, items in per_image.items():
        items.sort(key=lambda t: (round(t[0] / 40), t[1]))
        fname = images.get(img_id)
        if fname:
            result[fname] = "\n".join(t[2] for t in items)
    return result


def process_dataset(name, source_dir, label_dir, category, ts_prefix_filter=None, schema="bbox"):
    if not os.path.isdir(source_dir):
        print(f"[skip] {name}: 원천데이터 폴더 없음 — {source_dir}")
        return 0
    pairs = find_ts_tl_pairs(source_dir, label_dir, ts_prefix_filter)
    if not pairs:
        print(f"[skip] {name}: TS/TL 매칭 zip 없음")
        return 0
    # 0바이트(다운로드 실패) zip 걸러내기
    pairs = [(ts, tl) for ts, tl in pairs if os.path.getsize(ts) > 0 and os.path.getsize(tl) > 0]
    if not pairs:
        print(f"[skip] {name}: 매칭된 zip이 전부 0바이트(다운로드 실패로 추정) — 재다운로드 필요")
        return 0

    sample = random.sample(pairs, min(ZIPS_PER_DATASET, len(pairs)))
    out_cat_dir = os.path.join(OUT_DIR, category)
    os.makedirs(out_cat_dir, exist_ok=True)
    saved = 0

    for ts_path, tl_path in sample:
        try:
            with zipfile.ZipFile(ts_path) as tszf, zipfile.ZipFile(tl_path) as tlzf:
                img_members = [m for m in tszf.namelist() if re.search(r"\.(jpg|jpeg|png)$", m, re.I)]
                if not img_members:
                    continue
                chosen = random.sample(img_members, min(IMAGES_PER_ZIP, len(img_members)))

                if schema == "coco_ocr":
                    # 239 방식은 JSON 하나에 여러 이미지가 얽혀 있을 수 있어 라벨 zip 전체를 먼저 파싱
                    text_by_filename = {}
                    for jm in [m for m in tlzf.namelist() if m.lower().endswith(".json")]:
                        try:
                            text_by_filename.update(extract_coco_ocr_attr(read_json_from_zip(tlzf, jm)))
                        except Exception as e:
                            print(f"  라벨 파싱 실패({jm}): {e}")

                for img_member in chosen:
                    base = os.path.splitext(os.path.basename(img_member))[0]
                    ext = os.path.splitext(img_member)[1]
                    out_base = f"{name}_{base}"
                    img_bytes = tszf.read(img_member)

                    gt_text = None
                    if schema == "coco_ocr":
                        gt_text = text_by_filename.get(os.path.basename(img_member))
                    else:
                        json_member = None
                        for jm in tlzf.namelist():
                            if os.path.splitext(os.path.basename(jm))[0] == base and jm.lower().endswith(".json"):
                                json_member = jm
                                break
                        if json_member:
                            try:
                                jdata = read_json_from_zip(tlzf, json_member)
                                if schema == "bbox":
                                    gt_text = extract_bbox_style(jdata)
                                elif schema == "polygons":
                                    gt_text = extract_polygons_style(jdata)
                            except Exception as e:
                                print(f"  라벨 파싱 실패({json_member}): {e}")

                    with open(os.path.join(out_cat_dir, out_base + ext), "wb") as f:
                        f.write(img_bytes)
                    if gt_text:
                        with open(os.path.join(out_cat_dir, out_base + ".txt"), "w", encoding="utf-8") as f:
                            f.write(gt_text)
                        saved += 1
                    else:
                        print(f"  [주의] 정답 텍스트 없이 이미지만 저장: {out_base}")
        except zipfile.BadZipFile:
            print(f"  [오류] 손상된 zip(스킵): {ts_path}")
            continue

    print(f"[done] {name} -> {category}/  (정답 텍스트 확보 {saved}장)")
    return saved


def main():
    if not os.path.isdir(ROOT):
        print(f"'{ROOT}' 없음 — 경로를 확인하세요.")
        return

    datasets = [
        dict(name="023공공", category="manufacturing", schema="bbox",
             source_dir=os.path.join(ROOT, "023.OCR 데이터(공공)", "01-1.정식개방데이터", "Training", "01.원천데이터"),
             label_dir=os.path.join(ROOT, "023.OCR 데이터(공공)", "01-1.정식개방데이터", "Training", "02.라벨링데이터")),
        dict(name="025금융물류", category="retail", schema="bbox",
             source_dir=os.path.join(ROOT, "025.OCR 데이터(금융 및 물류)", "01-1.정식개방데이터", "Training", "01.원천데이터"),
             label_dir=os.path.join(ROOT, "025.OCR 데이터(금융 및 물류)", "01-1.정식개방데이터", "Training", "02.라벨링데이터")),
        dict(name="055금융업특화", category="fnb", schema="bbox",
             source_dir=os.path.join(ROOT, "055.금융업 특화 문서 OCR 데이터", "01.데이터", "1. Training", "원천데이터"),
             label_dir=os.path.join(ROOT, "055.금융업 특화 문서 OCR 데이터", "01.데이터", "1. Training", "라벨링데이터")),
        dict(name="056의약품화장품", category="fnb", schema="polygons",
             source_dir=os.path.join(ROOT, "056.의약품, 화장품 패키징 OCR 데이터", "01.데이터", "1. Training", "원천데이터"),
             label_dir=os.path.join(ROOT, "056.의약품, 화장품 패키징 OCR 데이터", "01.데이터", "1. Training", "라벨링데이터")),
        dict(name="239건축도면", category="manufacturing", schema="coco_ocr", ts_prefix_filter="TS_OCR",
             source_dir=os.path.join(ROOT, "239.건축 도면 데이터", "01-1.정식개방데이터", "Training", "01.원천데이터"),
             label_dir=os.path.join(ROOT, "239.건축 도면 데이터", "01-1.정식개방데이터", "Training", "02.라벨링데이터")),
    ]

    total = 0
    for ds in datasets:
        total += process_dataset(
            ds["name"], ds["source_dir"], ds["label_dir"], ds["category"],
            ts_prefix_filter=ds.get("ts_prefix_filter"), schema=ds["schema"],
        )

    print(f"\n총 {total}장(정답 텍스트 포함) 확보 -> {OUT_DIR}")
    print("다음 실행: python ingest_aihub_samples.py  (스윕 + 리포트 자동 생성)")


if __name__ == "__main__":
    main()
