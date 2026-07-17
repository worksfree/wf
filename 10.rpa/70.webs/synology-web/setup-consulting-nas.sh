#!/bin/bash
# ══════════════════════════════════════════════════════════════
#  setup-consulting-nas.sh
#  NAS에서 1회 실행 — consulting 서브도메인 심볼릭 링크 구성
#
#  사전 조건: portal 배포가 완료된 상태여야 함
#             (deploy.ps1 → [3] portal 선택 후 실행)
#
#  NAS SSH 접속 후 실행:
#    ssh admin@<NAS-IP>
#    bash /volume1/web/setup-consulting-nas.sh
#  또는 로컬에서:
#    ssh admin@<NAS-IP> 'bash -s' < setup-consulting-nas.sh
# ══════════════════════════════════════════════════════════════

PORTAL=/volume1/web/portal
CONS=/volume1/web/consulting

echo "======================================================"
echo " WorksFree Consulting — NAS 심볼릭 링크 초기 설정"
echo "======================================================"
echo ""

# ── 1. portal 배포 존재 확인 ──────────────────────────────
if [ ! -d "$PORTAL/consulting" ]; then
  echo "[!] $PORTAL/consulting 디렉토리가 없습니다."
  echo "    deploy.ps1 → [3] portal 배포를 먼저 실행하세요."
  exit 1
fi
echo "[OK] portal 배포 확인됨: $PORTAL/consulting"
echo ""

# ── 2. consulting 루트 디렉토리 생성 ──────────────────────
mkdir -p "$CONS"
echo "[1] 루트 디렉토리: $CONS"

# ── 3. 심볼릭 링크 생성 (-sfn: 기존 링크 교체 허용) ───────
# 대시보드 index.html
ln -sfn "$PORTAL/consulting/index.html"              "$CONS/index.html"
echo "    index.html → $PORTAL/consulting/index.html"

# ESG 자가진단
ln -sfn "$PORTAL/consulting/esg"                     "$CONS/esg"
echo "    esg/       → $PORTAL/consulting/esg"

# 기업공시 조회 (DART)
ln -sfn "$PORTAL/consulting/dart"                    "$CONS/dart"
echo "    dart/      → $PORTAL/consulting/dart"

# 타코 매니저 (v1·v2·v3 포함)
ln -sfn "$PORTAL/consulting/tacomanager"             "$CONS/tacomanager"
echo "    tacomanager/ → $PORTAL/consulting/tacomanager"

# 블로그 자동화 (별도 경로)
ln -sfn "$PORTAL/app-store/web/naver-blog-commenter" "$CONS/blog"
echo "    blog/      → $PORTAL/app-store/web/naver-blog-commenter"

echo ""
echo "[2] 생성된 링크 목록:"
ls -la "$CONS/"

# ── 4. 링크 검증 ──────────────────────────────────────────
echo ""
echo "======================================================"
echo " 링크 검증"
echo "======================================================"
FAIL=0
for target in index.html esg dart tacomanager blog; do
  src="$CONS/$target"
  if [ -e "$src" ]; then
    echo "  ✓ $target"
  else
    echo "  ✗ $target — 대상 없음 (링크는 있지만 portal 경로에 파일 부재)"
    FAIL=1
  fi
done

echo ""
if [ $FAIL -eq 0 ]; then
  echo "[완료] 모든 링크가 정상입니다."
  echo ""
  echo "다음 단계:"
  echo "  1. nginx-consulting.conf → DSM 웹 스테이션 적용"
  echo "  2. Cloudflare Tunnel → consulting.worksfree.kr 퍼블릭 호스트네임 추가"
  echo "  3. 이후 portal 배포만 해도 consulting 자동 최신화"
else
  echo "[주의] 일부 링크 대상이 없습니다. portal 배포 후 이 스크립트를 재실행하세요."
fi
