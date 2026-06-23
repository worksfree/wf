# CLAUDE.md — 시놀로지NAS 풀스택가이드 (출판용)

이 폴더는 시놀로지 NAS 구축 가이드 시리즈의 출판용 원본 폴더다.

## 폴더 역할

출판·배포용 최종 원고를 보관한다. 개발 작업 폴더(`10.rpa/70.webs/synology-web/`)와 구축가이드 문서들이 하드링크로 연결되어 있으며 **이 폴더가 canonical(기준) 소스**다.

## 구축가이드 하드링크 현황

| 파일 | 역할 | 출판용 경로 (기준) | 개발용 경로 (하드링크) |
|------|------|------------------|----------------------|
| NAS웹서비스_구축가이드.md | 웹 서비스 가이드 **최종본** | 이 폴더 | `10.rpa/70.webs/synology-web/` |
| NAS메일서버_구축가이드.md | 메일 서버 가이드 최종본 | 이 폴더 | `10.rpa/70.webs/synology-web/` |

**하드링크 방향**: 출판용이 원본, 개발용이 링크.  
**중요**: 하드링크는 동일한 inode를 공유하므로 어느 경로에서 편집해도 즉시 양쪽에 반영된다. 단, 관행상 이 출판용 폴더에서 먼저 편집한다.

## 편집 원칙

1. **구축가이드 수정** → 이 폴더(`30.publish/시놀로지NAS_풀스택가이드/`)에서 편집
2. 저장하면 개발용 폴더에도 자동 반영됨 (하드링크이므로 별도 동기화 불필요)
3. 신규 구축가이드 추가 시 → 이 폴더에 파일 생성 후 개발용 폴더에 하드링크 연결

## PDF → JPG 추출 시 우측 세로선 아티팩트 (필독)

### 문제
Edge headless로 HTML → PDF 변환 후 PyMuPDF로 JPG 추출하면
**우측 끝에 1~10px 폭의 흰색·청색 세로선**이 항상 생긴다.
커버처럼 어두운 배경에서 특히 두드러진다.

### 원인
Edge headless 페이지 경계 렌더링 한계.
배경 이미지·색상이 우측 끝까지 완벽하게 채워지지 않아 발생.

### 대응 1 — HTML (커버 파일)
`@media print`에서 반드시 아래 두 항목을 유지한다.
```css
html { overflow: hidden !important; }
.cover { width: 100% !important; }   /* 148.5mm 절대금지 — 페이지 폭 불일치 야기 */
```

### 대응 2 — Python (PDF 추출 스크립트 공통)
PDF 페이지를 JPG로 추출할 때 **반드시** 아래 함수를 적용한다.
빠뜨리면 우측 세로선이 남는다.

```python
def fix_right_edge(img, fix_px=12):
    """Edge headless 우측 아티팩트 제거 — PDF 추출 후 항상 호출"""
    w, h = img.size
    pixels = img.load()
    sample_x = w - fix_px - 10   # 아티팩트 영역 밖 기준점
    for y in range(h):
        ref = pixels[sample_x, y]
        for x in range(w - fix_px, w):
            pixels[x, y] = ref
    return img
```

적용 대상: `make_cover_jpg_v3.py`, `make_kmong_preview.py` 및 이후 추가될 모든 PDF→JPG 변환 스크립트.

---

## 하드링크 생성 명령 (참고)

```powershell
# 신규 가이드 하드링크 추가 시 (출판용 파일이 이미 있을 때)
New-Item -ItemType HardLink `
  -Path "D:\drive_files\10.worksfree\10.rpa\70.webs\synology-web\파일명.md" `
  -Target "D:\drive_files\10.worksfree\30.publish\시놀로지NAS_풀스택가이드\파일명.md"

# 하드링크 확인
fsutil hardlink list "D:\drive_files\10.worksfree\30.publish\시놀로지NAS_풀스택가이드\파일명.md"
```
