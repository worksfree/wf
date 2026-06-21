<style>
.warning-icon {
  display: inline-block;
  width: 1.2em;
  height: 1.2em;
  background: #ff9800;
  color: white;
  text-align: center;
  line-height: 1.2em;
  border-radius: 3px;
  font-weight: bold;
  font-size: 0.9em;
  margin-right: 0.2em;
}

.info-icon {
  display: inline-block;
  width: 1.2em;
  height: 1.2em;
  background: #2196F3;
  color: white;
  text-align: center;
  line-height: 1.2em;
  border-radius: 50%;
  font-weight: bold;
  font-size: 0.9em;
  margin-right: 0.2em;
}

.check-icon {
  display: inline-block;
  width: 1.2em;
  height: 1.2em;
  background: #4CAF50;
  color: white;
  text-align: center;
  line-height: 1.2em;
  border-radius: 3px;
  font-weight: bold;
  font-size: 0.9em;
  margin-right: 0.2em;
}

.cross-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.2em;
  height: 1.2em;
  background: #f44336;
  color: white;
  border-radius: 3px;
  font-weight: bold;
  font-size: 1em;
  margin-right: 0.2em;
  vertical-align: middle;
}

.center-box {
  padding: 20px 40px;
  background: #f0f0f0;
  border-radius: 8px;
}
</style>

# QR Code Generator 사용자 매뉴얼

> **버전**: v1.0
> **최종 업데이트**: 2026-01-26
> **제작**: WorksFree

---

## 목차

