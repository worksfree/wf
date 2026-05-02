# NaverBlogCommenter  |  WorksFree RPA v1.0

네이버 블로그 이웃 자동 **공감 + 댓글** RPA 도구

---

## 설치

```bash
pip install -r requirements.txt
```

Chrome이 설치되어 있어야 합니다.  
ChromeDriver는 `selenium >= 4.6` 에서 자동 관리됩니다.

---

## 실행

```bash
python naver_blog_commenter.py
```

---

## 크레딧 소비

| 작업            | 크레딧 |
|-----------------|--------|
| 👍 공감          | 1 / 건 |
| 💬 기본 댓글     | 1 / 건 |
| 🤖 AI 댓글 (Claude) | 3 / 건 |

---

## 데모 충전 코드 (테스트용)

| 코드      | 충전량 |
|-----------|--------|
| DEMO100   | 100    |
| DEMO300   | 300    |
| WF2024    | 50     |

> 실제 배포 시 `wf_license` 서버 검증 코드로 교체 필요

---

## wf_* 모듈 연동 포인트

- `wf_license` → 크레딧 충전 코드 서버 검증
- `wf_credit`  → 크레딧 잔액 동기화
- `wf_log`     → 실행 이력 원격 수집
- `wf_googlesheet` → 댓글 작성 이력 시트 기록

---

## 주의사항

- 네이버 서비스 약관에 따라 자동화 사용에 제한이 있을 수 있습니다.
- 딜레이를 충분히 설정(3초 이상 권장)하여 계정 제재를 최소화하세요.
- AI 댓글 사용 시 Claude API Key 필요 (claude.ai 또는 console.anthropic.com)
