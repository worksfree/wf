# 사용자 매뉴얼 제작 가이드

## 📋 작업 순서

### 1단계: 이미지 폴더 생성
```powershell
New-Item -ItemType Directory -Force -Path "D:\drive_files\10.worksfree\10.rpa\docs\images"
```

### 2단계: 스크린샷 캡처

**필수 설정**:
- 모니터 해상도: FHD (1920x1080)
- 앱 실행 후 전체 화면 캡처 (Win + Shift + S)

**캡처할 이미지 목록** (총 20개):

#### BOM 엑셀 저장 (7개)
- [ ] `be_01_app_launch.png` - 바탕화면 아이콘 또는 앱 실행 후 메인 화면
- [ ] `be_02_folder_select.png` - "폴더 선택" 버튼 클릭 전 화면
- [ ] `be_03_scan_progress.png` - 폴더 스캔 중 진행률 표시
- [ ] `be_04_start_export.png` - "저장시작" 버튼 활성화 상태
- [ ] `be_05_complete.png` - 작업 완료 메시지 박스
- [ ] `be_06_buttons.png` - 하단 버튼 영역 (저장시작, 설정, 등록, 업데이트, 종료)

#### DWG 파일 분류 (9개)
- [ ] `dc_01_app_launch.png` - 바탕화면 아이콘 또는 앱 실행 후 메인 화면
- [ ] `dc_02_folder_select.png` - "폴더 선택" 버튼 클릭 전 화면
- [ ] `dc_03_excel_select.png` - "엑셀 선택" 버튼 클릭 전 화면
- [ ] `dc_04_excel_list.png` - 엑셀 파일 선택 후 리스트 표시
- [ ] `dc_05_scan_toggle.png` - "폴더 스캔" 체크박스와 파일 개수 표시
- [ ] `dc_06_start_classification.png` - "분류시작" 버튼 활성화 상태
- [ ] `dc_07_progress.png` - 분류 작업 진행 중
- [ ] `dc_08_complete.png` - 작업 완료 메시지 박스
- [ ] `dc_09_buttons.png` - 하단 버튼 영역

#### 관리자 기능 (3개)
- [ ] `admin_01_toggle.png` - "진행률:" 레이블 클릭 시 비밀번호 입력
- [ ] `admin_02_log_frame.png` - 관리자 모드 로그 프레임 표시
- [ ] `admin_03_test_data.png` - 테스트 데이터 생성 버튼 (DC만)

---

### 3단계: 버튼 좌표 확인

**방법 1: Paint 사용**
1. 이미지를 Paint로 열기
2. 마우스를 버튼 좌상단으로 이동
3. 하단 상태 표시줄에서 좌표 확인 (예: `100, 50`)
4. 버튼 우하단으로 이동하여 크기 계산

**방법 2: PowerShell 스크립트**
```powershell
# 이미지에 마우스 좌표 표시 (옵션)
Add-Type -AssemblyName System.Drawing
$img = [System.Drawing.Image]::FromFile("D:\drive_files\10.worksfree\10.rpa\docs\images\be_01.png")
Write-Host "이미지 크기: $($img.Width) x $($img.Height)"
```

---

### 4단계: border_config.json 수정

`D:\drive_files\10.worksfree\10.rpa\docs\border_config.json` 파일을 열어서 실제 버튼 위치에 맞게 좌표 수정:

```json
{
  "path": "images/be_02_folder_select.png",
  "borders": [
    {
      "x": 20,        // ← 실제 버튼 X 좌표 - 5
      "y": 120,       // ← 실제 버튼 Y 좌표 - 5
      "width": 120,   // ← 실제 버튼 너비 + 10
      "height": 40,   // ← 실제 버튼 높이 + 10
      "thickness": 5
    }
  ]
}
```

**좌표 계산 팁**:
- 경계선이 버튼보다 약간 크게 표시되도록 여유 공간 추가
- `x, y`: 버튼 좌상단 좌표에서 `-5` (왼쪽/위로 5px 여유)
- `width, height`: 실제 크기에서 `+10` (우측/하단 5px 여유)

---

### 5단계: 적색 경계선 추가

**필수 패키지 설치**:
```powershell
pip install pillow
```

**배치 처리 실행**:
```powershell
cd D:\drive_files\10.worksfree\10.rpa\docs
python add_red_border.py --batch border_config.json
```

**결과**:
- 모든 이미지에 적색 경계선이 자동으로 추가됨
- 원본 이미지가 덮어쓰기됨 (백업 권장)