1. [프로그램 소개](#1-프로그램-소개)
2. [설치 및 실행](#2-설치-및-실행)
3. [사용자 등록](#3-사용자-등록)
4. [기본 사용법](#4-기본-사용법)
5. [크레딧 관리](#5-크레딧-관리)
6. [고급 기능](#6-고급-기능)
7. [문제 해결](#7-문제-해결)

---

## 1. 프로그램 소개

### 1.1 QR Code Generator란?

QR Code Generator는 텍스트, URL, 데이터를 QR 코드 이미지로 변환하는 프로그램입니다. 단일 QR 코드 생성부터 엑셀/CSV 파일을 통한 대량 QR 코드 일괄 생성까지 지원합니다.

### 1.2 주요 기능

- <span class="check-icon">✓</span>텍스트/URL → QR 코드 생성
- <span class="check-icon">✓</span>다양한 크기 및 형식 지원 (PNG, JPEG, SVG)
- <span class="check-icon">✓</span>대량 생성 (엑셀/CSV 입력)
- <span class="check-icon">✓</span>로고 삽입 옵션
- <span class="check-icon">✓</span>색상 커스터마이징
- <span class="check-icon">✓</span>**무료 사용** (크레딧 무제한)

### 1.3 시스템 요구사항

- **운영체제**: Windows 10/11 (64bit)
- **메모리**: 4GB RAM 이상
- **디스크 공간**: 500MB 이상

---

<div style="page-break-after: always;"></div>

---

## 2. 설치 및 실행

### 2.1 프로그램 다운로드

1. WorksFree 공식 웹사이트 또는 제공받은 링크에서 압축 파일 또는 설치 파일을 다운로드합니다.

2. 다운로드를 받으면 `qrcode_generator_vX.X.X_portable.zip` 형식의 파일이 저장됩니다.

### 2.2 압축 해제

1. 다운로드한 ZIP 파일을 원하는 위치에서 압축 해제합니다.
   - **권장 경로**: `C:\WorksFree\qrcode_generator` 또는 `D:\WorksFree\qrcode_generator`
   - <span class="warning-icon">!</span>**주의**: 경로에 다음 문자들을 사용하지 마세요
     - Windows 파일시스템 금지 문자: `*` `:` `?` `"` `<` `>` `|` `/` `\`
     - 특수기호: `★` `◈` `☞` `〉` `⅓` `⅔` `①` 등
     - <span class="cross-icon">×</span>잘못된 예: `C:\Work★Free\qr`, `D:\Apps◈QRCode`
     - <span class="check-icon">✓</span>올바른 예: `C:\WorksFree\qrcode_generator`, `D:\Apps\qrcode_generator`

2. 압축 해제 후 폴더 구조:
   ```
   qrcode_generator_vX.X.X_portable/
   ├── QRCode_Generator.exe           # 실행 파일
   ├── create_desktop_shortcut.bat    # 바로가기 생성 스크립트
   ├── _internal/                     # 필수 라이브러리
   └── ...
   ```

### 2.3 바탕화면 바로가기 생성

1. 압축 해제한 폴더에서 `create_desktop_shortcut.bat` 파일을 **더블클릭**합니다.

2. 바탕화면에 "QR Code Generator" 아이콘이 생성됩니다.

3. 바로가기 아이콘에 마우스를 올리면 **버전 정보**가 표시됩니다.

---

<div style="page-break-after: always;"></div>

---

### 2.4 프로그램 실행

1. 바탕화면의 "QR Code Generator" 아이콘을 더블클릭합니다.

2. 프로그램이 시작되면 다음과 같은 메인 화면이 나타납니다.

<span class="info-icon">i</span>**참고**: 이 프로그램은 **무료**입니다. 사용자 등록 없이도 모든 기능을 사용할 수 있습니다.

## 3. 사용자 등록

### 3.1 체험판 등록

<span class="info-icon">i</span>**참고**: QR Code Generator는 **무료 앱**으로 사용자 등록이 필수가 아닙니다. 등록 없이도 모든 기능을 무제한으로 사용할 수 있습니다.

등록을 원하시는 경우:

1. 메인 화면 하단의 **"등 록"** 버튼을 클릭합니다.

2. 등록 버튼을 클릭하면 등록 창이 나타납니다.

3. 등록을 위해 필요한 정보를 입력합니다.
   - **이름**: 사용자 이름 (선택 항목)
   - **연락처**: 전화번호 (선택 항목)
   - **이메일**: 유효한 이메일 주소 (선택 항목)

4. **"등록하기"** 버튼을 클릭합니다.

5. 등록이 완료되면 **"등 록"** 버튼은 **"설 정"** 버튼으로 변경됩니다.

### 3.2 체험판 크레딧

- QR Code Generator는 **무료 앱**입니다.
- 크레딧 제한이 없으며 무제한으로 사용 가능합니다.
- 크레딧 표시: `무제한`

---

<div style="page-break-after: always;"></div>

---

## 4. 기본 사용법

### 4.1 단일 QR 코드 생성

1. **데이터 입력**: 텍스트 입력란에 변환할 텍스트 또는 URL을 입력합니다.

2. **설정 조정**: 필요에 따라 크기, 색상, 로고 등을 설정합니다.

3. **미리보기**: 입력 즉시 QR 코드 미리보기가 표시됩니다.

4. **저장**: **"저장"** 버튼을 클릭하여 이미지 파일로 저장합니다.

### 4.2 대량 QR 코드 생성

1. **파일 선택**: **"파일 선택"** 버튼을 클릭하여 엑셀/CSV 파일을 선택합니다.

2. **컬럼 지정**: QR 코드로 변환할 데이터가 있는 컬럼을 선택합니다.

3. **출력 폴더**: **"출력 폴더"** 버튼을 클릭하여 저장 위치를 지정합니다.

4. **일괄 생성**: **"일괄 생성"** 버튼을 클릭합니다.

### 4.3 설정 옵션

#### QR 코드 설정

| 항목 | 기본값 | 범위 |
|------|--------|------|
| 크기 | 200px | 100-1000px |
| 오류 정정 | M (15%) | L/M/Q/H |
| 테두리 | 4 | 0-10 |

#### 색상 설정

| 항목 | 기본값 |
|------|--------|
| 전경색 | 검정 (#000000) |
| 배경색 | 흰색 (#FFFFFF) |

#### 출력 형식

- PNG (기본)
- JPEG
- SVG

### 4.4 진행 상황 확인

1. 대량 생성 시 진행률 바와 상태 메시지로 현재 작업 상황을 확인할 수 있습니다.

2. 처리된 QR 코드 개수가 실시간으로 업데이트됩니다.

### 4.5 작업 완료

1. 모든 QR 코드 생성이 완료되면 완료 메시지가 나타납니다.

2. 생성된 파일 위치가 표시됩니다.

---

<div style="page-break-after: always;"></div>

---

## 5. 크레딧 관리

### 5.1 크레딧 확인

- QR Code Generator는 **무료 앱**입니다.
- 메인 화면에 `무제한` 또는 `Free`로 표시됩니다.
- 크레딧 차감 없이 무제한 사용 가능합니다.

### 5.2 크레딧 부족 시

- 해당 없음 (무료 앱)
- 사용 제한이 없습니다.

### 5.3 크레딧 구매

- 해당 없음 (무료 앱)
- 크레딧 구매가 필요하지 않습니다.

### 5.4 크레딧 업데이트

- 해당 없음 (무료 앱)
- 항상 무제한으로 사용 가능합니다.

---

<div style="page-break-after: always;"></div>

---

## 6. 고급 기능

### 6.1 설정 화면

등록 완료 후 **"설 정"** 버튼을 클릭하면 설정 화면이 나타납니다.

설정 화면에서 다음 옵션을 변경할 수 있습니다:

| 항목 | 기본값 | 설명 |
|------|--------|------|
| 기본 크기 | 200px | QR 코드 기본 크기 |
| 기본 오류 정정 | M | 기본 오류 정정 레벨 |
| 기본 출력 형식 | PNG | 기본 이미지 형식 |
| 로고 크기 비율 | 20% | 로고 크기 (QR 대비) |
| 최상위 고정 | OFF | 앱 화면이 항상 위로 올라와 있게 설정 |

### 6.2 오류 정정 레벨

| 레벨 | 복원율 | 용도 |
|------|--------|------|
| L | 7% | 깨끗한 환경 |
| M | 15% | 일반 사용 (기본) |
| Q | 25% | 로고 삽입 시 권장 |
| H | 30% | 열악한 환경 |

<span class="info-icon">i</span>**참고**: 로고를 삽입할 경우 Q 또는 H 레벨을 권장합니다.

### 6.3 로고 삽입

QR 코드 중앙에 로고를 삽입할 수 있습니다:

1. **"로고 선택"** 버튼을 클릭합니다.
2. 삽입할 이미지 파일을 선택합니다 (PNG, JPEG 지원).
3. 로고 크기는 QR 코드의 25% 이하를 권장합니다.
4. 오류 정정 레벨을 Q 또는 H로 설정합니다.

---

<div style="page-break-after: always;"></div>

---

## 7. 문제 해결

### 7.1 자주 묻는 질문 (FAQ)

#### Q1. QR 코드가 인식되지 않아요.

**A1**: 다음 사항을 확인해주세요:
1. 오류 정정 레벨을 높이기 (H 권장)
2. QR 코드 크기가 너무 작은지 확인 (최소 100px 권장)
3. 전경색과 배경색의 대비가 충분한지 확인

#### Q2. 로고가 너무 커서 QR이 인식되지 않아요.

**A2**: 다음 방법을 시도해보세요:
1. 로고 크기를 QR 코드의 25% 이하로 조정
2. 오류 정정 레벨을 H로 변경
3. 로고 배경을 투명하게 처리

#### Q3. 파일 저장 오류가 발생해요.

**A3**: 다음 사항을 확인해주세요:
1. 출력 폴더에 쓰기 권한이 있는지 확인
2. 디스크 공간이 충분한지 확인
3. 파일명에 특수문자가 없는지 확인

#### Q4. 대량 생성 시 일부만 생성되었어요.

**A4**: 다음 사항을 확인해주세요:
1. 엑셀/CSV 파일의 데이터가 올바른지 확인
2. 빈 셀이 있는 행은 건너뜀
3. 파일명에 특수문자가 있는지 확인

### 7.2 오류 메시지 해결

#### "잘못된 데이터 형식"

- **원인**: 입력된 데이터가 QR 코드로 변환할 수 없음
- **해결**: 데이터 형식 확인 (특수문자, 길이 제한)

#### "파일 저장 실패"

- **원인**: 출력 경로 오류 또는 권한 문제
- **해결**: 출력 폴더 권한 확인 및 경로 재지정

#### "하드웨어 정보 불일치"

- **원인**: 최초 등록한 컴퓨터와 다른 컴퓨터에서 실행
- **해결**: 다른 이메일로 현재 컴퓨터에서 새로 등록

### 7.3 고객 지원

추가 지원이 필요한 경우 다음 채널로 문의해주세요:

- **이메일**: insung.lee@worksfree.kr
- **웹사이트**: https://worksfree.com/support
- **운영 시간**: 평일 09:00 - 18:00 (주말/공휴일 제외)

문의 시 다음 정보를 함께 제공해주시면 보다 신속한 지원이 가능합니다:
- 프로그램 버전 (바탕화면 바로가기 툴팁에서 확인)
- 오류 메시지 스크린샷

---

<div style="page-break-after: always;"></div>

---

```
라이선스 및 저작권

© 2025 WorksFree. All rights reserved.

본 소프트웨어 및 문서의 무단 복제, 배포, 수정을 금지합니다.

```

---
