# dwg-extract-pc — 로컬 DWG 표제란/BOM 추출 서버

`service/dwg-extract`가 쓰는 PC 로컬 서비스. AutoCAD DWG 파일을 이미지로
변환해 OCR로 다시 읽는 우회로 대신, DWG 안에 이미 벡터 텍스트로 들어있는
표제란(설계자/일자/승인 등)과 BOM(부품표)을 직접 파싱해서 뽑는다 —
Ollama/GPU는 전혀 쓰지 않는다(OCR과 완전히 별개 파이프라인).

핵심 로직과 실측 검증 근거는 `dwg_extract.py` 상단 주석 참고. 요약:
- DWG 파싱은 GNU LibreDWG(`bin/dwgread.exe`, GPL 완전 오픈소스)를 서브프로세스로 호출
- 표제란: 라벨 텍스트를 앵커로 삼아 가장 가까운(유클리드 거리) MTEXT를 값으로 채택
- BOM: MTEXT 자식이 가장 많은 블록(SolidWorks가 DWG로 내보낼 때 자동 생성하는
  `SW_TABLEANNOTATION_N` 등)을 찾아 행/열로 재구성
- 2026-07-25 실측 검증: 실제 도면 2건(단품 1건, 조립도 1건)에서 표제란 전체 필드 +
  BOM 24행 전부 원본과 정확히 일치 확인

## 설정 (최초 1회)

`bin/` 폴더에 LibreDWG 바이너리(`dwgread.exe` + 의존 DLL 4개)가 이미 포함돼 있어
추가 설치가 필요 없다 — 표준 라이브러리만 쓰므로 pip install도 불필요.

```powershell
cd D:\drive_files\10.worksfree\10.rpa\70.webs\synology-web\workers\dwg-extract-pc
python -m venv venv   # 다른 워커들과 실행 관례를 맞추기 위한 선택 사항
```

## 실행

```powershell
python dwg_extract_server.py
```

포트 8767에서 대기 — `http://localhost:8767/health`로 정상 기동 확인 가능.

## 인프라 연결 (사용자가 Cloudflare 대시보드에서 직접 설정 필요 — 아직 미완료)

`ocr-detect-pc`(`detect.worksfree.kr`)와 동일한 절차:

1. Cloudflare Tunnel(이 PC가 커넥터인 터널, 예: `lifeart_ai`) → Public Hostname 추가
   - Subdomain: `dwg-extract` (예: `dwg-extract.worksfree.kr`)
   - Service URL: `http://localhost:8767`
2. Zero Trust → Access → Applications → 위 호스트네임 앱 생성
   - 정책: 기존 `biz-rag-worker` Service Token 재사용(새 토큰 발급 불필요)
3. 워커(`workers/dwg-extract`) 시크릿 등록: `PC_EXTRACT_URL=https://dwg-extract.worksfree.kr`
   (`CF_ACCESS_CLIENT_ID`/`CF_ACCESS_CLIENT_SECRET`도 동일 Service Token 재사용)

## 되돌리기(기능 끄기)

이 서버를 그냥 끄면(또는 안 켜면) `service/dwg-extract` 페이지가 "오프라인" 상태로
표시될 뿐, 이 저장소의 다른 어떤 기능에도 영향이 없다 — 이 폴더와 `workers/dwg-extract`
워커, 허브 사이드바 노드를 삭제하면 완전히 원상복구된다.
