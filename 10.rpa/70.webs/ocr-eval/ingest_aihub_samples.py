"""
AI-Hub에서 수동으로 승인받아 내려받은 업종별(유통/요식/제조) 표본을
`aihub_samples/{retail,fnb,manufacturing}/`에 넣어두면, 이 스크립트가
scratchpad/ocr_lab/sweep_contrast_sharpen.py와 동일한 방식(coarse-to-fine
그리드 서치)으로 콘트라스트/샤프니스 최적값을 실측하고 리포트를 만든다.

사람이 해야 하는 부분(회원가입·본인인증·목적 심사 신청)은
AIHub_샘플_다운로드_가이드.md 참고. 그 승인이 끝나고 파일을 폴더에
떨어뜨리기만 하면 이 스크립트가 전처리 파라미터 최적화·정확도 채점·
리포트 생성까지 전부 자동으로 끝낸다.

사용법:
    python ingest_aihub_samples.py
"""
import glob, json, os, sys, time

# stdout이 파일로 리다이렉트되면 Windows에서 cp949로 인코딩을 시도해 em-dash(—) 등에서
# UnicodeEncodeError로 죽는다(2026-07-23 야간 sweep_contrast_sharpen.py 실행에서 실제로
# 발생 — 1단계 294건 완료 후 2단계 진입 로그에서 크래시). UTF-8을 명시적으로 강제한다.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE = os.path.dirname(__file__)
sys.path.insert(0, BASE)
import ocr_eval_lib as lib

SAMPLES_DIR = os.path.join(BASE, "aihub_samples")
RESULTS_PATH = os.path.join(BASE, "aihub_sweep_results.jsonl")
REPORT_PATH = os.path.join(BASE, "aihub_sweep_report.md")
LOG_PATH = os.path.join(BASE, "aihub_sweep_progress.log")

IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp")
MAX_IMAGES_PER_CATEGORY = 6  # 그리드 서치 시간 제한 — 카테고리당 표본 수가 많아도 이 개수만 사용

# 로컬 6종 표본 스윕(scratchpad/ocr_lab)에서 쓴 것과 동일한 그리드 — 결과를 직접 비교 가능하도록 통일
STAGE1_CONTRAST = [-20, -10, 0, 10, 20, 35, 50]
STAGE1_SHARPEN = [0, 15, 30, 45, 60, 80, 100]


def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def _find_text_in_json(obj, depth=0):
    """AI-Hub 어노테이션 JSON 스키마가 데이터셋마다 달라 완벽할 수 없는 best-effort 추출.
    흔한 키(text/value/content 등)를 재귀 탐색해 순서대로 이어붙인다."""
    if depth > 6:
        return []
    found = []
    text_keys = {"text", "value", "content", "raw_text", "gt_text", "transcription", "annotation", "label"}
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.lower() in text_keys and isinstance(v, str) and v.strip():
                found.append(v.strip())
            elif isinstance(v, (dict, list)):
                found.extend(_find_text_in_json(v, depth + 1))
    elif isinstance(obj, list):
        for item in obj:
            found.extend(_find_text_in_json(item, depth + 1))
    return found


def load_ground_truth(image_path):
    """같은 이름의 .txt가 있으면 그대로 사용, 없으면 같은 이름의 .json에서 best-effort 추출."""
    base_noext = os.path.splitext(image_path)[0]
    txt_path = base_noext + ".txt"
    if os.path.exists(txt_path):
        with open(txt_path, "r", encoding="utf-8") as f:
            return f.read(), "txt"
    json_path = base_noext + ".json"
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            texts = _find_text_in_json(data)
            if texts:
                return "\n".join(texts), "json(best-effort)"
        except Exception as e:
            log(f"  JSON 어노테이션 파싱 실패: {json_path} — {e}")
    return None, None


def discover_categories():
    if not os.path.isdir(SAMPLES_DIR):
        return {}
    categories = {}
    for cat in sorted(os.listdir(SAMPLES_DIR)):
        cat_dir = os.path.join(SAMPLES_DIR, cat)
        if not os.path.isdir(cat_dir):
            continue
        images = []
        for ext in IMAGE_EXTS:
            images.extend(glob.glob(os.path.join(cat_dir, f"*{ext}")))
            images.extend(glob.glob(os.path.join(cat_dir, f"*{ext.upper()}")))
        images = sorted(set(images))[:MAX_IMAGES_PER_CATEGORY]
        if images:
            categories[cat] = images
    return categories