**개별 이미지 처리** (테스트용):
```powershell
# 대화형 모드
python add_red_border.py images/be_01_app_launch.png

# 명령행 모드 (x=100, y=50, width=200, height=100, 두께=5)
python add_red_border.py images/be_01_app_launch.png 100 50 200 100 5
```

---

### 6단계: Markdown → HTML/PDF 변환

**HTML 변환**:
```powershell
# Pandoc 설치 필요: https://pandoc.org/installing.html
pandoc USER_MANUAL.md -o USER_MANUAL.html --standalone --css=style.css
```

**PDF 변환** (추천):
```powershell
# VS Code 확장: Markdown PDF 설치
# 1. USER_MANUAL.md 열기
# 2. Ctrl+Shift+P → "Markdown PDF: Export (pdf)"
# 3. 또는 우클릭 → "Markdown PDF: Export (pdf)"
```

**스타일 적용** (선택사항):
```css
/* docs/style.css */
body {
    font-family: 'Malgun Gothic', sans-serif;
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
}

h1, h2, h3 {
    color: #2c3e50;
}

img {
    max-width: 100%;
    border: 1px solid #ddd;
    border-radius: 4px;
    padding: 5px;
    margin: 10px 0;
}

table {
    border-collapse: collapse;
    width: 100%;
}

th, td {
    border: 1px solid #ddd;
    padding: 12px;
    text-align: left;
}

th {
    background-color: #3498db;
    color: white;
}

code {
    background-color: #f4f4f4;
    padding: 2px 5px;
    border-radius: 3px;
}
```

---

## 🎯 체크리스트

### 사전 준비
- [ ] FHD 모니터 준비 (1920x1080)
- [ ] Python 3.x 설치
- [ ] Pillow 패키지 설치 (`pip install pillow`)
- [ ] 앱 4개 모두 설치 (BE, DC, CV, KFN)

### 이미지 캡처
- [ ] BOM 엑셀 저장: 7개 이미지
- [ ] DWG 파일 분류: 9개 이미지
- [ ] 관리자 기능: 3개 이미지
- [ ] 모든 이미지를 `docs/images/` 폴더에 저장

### 경계선 추가
- [ ] `border_config.json` 좌표 수정
- [ ] 배치 스크립트 실행
- [ ] 모든 이미지에 적색 경계선 확인

### 최종 확인
- [ ] Markdown 미리보기 확인 (VS Code)
- [ ] 이미지 링크 정상 작동 확인
- [ ] HTML/PDF 변환 테스트
- [ ] 오타 및 문법 검토

---

## 📊 예상 소요 시간

| 작업 | 소요 시간 |
|------|-----------|
| 스크린샷 캡처 | 30분 |
| 좌표 확인 및 JSON 수정 | 20분 |
| 적색 경계선 추가 | 5분 |
| HTML/PDF 변환 | 10분 |
| 최종 검토 | 15분 |
| **총 소요 시간** | **약 1.5시간** |

---

## 💡 팁

1. **백업 먼저**: 이미지 캡처 후 원본 백업
2. **일관성**: 모든 이미지에 동일한 해상도와 DPI 사용
3. **테스트**: 1~2개 이미지로 먼저 테스트 후 전체 처리
4. **버전 관리**: 매뉴얼 업데이트 시 날짜와 버전 명시

---

## 🆘 문제 해결

### Q: 적색 경계선이 너무 작거나 크게 나와요.
**A**: `border_config.json`의 `thickness` 값을 조정하세요 (권장: 5~8).

### Q: 좌표를 잘못 입력했어요.
**A**: 원본 이미지를 복원하고 다시 처리하세요. 또는 개별 이미지만 다시 처리:
```powershell
python add_red_border.py images/be_01.png 100 50 200 100 5
```

### Q: 이미지가 매뉴얼에 표시되지 않아요.
**A**: 
- 이미지 경로가 `images/` 폴더인지 확인
- Markdown 미리보기에서 이미지 로드 확인
- 상대 경로 vs 절대 경로 확인

---

**작업 시작 명령어**:
```powershell
# 1. 이미지 폴더 생성
New-Item -ItemType Directory -Force -Path "D:\drive_files\10.worksfree\10.rpa\docs\images"

# 2. 스크린샷 캡처 (수동)
# ... 20개 이미지 캡처 ...

# 3. 패키지 설치
pip install pillow

# 4. 좌표 수정 (수동)
# border_config.json 편집

# 5. 적색 경계선 추가
cd D:\drive_files\10.worksfree\10.rpa\docs
python add_red_border.py --batch border_config.json

# 6. 미리보기 확인
code USER_MANUAL.md
```
