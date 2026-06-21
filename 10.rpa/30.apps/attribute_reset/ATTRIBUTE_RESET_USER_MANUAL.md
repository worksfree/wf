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

# Attribute Reset 사용자 매뉴얼

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

### 1.1 Attribute Reset이란?

Attribute Reset은 SOLIDWORKS 파일의 사용자 정의 속성(Custom Properties)을 일괄 초기화하는 프로그램입니다. 템플릿 파일 생성 시 기존 속성값을 정리하거나, 파일 재사용을 위해 속성을 초기화할 때 유용합니다.

### 1.2 주요 기능

- <span class="check-icon">✓</span>SOLIDWORKS 파일 속성 일괄 초기화
- <span class="check-icon">✓</span>파트(.sldprt) 및 어셈블리(.sldasm) 지원
- <span class="check-icon">✓</span>특정 속성만 선택적 초기화 가능
- <span class="check-icon">✓</span>백업 자동 생성 옵션
- <span class="check-icon">✓</span>폴더 내 파일 일괄 처리
- <span class="check-icon">✓</span>크레딧 기반 사용량 관리

### 1.3 시스템 요구사항

- **운영체제**: Windows 10/11 (64bit)
- **필수 프로그램**: SOLIDWORKS (2016 이상 권장)
- **메모리**: 4GB RAM 이상
- **디스크 공간**: 500MB 이상

---

<div style="page-break-after: always;"></div>

---

## 2. 설치 및 실행

### 2.1 프로그램 다운로드

1. WorksFree 공식 웹사이트 또는 제공받은 링크에서 압축 파일 또는 설치 파일을 다운로드합니다.

2. 다운로드를 받으면 `attribute_reset_vX.X.X_portable.zip` 형식의 파일이 저장됩니다.

### 2.2 압축 해제

