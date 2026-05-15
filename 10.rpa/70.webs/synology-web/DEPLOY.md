# WorksFree Hub — 시놀로지 NAS 배포 가이드

> 버전: 0.7.0.1 · 작성일: 2025 · 대상: DS923+ 이상 (Web Station + Docker 지원 모델)

---

## 📁 최종 파일 구조

```
wfhub/                          ← 배포 루트
├── index.html                  ← 허브 (트리 네비 + 역할 라우터)
├── nginx-wfhub.conf            ← Nginx 설정 (Basic Auth 포함)
├── setup-auth.sh               ← GFC 인증 파일 생성 스크립트
│
├── gfc/
│   └── index.html              ← GFC 법인 컨설팅 진단 (🔒 GFC 전용)
│
├── qr/
│   └── index.html              ← QR 코드 생성기 (공용)
│
└── esg/
    └── index.html              ← ESG 자가진단 (공용, 준비중)
```

**새 콘텐츠 추가 시:** 폴더 만들고 `index.html` 넣은 후 허브 `index.html`의 `TREE` 배열에 한 줄 추가.

---

## 🔐 접근 제어 구조

| 대상 | 공유 URL | GFC 메뉴 | /gfc/ 직접 접근 |
|---|---|---|---|
| GFC 동료 | `/?role=gfc-2025-samsung-wf` | ✅ 표시 | 🔒 ID/PW 필요 |
| 경영지도사 | `/` | ❌ 숨김 | 🔒 ID/PW 필요 |

> **토큰 변경:** `index.html` 상단 `const GFC_TOKEN = '...'` 값만 수정.
> **Basic Auth 비밀번호 변경:** `setup-auth.sh` 재실행.

---

## 🚀 배포 절차

### STEP 1 — 파일 업로드

**방법 A: File Station (GUI)**
```
DSM → File Station → /volume1/web/ 열기
→ 새 폴더 [wfhub] 생성
→ 로컬 PC의 wfhub/ 폴더 전체 드래그앤드롭 업로드
```

**방법 B: SCP 명령어 (터미널)**
```bash
# PC 터미널에서 실행
scp -r ./wfhub admin@192.168.x.x:/volume1/web/
```

---

### STEP 2 — Web Station 설정

```
DSM → Web Station 열기
→ [웹 서비스 포털] 탭
→ [생성] 클릭
→ 다음과 같이 설정:

  서비스 유형:   정적 웹 사이트
  포털 유형:     이름 기반
  호스트 이름:   hub.worksfree.co.kr  (본인 도메인)
  포트:          80 / 443
  문서 루트:     /volume1/web/wfhub
  HTTP 백엔드:   Nginx
```

---

### STEP 3 — SSL 인증서 발급 (HTTPS)

```
DSM → 제어판 → 보안 → 인증서 탭
→ [추가] → "Let's Encrypt에서 인증서 받기"
→ 도메인: hub.worksfree.co.kr
→ 이메일: 본인 이메일
→ [완료]

※ 자동 갱신되므로 이후 신경 안 써도 됩니다.
```

---

### STEP 4 — GFC Basic Auth 설정

**4-1. SSH 접속**
```bash
ssh admin@192.168.x.x
# 또는 DSM → 제어판 → 터미널 및 SNMP → SSH 서비스 활성화 후 접속
```

**4-2. 인증 파일 생성 스크립트 실행**
```bash
cd /volume1/web/wfhub
chmod +x setup-auth.sh
sudo ./setup-auth.sh

# 프롬프트 예시:
# GFC 전용 ID를 입력하세요: gfc
# New password: (GFC 팀에게만 알려줄 비밀번호)
# Re-type new password: (재입력)
# ✅ 인증 파일 생성 완료
```

**4-3. 생성된 파일 확인**
```bash
cat /volume1/web/wfhub/.htpasswd-gfc
# gfc:$apr1$xxxx... 형태면 정상
```

---

### STEP 5 — Nginx 설정 적용