def run_one(image_path, category, gt_text, contrast_pct, sharpen_pct, stage, img_cache):
    img = img_cache[image_path]
    last_err = None
    for attempt in range(2):
        try:
            cleaned, elapsed = lib.run_ocr_with_settings(img, contrast_pct, sharpen_pct)
            c = lib.cer(gt_text, cleaned) if gt_text else None
            result = {
                "stage": stage, "image": os.path.basename(image_path), "category": category,
                "contrast_pct": contrast_pct, "sharpen_pct": sharpen_pct,
                "cer": round(c, 4) if c is not None else None,
                "elapsed_sec": round(elapsed, 1), "out_chars": len(cleaned),
                "has_gt": gt_text is not None,
            }
            with open(RESULTS_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(result, ensure_ascii=False) + "\n")
            return result
        except Exception as e:
            last_err = e
            time.sleep(2)
    log(f"  FAILED after retry: {os.path.basename(image_path)} c={contrast_pct} s={sharpen_pct} — {last_err}")
    result = {"stage": stage, "image": os.path.basename(image_path), "category": category,
              "contrast_pct": contrast_pct, "sharpen_pct": sharpen_pct, "cer": None, "error": str(last_err)}
    with open(RESULTS_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(result, ensure_ascii=False) + "\n")
    return result


def main():
    categories = discover_categories()
    if not categories:
        print(f"'{SAMPLES_DIR}' 아래에 retail/fnb/manufacturing 같은 하위 폴더에 이미지가 있어야 합니다.")
        print("AIHub_샘플_다운로드_가이드.md를 먼저 진행하세요.")
        return

    open(RESULTS_PATH, "w").close()
    open(LOG_PATH, "w").close()
    log(f"=== AI-Hub 표본 스윕 시작 — 카테고리: {list(categories.keys())} ===")

    img_cache, gt_cache, gt_source_cache = {}, {}, {}
    total_calls = 0
    for cat, images in categories.items():
        n_with_gt = 0
        for img_path in images:
            img_cache[img_path] = lib.cv_read(img_path)
            gt, src = load_ground_truth(img_path)
            gt_cache[img_path] = gt
            gt_source_cache[img_path] = src
            if gt:
                n_with_gt += 1
        log(f"  카테고리 '{cat}': 이미지 {len(images)}개 (정답 텍스트 확보 {n_with_gt}개)")
        total_calls += len(images) * len(STAGE1_CONTRAST) * len(STAGE1_SHARPEN)

    log(f"1단계(coarse) 예상 호출 수: {total_calls}")
    done, t_start = 0, time.time()
    for cat, images in categories.items():
        for c in STAGE1_CONTRAST:
            for s in STAGE1_SHARPEN:
                for img_path in images:
                    run_one(img_path, cat, gt_cache[img_path], c, s, "coarse", img_cache)
                    done += 1
                    if done % 20 == 0:
                        elapsed_min = (time.time() - t_start) / 60
                        rate = done / elapsed_min if elapsed_min > 0 else 0
                        eta_min = (total_calls - done) / rate if rate > 0 else 0
                        log(f"  진행 {done}/{total_calls} ({elapsed_min:.1f}분 경과, 예상 잔여 {eta_min:.1f}분)")
    log(f"1단계 완료 ({(time.time()-t_start)/60:.1f}분)")

    all_rows = [json.loads(l) for l in open(RESULTS_PATH, encoding="utf-8") if l.strip()]
    best_per_cat = {}
    for cat in categories:
        rows = [r for r in all_rows if r["category"] == cat and r["cer"] is not None]
        if not rows:
            log(f"  카테고리 '{cat}': 정답 텍스트가 없어 CER 채점 불가 — 최적값 산출 스킵(출력 길이 등 보조지표만 참고 가능)")
            continue
        agg = {}
        for r in rows:
            agg.setdefault((r["contrast_pct"], r["sharpen_pct"]), []).append(r["cer"])
        means = {k: sum(v) / len(v) for k, v in agg.items()}
        best_key = min(means, key=means.get)
        best_per_cat[cat] = {"contrast_pct": best_key[0], "sharpen_pct": best_key[1], "mean_cer": means[best_key]}
        log(f"  카테고리 '{cat}' 최적: contrast={best_key[0]} sharpen={best_key[1]} (평균 CER {means[best_key]:.4f})")

    # 2단계(fine): 정답이 있는 카테고리만 정밀 탐색
    stage2_plan = []
    total2 = 0
    for cat, b in best_per_cat.items():
        c_range = sorted(set(max(-20, min(50, b["contrast_pct"] + d)) for d in [-10, -5, 0, 5, 10]))
        s_range = sorted(set(max(0, min(100, b["sharpen_pct"] + d)) for d in [-15, -7, 0, 7, 15]))
        stage2_plan.append((cat, c_range, s_range, categories[cat]))
        total2 += len(c_range) * len(s_range) * len(categories[cat])

    if stage2_plan:
        log(f"2단계(fine) 예상 호출 수: {total2}")
        done2, t2 = 0, time.time()
        for cat, c_range, s_range, images in stage2_plan:
            for c in c_range:
                for s in s_range:
                    for img_path in images:
                        run_one(img_path, cat, gt_cache[img_path], c, s, "fine", img_cache)
                        done2 += 1
            log(f"  2단계 카테고리 '{cat}' 완료 ({done2}/{total2})")
        log(f"2단계 완료 ({(time.time()-t2)/60:.1f}분)")

    generate_report(categories, best_per_cat, gt_source_cache)
    log(f"=== 완료 — 리포트: {REPORT_PATH} ===")


