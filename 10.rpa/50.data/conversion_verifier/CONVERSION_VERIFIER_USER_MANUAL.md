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

# Conversion Verifier 사용자 매뉴얼

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

### 1.1 Conversion Verifier란?

Conversion Verifier는 3D CAD 파일과 변환된 2D 도면(DWG/PDF) 간의 변환 상태를 검증하는 프로그램입니다. 변환 누락이나 미변환 파일을 자동으로 탐지하여 도면 관리의 완전성을 보장합니다.

### 1.2 주요 기능

- <span class="check-icon">✓</span>3D-2D 변환 상태 자동 검증
- <span class="check-icon">✓</span>변환 누락 파일 탐지
- <span class="check-icon">✓</span>다양한 형식 지원 (SLDPRT, SLDASM, DWG, PDF)
- <span class="check-icon">✓</span>검증 결과 리포트 생성
- <span class="check-icon">✓</span>대용량 폴더 처리 지원
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

2. 다운로드를 받으면 `conversion_verifier_vX.X.X_portable.zip` 형식의 파일이 저장됩니다.

### 2.2 압축 해제

1. 다운로드한 ZIP 파일을 원하는 위치에서 압축 해제합니다.
   - **권장 경로**: `C:\WorksFree\conversion_verifier` 또는 `D:\WorksFree\conversion_verifier`
   - <span class="warning-icon">!</span>**주의**: 경로에 다음 문자들을 사용하지 마세요
     - Windows 파일시스템 금지 문자: `*` `:` `?` `"` `<` `>` `|` `/` `\`
     - 특수기호: `★` `◈` `☞` `〉` `⅓` `⅔` `①` 등
     - <span class="cross-icon">×</span>잘못된 예: `C:\Work★Free\cv`, `D:\Apps◈Verifier`
     - <span class="check-icon">✓</span>올바른 예: `C:\WorksFree\conversion_verifier`, `D:\Apps\conversion_verifier`

2. 압축 해제 후 폴더 구조:
   ```
   conversion_verifier_vX.X.X_portable/
   ├── Conversion_Verifier.exe         # 실행 파일
   ├── create_desktop_shortcut.bat     # 바로가기 생성 스크립트
   ├── _internal/                      # 필수 라이브러리
   └── ...
   ```

### 2.3 바탕화면 바로가기 생성

1. 압축 해제한 폴더에서 `create_desktop_shortcut.bat` 파일을 **더블클릭**합니다.

2. 바탕화면에 "Conversion Verifier" 아이콘이 생성됩니다.

3. 바로가기 아이콘에 마우스를 올리면 **버전 정보**가 표시됩니다.

---

<div style="page-break-after: always;"></div>

---

### 2.4 프로그램 실행

1. 바탕화면의 "Conversion Verifier" 아이콘을 더블클릭합니다.

2. 프로그램이 시작되면 다음과 같은 메인 화면이 나타납니다.

<span class="info-icon">i</span>**참고**: 이 프로그램은 **무료**입니다. 사용자 등록 없이도 모든 기능을 사용할 수 있습니다.

## 3. 사용자 등록

### 3.1 체험판 등록

<span class="info-icon">i</span>**참고**: Conversion Verifier는 **무료 앱**으로 사용자 등록이 필수가 아닙니다. 등록 없이도 모든 기능을 무제한으로 사용할 수 있습니다.

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

- Conversion Verifier는 **무료 앱**입니다.
- 크레딧 제한이 없으며 무제한으로 사용 가능합니다.
- 크레딧 표시: `무제한`

---

<div style="page-break-after: always;"></div>

---

## 4. 기본 사용법

### 4.1 작업 폴더 선택

1. **"폴더 선택"** 버튼을 클릭합니다.

2. 검증할 3D CAD 파일과 2D 도면이 있는 폴더를 선택합니다.

3. 선택한 폴더 경로가 표시됩니다.

### 4.2 검증 실행

1. 폴더 선택 후 **"검증 실행"** 버튼이 활성화됩니다.

2. **"검증 실행"** 버튼을 클릭하면 검증 작업이 시작됩니다.

3. 프로그램이 자동으로 다음 작업을 수행합니다:
   - 3D CAD 파일 목록 수집 (.sldprt, .sldasm)
   - 2D 도면 파일 목록 수집 (.dwg, .pdf)
   - 파일명 기준 매칭 검사
   - 변환 누락 파일 탐지

### 4.3 진행 상황 확인

1. 진행률 바와 상태 메시지로 현재 작업 상황을 확인할 수 있습니다.

2. 처리된 파일 개수가 실시간으로 업데이트됩니다.

### 4.4 작업 완료

1. 모든 파일 검증이 완료되면 완료 메시지가 나타납니다.

2. 검증 결과가 요약되어 표시됩니다.

### 4.5 결과 확인

검증 완료 시 다음 정보가 표시됩니다:
- 총 3D 파일 수
- 변환 완료 파일 수
- 변환 누락 파일 수
- 누락 파일 목록 (파일명)

---

<div style="page-break-after: always;"></div>

---

## 5. 크레딧 관리

### 5.1 크레딧 확인

- Conversion Verifier는 **무료 앱**입니다.
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

**"설 정"** 버튼을 클릭하면 설정 화면이 나타납니다.

설정 화면에서 다음 옵션을 변경할 수 있습니다:

| 항목 | 기본값 | 설명 |
|------|--------|------|
| 3D 확장자 | .sldprt, .sldasm | 검사할 3D 파일 확장자 |
| 2D 확장자 | .dwg, .pdf | 검사할 2D 파일 확장자 |
| 하위 폴더 포함 | ON | 하위 폴더도 검사에 포함 |
| 최상위 고정 | OFF | 앱 화면이 항상 위로 올라와 있게 설정 |

### 6.2 검증 규칙

검증 규칙을 설정할 수 있습니다:

- **파일명 매칭**: 파일명이 동일한 경우 매칭으로 판정
- **확장자 무시**: 확장자를 제외한 파일명으로 매칭
- **대소문자 무시**: 대소문자 구분 없이 매칭

---

<div style="page-break-after: always;"></div>

---

## 7. 문제 해결

### 7.1 자주 묻는 질문 (FAQ)

#### Q1. 변환이 완료된 파일인데 누락으로 표시돼요.

**A1**: 다음 사항을 확인해주세요:
1. 파일명이 정확히 일치하는지 확인 (확장자 제외)
2. 대소문자가 다른 경우 설정에서 "대소문자 무시" 옵션 활성화
3. 2D 파일이 지정된 확장자(.dwg, .pdf)인지 확인

#### Q2. 하위 폴더의 파일이 검사되지 않아요.

**A2**: 설정에서 "하위 폴더 포함" 옵션을 확인해주세요:
1. 설정 화면으로 이동
2. "하위 폴더 포함" 옵션을 ON으로 변경
3. 검증 다시 실행

#### Q3. 특정 확장자가 검사되지 않아요.

**A3**: 설정에서 확장자 목록을 확인해주세요:
1. 설정 화면에서 3D/2D 확장자 목록 확인
2. 필요한 확장자 추가 (예: .step, .dxf)

#### Q4. 프로그램이 느리게 실행돼요.

**A4**: 다음 방법을 시도해보세요:
1. 검사 대상 폴더를 SSD 드라이브로 이동
2. 불필요한 프로그램 종료
3. 하위 폴더가 너무 많은 경우 범위 축소

### 7.2 오류 메시지 해결

#### "폴더를 찾을 수 없습니다"

- **원인**: 선택한 폴더가 삭제되었거나 이동됨
- **해결**: 폴더 경로 다시 선택

#### "파일 접근 권한 오류"

- **원인**: 파일 또는 폴더에 읽기 권한 없음
- **해결**: 관리자 권한으로 프로그램 실행

### 7.3 고객 지원

추가 지원이 필요한 경우 다음 채널로 문의해주세요:

- **이메일**: insung.lee@worksfree.co.kr
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