**방법 A: DSM 리버스 프록시 GUI**
```
DSM → 로그인 포털 → 고급 탭 → 리버스 프록시
→ [생성]

  이름:          wfhub-gfc-auth
  소스 프로토콜: HTTPS
  소스 호스트:   hub.worksfree.co.kr
  소스 포트:     443
  소스 경로:     /gfc/

  대상 프로토콜: HTTP
  대상 호스트:   localhost
  대상 포트:     80
  대상 경로:     /gfc/

→ [사용자 지정 헤더] 탭
→ 헤더 추가: Authorization  (Basic Auth 전달용)
```

**방법 B: Nginx 직접 설정 (권장)**
```bash
# 설정 파일 복사
sudo cp /volume1/web/wfhub/nginx-wfhub.conf \
        /etc/nginx/conf.d/wfhub.conf

# 도메인 수정 (nano 또는 vi)
sudo vi /etc/nginx/conf.d/wfhub.conf
# server_name 을 본인 도메인으로 변경

# 문법 검사
sudo nginx -t

# 적용
sudo nginx -s reload
```

---

### STEP 6 — 공유기 포트포워딩

```
공유기 관리 페이지 (보통 192.168.1.1)
→ 포트포워딩 메뉴

추가 규칙 1:
  외부 포트: 80  →  내부 IP: NAS IP  →  내부 포트: 80

추가 규칙 2:
  외부 포트: 443 →  내부 IP: NAS IP  →  내부 포트: 443
```

---

### STEP 7 — 동작 확인

```
✅ 체크리스트

□ https://hub.worksfree.co.kr/          → 허브 홈 화면 (경영지도사용)
□ https://hub.worksfree.co.kr/?role=gfc-2025-samsung-wf
                                         → GFC 메뉴 포함 허브
□ https://hub.worksfree.co.kr/qr/       → QR 생성기 (인증 없이 접근)
□ https://hub.worksfree.co.kr/gfc/      → 브라우저 ID/PW 팝업 ← 핵심
□ 잘못된 토큰으로 GFC 메뉴 클릭 시      → 빨간 접근 거부 모달
```

---

## 📋 공유 URL 정리

```
그룹          공유 URL
──────────    ─────────────────────────────────────────────────
GFC 동료      https://hub.worksfree.co.kr/?role=gfc-2025-samsung-wf
              + 별도로 Basic Auth ID/PW 안내

경영지도사    https://hub.worksfree.co.kr/
              (토큰 없음, GFC 메뉴 자동 숨김)
```

---

## 🔧 운영 중 자주 쓰는 작업

### 새 콘텐츠 추가
```
1. /volume1/web/wfhub/새폴더/ 생성
2. index.html 업로드
3. 허브 index.html 의 TREE 배열에 한 줄 추가
4. 저장 — 즉시 반영 (서버 재시작 불필요)
```

### GFC 비밀번호 변경
```bash
ssh admin@NAS_IP
cd /volume1/web/wfhub
sudo ./setup-auth.sh     # 재실행하면 덮어씌워짐
```

### GFC 토큰 변경
```
허브 index.html 열기
const GFC_TOKEN = 'gfc-2025-samsung-wf';  ← 이 값 수정
저장 후 새 URL을 GFC 동료에게 재공유
```

### Nginx 재시작
```bash
sudo nginx -s reload
```

---

## ⚠️ 주의사항

1. **`.htpasswd-gfc` 파일은 웹 루트 밖에 두는 것이 이상적.**
   현재 `/volume1/web/wfhub/.htpasswd-gfc` 위치는 Nginx 설정에서
   해당 경로 직접 접근을 막아두었으므로 실용상 문제없음.

2. **URL 토큰은 완전한 보안이 아님.**
   토큰이 유출되면 GFC 메뉴가 보임. `/gfc/` 직접 접근은
   Basic Auth가 막아주는 이중 구조로 운영할 것.

3. **DDNS 사용 시** 시놀로지 DDNS (synology.me 도메인)도 동일하게 적용 가능.
   Let's Encrypt 인증서는 DDNS 도메인도 지원.

4. **2단계 업그레이드 시** (Supabase 인증 도입)
   각 콘텐츠 `index.html`은 그대로 재사용.
   허브 `index.html`의 역할 판별 로직만 교체하면 됨.

---

*WorksFree Hub v0.7.0.1*