def generate_report(categories, stage1_best, gt_source_cache):
    all_rows = [json.loads(l) for l in open(RESULTS_PATH, encoding="utf-8") if l.strip()]
    lines = ["# AI-Hub 업종별 표본 — 콘트라스트 x 샤프니스 스윕 결과\n",
             f"생성 시각: {time.strftime('%Y-%m-%d %H:%M:%S')}\n",
             f"모델: `{lib.OCR_MODEL}` · 총 호출: {len(all_rows)}건\n"]

    lines.append("## 카테고리별 최종 추천 설정 (2단계 정밀 탐색 기준)\n")
    lines.append("| 카테고리 | 표본 수 | 추천 콘트라스트 | 추천 샤프니스 | 평균 CER |")
    lines.append("|---|---|---|---|---|")
    for cat in categories:
        fine_rows = [r for r in all_rows if r["stage"] == "fine" and r["category"] == cat and r["cer"] is not None]
        if not fine_rows:
            lines.append(f"| {cat} | {len(categories[cat])} | 정답 텍스트 없음(채점 불가) | - | - |")
            continue
        agg = {}
        for r in fine_rows:
            agg.setdefault((r["contrast_pct"], r["sharpen_pct"]), []).append(r["cer"])
        means = {k: sum(v) / len(v) for k, v in agg.items()}
        best_key = min(means, key=means.get)
        lines.append(f"| {cat} | {len(categories[cat])} | {best_key[0]:+d}% | {best_key[1]}% | {means[best_key]:.4f} |")

    lines.append("\n## 정답 텍스트 출처 (품질 참고용 — json(best-effort)는 스키마 추정이라 부정확할 수 있음)\n")
    lines.append("| 이미지 | 출처 |")
    lines.append("|---|---|")
    for img_path, src in gt_source_cache.items():
        lines.append(f"| {os.path.basename(img_path)} | {src or '없음(CER 채점 제외)'} |")

    fail_count = sum(1 for r in all_rows if r.get("cer") is None and r.get("has_gt"))
    lines.append(f"\n## 실패한 호출: {fail_count}건\n")
    lines.append("\n## 참고\n")
    lines.append("- 로컬 6종 표본(손글씨·긴문서·영수증) 스윕 결과(`scratchpad/ocr_lab/sweep_report.md`)와 그리드가 동일하므로 카테고리 간 직접 비교 가능.")
    lines.append(f"- 카테고리당 최대 {MAX_IMAGES_PER_CATEGORY}개 표본만 사용(전체 그리드 서치 시간 제한) — 표본을 더 반영하려면 이 스크립트의 `MAX_IMAGES_PER_CATEGORY`를 조정 후 재실행.")

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