1. 다운로드한 ZIP 파일을 원하는 위치에서 압축 해제합니다.
   - **권장 경로**: `C:\WorksFree\attribute_reset` 또는 `D:\WorksFree\attribute_reset`
   - <span class="warning-icon">!</span>**주의**: 경로에 다음 문자들을 사용하지 마세요
     - Windows 파일시스템 금지 문자: `*` `:` `?` `"` `<` `>` `|` `/` `\`
     - 특수기호: `★` `◈` `☞` `〉` `⅓` `⅔` `①` 등
     - <span class="cross-icon">×</span>잘못된 예: `C:\Work★Free\reset`, `D:\Apps◈Attribute`
     - <span class="check-icon">✓</span>올바른 예: `C:\WorksFree\attribute_reset`, `D:\Apps\attribute_reset`

2. 압축 해제 후 폴더 구조:
   ```
   attribute_reset_vX.X.X_portable/
   ├── Attribute_Reset.exe            # 실행 파일
   ├── create_desktop_shortcut.bat    # 바로가기 생성 스크립트
   ├── _internal/                     # 필수 라이브러리
   └── ...
   ```

### 2.3 바탕화면 바로가기 생성

1. 압축 해제한 폴더에서 `create_desktop_shortcut.bat` 파일을 **더블클릭**합니다.

2. 바탕화면에 "Attribute Reset" 아이콘이 생성됩니다.

3. 바로가기 아이콘에 마우스를 올리면 **버전 정보**가 표시됩니다.

---

<div style="page-break-after: always;"></div>

---

### 2.4 프로그램 실행

1. 바탕화면의 "Attribute Reset" 아이콘을 더블클릭합니다.

2. 프로그램이 시작되면 다음과 같은 메인 화면이 나타납니다.

   <span class="warning-icon">!</span>**주의**: 사용자 등록 전에는 크레딧 없음으로 나옵니다. 사용자 등록 후에 체험판 크레딧도 사용이 가능합니다.

## 3. 사용자 등록

### 3.1 체험판 등록

프로그램을 처음 실행하면 사용자 등록이 필요합니다.

1. 메인 화면 하단의 **"등 록"** 버튼을 클릭합니다.

2. 등록 버튼을 클릭하면 등록 창이 나타납니다.

3. 등록을 위해 필요한 정보를 입력합니다. 실제 사용중인 이메일을 입력합니다.(인증코드 수신 및 확인용)
   - **이름**: 사용자 이름 (선택 항목)
   - **연락처**: 전화번호 (선택 항목)
   - **이메일**: 유효한 이메일 주소 (필수 항목)

4. 이메일을 입력한 후 **"인증코드 받기"** 버튼을 클릭합니다.

5. 본인 이메일의 수신함에서 **6자리 인증코드**를 확인합니다.

6. 인증코드를 입력합니다. <span class="warning-icon">!</span>**주의**: 인증코드는 1회용이며 5분 경과 후 인증이 불가능합니다.

7. 인증코드를 입력한 후 **"등록하기"** 버튼을 클릭합니다.

8. 등록이 완료되면 등록창은 잠시 후 사라지고 메인 앱에서 **"등 록"** 버튼은 **"설 정"** 버튼으로 변경됩니다.

### 3.2 체험판 크레딧

- 체험판 등록 시 **20,000 크레딧**이 무료로 제공됩니다.
- 크레딧은 파일당 200크레딧씩 차감됩니다.
- 약 100개의 파일을 처리할 수 있습니다.
- 메인 화면 우측 하단에서 **잔여 크레딧**을 확인할 수 있습니다.

---

<div style="page-break-after: always;"></div>

---

## 4. 기본 사용법

### 4.1 작업 폴더 선택

1. **"폴더 선택"** 버튼을 클릭합니다.

2. 속성을 초기화할 SOLIDWORKS 파일(.sldprt, .sldasm)이 있는 폴더를 선택합니다.

3. 선택한 폴더 경로가 표시됩니다.

4. 폴더 내 SOLIDWORKS 파일 개수가 표시됩니다.

### 4.2 초기화 설정

1. **초기화 대상 선택**: 초기화할 속성을 선택합니다.
   - 전체 속성 초기화
   - 특정 속성만 선택적 초기화

2. **백업 옵션**: 원본 파일 백업 여부를 선택합니다.
   - 백업 생성 시 `.bak` 확장자로 저장

### 4.3 속성 초기화 실행

1. 설정 완료 후 **"초기화 실행"** 버튼이 활성화됩니다.

2. **"초기화 실행"** 버튼을 클릭하면 초기화 작업이 시작됩니다.

3. 프로그램이 자동으로 다음 작업을 수행합니다:
   - SOLIDWORKS 실행
   - 파일 순차 오픈
   - 선택된 속성 초기화
   - 파일 저장 후 닫기

### 4.4 진행 상황 확인

1. 진행률 바와 상태 메시지로 현재 작업 상황을 확인할 수 있습니다.

2. 처리된 파일 개수와 남은 크레딧이 실시간으로 업데이트됩니다.

### 4.5 작업 완료

1. 모든 파일 처리가 완료되면 완료 메시지가 나타납니다.

2. 초기화된 파일 수와 처리 결과가 표시됩니다.

---

<div style="page-break-after: always;"></div>

---

## 5. 크레딧 관리

### 5.1 크레딧 확인

- 메인 화면 우측 하단에서 현재 크레딧을 확인할 수 있습니다.
- 표시 형식:
  - 체험판 크레딧만 있는 경우: `체험판: 18,000`
  - 충전 크레딧만 있는 경우: `충전: 40,000`
  - 둘 다 있는 경우: `체험판: 2,000/충전: 40,000`

### 5.2 크레딧 부족 시

1. 크레딧이 부족한 경우 경고 메시지가 나타납니다.

2. **"예(Y)"** 버튼을 클릭하면 보유한 크레딧이 전부 소진될 때까지 작업이 진행됩니다.

3. 크레딧이 소진되면 작업이 중단되고 크레딧 구매 안내가 표시됩니다.

### 5.3 크레딧 구매

크레딧은 다음 채널에서 구매할 수 있습니다:

#### 네이버 스마트스토어 <div style="color: red;">(준비중)</div>
- URL: [https://smartstore.naver.com/worksfree](https://smartstore.naver.com/worksfree)
- 결제 방법: 네이버페이, 신용카드, 계좌이체

#### WorksFree 공식 웹사이트 <div style="color: red;">(준비중)</div>
- URL: [https://worksfree.com](https://worksfree.com)
- 결제 방법: 신용카드, 계좌이체

### 5.4 크레딧 업데이트

크레딧을 구매한 후:

1. 메인 화면의 **"업데이트"** 버튼을 클릭합니다.

2. 프로그램이 서버에서 최신 크레딧 정보를 가져옵니다.

3. 업데이트가 완료되면 확인 메시지가 나타나고, 잔여 크레딧이 업데이트됩니다.

---

<div style="page-break-after: always;"></div>

---

## 6. 고급 기능

### 6.1 설정 화면

등록 완료 후 **"설 정"** 버튼을 클릭하면 설정 화면이 나타납니다.

설정 화면에서 다음 옵션을 변경할 수 있습니다:

| 항목 | 기본값 | 설명 |
|------|--------|------|
| SOLIDWORKS 경로 | 자동 감지 | SOLIDWORKS 실행 파일 경로 |
| 백업 생성 | ON | 원본 파일 백업 여부 |
| 백업 위치 | 원본과 같은 폴더 | 백업 파일 저장 위치 |
| 최상위 고정 | OFF | 앱 화면이 항상 위로 올라와 있게 설정 |

### 6.2 초기화 옵션

초기화 대상 속성을 세밀하게 설정할 수 있습니다:

- **전체 속성**: 모든 사용자 정의 속성 초기화
- **선택 속성**: 특정 속성만 선택하여 초기화
- **제외 속성**: 특정 속성을 제외하고 나머지 초기화

---

<div style="page-break-after: always;"></div>

---

## 7. 문제 해결

### 7.1 자주 묻는 질문 (FAQ)

#### Q1. SOLIDWORKS가 자동으로 실행되지 않아요.

**A1**: 다음 사항을 확인해주세요:
1. SOLIDWORKS가 정상적으로 설치되어 있는지 확인
2. 설정 화면에서 SOLIDWORKS 실행 파일 경로 확인
<br><span class="warning-icon">!</span>SOLIDWORKS 2023, 2024 등 여러 버전이 설치된 경우 경로가 기본값과 다를 수 있음

#### Q2. 일부 속성이 초기화되지 않아요.

**A2**: 다음 사항을 확인해주세요:
1. 초기화 대상 속성 설정 확인
2. 시스템 속성은 초기화 대상에서 제외됨
3. 파일이 읽기 전용인지 확인

#### Q3. 파일이 손상되었어요.

**A3**: 다음 방법을 시도해보세요:
1. 백업 파일(.bak)에서 복원
2. 백업 옵션을 항상 ON으로 설정 권장
3. 중요 파일은 별도 백업 후 작업 권장

#### Q4. 프로그램이 느리게 실행돼요.

**A4**: 다음 방법을 시도해보세요:
1. 파일이 있는 폴더를 SSD 드라이브로 이동
2. SOLIDWORKS 및 기타 프로그램 종료
3. 컴퓨터 재시작

### 7.2 오류 메시지 해결

#### "SOLIDWORKS 실행 실패"

- **원인**: SOLIDWORKS 설치 경로 오류 또는 라이선스 문제
- **해결**: SOLIDWORKS 수동 실행 테스트 후 설정에서 경로 확인

#### "파일 접근 권한 오류"

- **원인**: 파일이 읽기 전용이거나 다른 프로그램에서 사용 중
- **해결**: 파일 속성 확인 및 다른 프로그램 종료

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
