# ocr-detect-pc — 로컬 텍스트 위치 감지 서버

`service/ocr`의 "정밀 교정(베타)" 모드가 쓰는 PC 로컬 서비스. EasyOCR로 이미지에서
텍스트 **위치(바운딩 박스)만** 찾아 반환한다 — 실제 텍스트 인식은 하지 않는다.
인식은 이미 검증된 올mOCR-2(Ollama, `workers/ocr-service`)가 박스 영역을 잘라
다시 담당한다. 자세한 설계 배경은 `detect_server.py` 상단 주석 참고.

## 설정 (최초 1회)

```powershell
cd D:\drive_files\10.worksfree\10.rpa\70.webs\synology-web\workers\ocr-detect-pc
python -m venv venv
venv\Scripts\pip install -r requirements.txt
```

## 실행

```powershell
venv\Scripts\python detect_server.py
```

첫 실행 시 EasyOCR 모델 파일을 자동 다운로드한다(수 분 소요, 이후엔 캐시 재사용).
포트 8766에서 대기 — `http://localhost:8766/health`로 정상 기동 확인 가능.

## 인프라 연결 상태 (2026-07-24 설정 완료)

- Cloudflare Tunnel Public Hostname: `detect.worksfree.kr` → `http://localhost:8766`
- Zero Trust Access Application: `detect.worksfree.kr`, 정책 `service-token-only`
  (기존 `pc-ai.worksfree.kr`용 Service Token `biz-rag-worker` 재사용 — 새 토큰 발급 안 함)
- 워커(`workers/ocr-service`) 시크릿: `PC_DETECT_URL=https://detect.worksfree.kr`
  (CF_ACCESS_CLIENT_ID/SECRET은 기존 것 재사용, 새로 등록할 필요 없음)

## 상시화 (선택)

지금은 테스트 목적이라 수동 실행 기준으로 되어 있다. 상시 서비스로 돌리려면
`10.rpa/70.webs/site-rag/register_host_rewrite_task.ps1`과 같은 패턴(.vbs 래퍼 +
`Register-ScheduledTask`, `AtLogOn` 트리거)으로 Windows 작업 스케줄러에 등록하면 된다.

## 되돌리기(기능 끄기)

이 서버를 그냥 끄면(또는 안 켜면) `service/ocr`의 "정밀 교정" 토글을 선택해도
"오프라인" 상태로 표시되고, 기존 기본 OCR 흐름은 전혀 영향받지 않는다 — 이
폴더와 워커의 `/detect` 라우트, 클라이언트 토글 UI를 삭제하면 완전히 원상복구된다.
