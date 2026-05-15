#!/bin/bash
# ════════════════════════════════════════════════════════
#  setup-auth.sh
#  GFC 전용 Basic Auth 비밀번호 파일 생성 스크립트
#  시놀로지 NAS SSH에서 실행
#
#  실행 방법:
#    ssh admin@NAS_IP
#    cd /volume1/web/portal
#    chmod +x setup-auth.sh
#    sudo ./setup-auth.sh
# ════════════════════════════════════════════════════════

HTPASSWD_FILE="/volume1/web/portal/.htpasswd-gfc"

echo "================================================"
echo "  WorksFree Hub — GFC 인증 파일 설정"
echo "================================================"
echo ""

# htpasswd 명령어 확인 (없으면 openssl로 대체)
if command -v htpasswd &>/dev/null; then
    echo "▶ htpasswd 명령어를 사용합니다."
    echo ""
    echo "GFC 전용 ID를 입력하세요 (예: gfc):"
    read -r USERNAME
    echo ""
    # -c: 새 파일 생성, -B: bcrypt 암호화
    htpasswd -cB "$HTPASSWD_FILE" "$USERNAME"

else
    echo "▶ openssl로 비밀번호 파일을 생성합니다."
    echo ""
    echo "GFC 전용 ID를 입력하세요 (예: gfc):"
    read -r USERNAME
    echo "GFC 전용 비밀번호를 입력하세요:"
    read -rs PASSWORD
    echo ""

    # openssl로 SHA-1 해시 생성 (Apache 호환)
    HASH=$(openssl passwd -apr1 "$PASSWORD")
    echo "${USERNAME}:${HASH}" > "$HTPASSWD_FILE"
fi

# 파일 권한 설정 (Nginx만 읽을 수 있게)
chmod 640 "$HTPASSWD_FILE"
chown root:http "$HTPASSWD_FILE" 2>/dev/null || chmod 644 "$HTPASSWD_FILE"

echo ""
echo "✅ 인증 파일 생성 완료: $HTPASSWD_FILE"
echo ""
echo "다음 단계:"
echo "  1. DSM → 웹 스테이션 → Nginx 설정에 nginx-wfhub.conf 적용"
echo "  2. Nginx 재시작: sudo nginx -s reload"
echo "  3. /gfc/ 접속 시 ID/PW 팝업 확인"
echo ""
echo "GFC 동료 공유 URL:"
echo "  https://your-domain/  (일반)"
echo "  https://your-domain/?role=gfc-2025-samsung-wf  (GFC 전용)"
echo "================================================"
