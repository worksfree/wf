"""
OCR 테스트용 실사진 코퍼스 수집 스크립트 (2026-07-24).

사용자가 "OCR 테스트용 이미지를 인터넷에서 300장 정도 수집해달라"고 요청했으나,
무작위 웹 스크래핑은 (1) 그런 범용 크롤러 도구가 없고 (2) 저작권 출처가 불분명해
사내 도구 테스트용으로도 권장되지 않는다. 대신 **라이선스가 명시된 공개 OCR
벤치마크/데이터셋에서 실제로 다운로드**하는 방식으로 대체했다:

- KORIE(Korean Retail Receipts Benchmark, Google Drive 공개, 승인 불필요) —
  detection test+val 세트에서 실제 영수증 전체 사진 약 286장
- HumynLabs/Korean_Receipts_Dataset (HuggingFace, CC-BY-4.0) — 영수증 20장
- HumynLabs/Korean_Handwritten_Notes_Dataset (HuggingFace, CC-BY-4.0) — 손글씨 9장
- Kratos-AI/Korean-Documents-Dataset (HuggingFace) — 일반 문서 3장

총 298장, 660MB — 용량이 커서 git에는 커밋하지 않는다(.gitignore 처리).
이 스크립트를 재실행하면 test_corpus/ 아래에 동일하게 재현된다.

사용법:
    pip install gdown huggingface_hub
    python collect_test_corpus.py
"""
import os, glob, shutil, subprocess, sys

BASE = os.path.dirname(__file__)
CORPUS = os.path.join(BASE, "test_corpus")
WORK = os.path.join(BASE, "_corpus_download_tmp")

# KORIE(github.com/MahmoudSalah/KORIE) README의 Google Drive 파일ID — detection(전체 사진) 세트
KORIE_FILES = {
    "detection_test": "1UJZIcTX38FnMa8PZHYj--5OJ8-deSMRI",
    "detection_val":  "15wXqZUzWaYEJu-rWZwCPuMvHFMZgWQOD",
}

HF_DATASETS = {
    "kr_receipts_hf": "HumynLabs/Korean_Receipts_Dataset",       # -> receipt/
    "kr_handwritten": "HumynLabs/Korean_Handwritten_Notes_Dataset",  # -> handwriting/
    "kr_documents":   "Kratos-AI/Korean-Documents-Dataset",      # -> document/
}
HF_TARGET_CATEGORY = {
    "kr_receipts_hf": "receipt", "kr_handwritten": "handwriting", "kr_documents": "document",
}


def download_korie():
    import gdown
    for name, file_id in KORIE_FILES.items():
        zip_path = os.path.join(WORK, f"{name}.zip")
        extract_dir = os.path.join(WORK, name)
        if os.path.isdir(extract_dir):
            print(f"[skip] {name} already extracted")
            continue
        print(f"[download] KORIE {name} ...")
        gdown.download(f"https://drive.google.com/uc?id={file_id}", zip_path, quiet=False)
        shutil.unpack_archive(zip_path, extract_dir)


def download_hf():
    from huggingface_hub import snapshot_download
    for name, repo in HF_DATASETS.items():
        dest = os.path.join(WORK, "hf_" + name)
        if os.path.isdir(dest):
            print(f"[skip] {name} already downloaded")
            continue
        print(f"[download] HuggingFace {repo} ...")
        snapshot_download(repo_id=repo, repo_type="dataset", local_dir=dest,
                           allow_patterns=["*.JPEG", "*.jpg", "*.jpeg", "*.png"])


def assemble():
    for cat in ("receipt", "handwriting", "document"):
        os.makedirs(os.path.join(CORPUS, cat), exist_ok=True)

    # KORIE detection test+val -> receipt/ (전체 영수증 사진 — bbox 좌표 라벨은 사용하지 않고 이미지만)
    idx = 1
    patterns = [
        os.path.join(WORK, "detection_test", "**", "images", "*.png"),
        os.path.join(WORK, "detection_val", "**", "images", "*.png"),
    ]
    for pat in patterns:
        for f in sorted(glob.glob(pat, recursive=True)):
            shutil.copy(f, os.path.join(CORPUS, "receipt", f"korie_{idx:03d}.png"))
            idx += 1
    print(f"receipt(KORIE): {idx-1}장")

    # HuggingFace 보충 세트
    for name, cat in HF_TARGET_CATEGORY.items():
        src_dir = os.path.join(WORK, "hf_" + name)
        files = sorted(glob.glob(os.path.join(src_dir, "*.JPEG")) + glob.glob(os.path.join(src_dir, "*.jpg")))
        for i, f in enumerate(files, 1):
            shutil.copy(f, os.path.join(CORPUS, cat, f"hf_{i:03d}.jpg"))
        print(f"{cat}(HF {name}): {len(files)}장")

    total = sum(len(glob.glob(os.path.join(CORPUS, c, "*"))) for c in ("receipt", "handwriting", "document"))
    print(f"\n총 {total}장 -> {CORPUS}")


if __name__ == "__main__":
    os.makedirs(WORK, exist_ok=True)
    download_korie()
    download_hf()
    assemble()
