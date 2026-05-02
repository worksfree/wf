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

# Korean Filename Normalizer 사용자 매뉴얼

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

### 1.1 Korean Filename Normalizer란?

Korean Filename Normalizer는 Mac/iOS에서 생성된 파일의 자소분리(NFD) 한글 파일명을 Windows 호환(NFC) 형식으로 복원하는 프로그램입니다. Mac에서 Windows로 파일을 복사했을 때 한글 파일명이 깨져 보이는 문제를 해결합니다.

### 1.2 주요 기능

- <span class="check-icon">✓</span>NFD → NFC 자동 변환
- <span class="check-icon">✓</span>폴더 내 모든 파일 일괄 처리
- <span class="check-icon">✓</span>하위 폴더 포함 옵션
- <span class="check-icon">✓</span>미리보기 기능 (변경 전 확인)
- <span class="check-icon">✓</span>폴더명 변환 옵션
- <span class="check-icon">✓</span>**무료 사용** (크레딧 무제한)

### 1.3 시스템 요구사항

- **운영체제**: Windows 10/11 (64bit)
- **메모리**: 4GB RAM 이상
- **디스크 공간**: 500MB 이상

### 1.4 문제 상황

Mac/iOS에서 생성된 파일을 Windows에서 열면:
```
Mac에서 생성: "한글파일.txt"  (NFD: ㅎ+ㅏ+ㄴ+...)
Windows에서 표시: "ㅎㅏㄴㄱㅡㄹㅍㅏㅇㅣㄹ.txt" (자소분리)

→ 이 앱으로 정상 파일명으로 복원
```

---

<div style="page-break-after: always;"></div>

---

## 2. 설치 및 실행

### 2.1 프로그램 다운로드

1. WorksFree 공식 웹사이트 또는 제공받은 링크에서 압축 파일 또는 설치 파일을 다운로드합니다.

2. 다운로드를 받으면 `korean_filename_normalizer_vX.X.X_portable.zip` 형식의 파일이 저장됩니다.

### 2.2 압축 해제

1. 다운로드한 ZIP 파일을 원하는 위치에서 압축 해제합니다.
   - **권장 경로**: `C:\WorksFree\korean_filename_normalizer` 또는 `D:\WorksFree\korean_filename_normalizer`
   - <span class="warning-icon">!</span>**주의**: 경로에 다음 문자들을 사용하지 마세요
     - Windows 파일시스템 금지 문자: `*` `:` `?` `"` `<` `>` `|` `/` `\`
     - 특수기호: `★` `◈` `☞` `〉` `⅓` `⅔` `①` 등
     - <span class="cross-icon">×</span>잘못된 예: `C:\Work★Free\kfn`, `D:\Apps◈Korean`
     - <span class="check-icon">✓</span>올바른 예: `C:\WorksFree\korean_filename_normalizer`, `D:\Apps\korean_filename_normalizer`

2. 압축 해제 후 폴더 구조:
   ```
   korean_filename_normalizer_vX.X.X_portable/
   ├── Korean_Filename_Normalizer.exe  # 실행 파일
   ├── create_desktop_shortcut.bat     # 바로가기 생성 스크립트
   ├── _internal/                      # 필수 라이브러리
   └── ...
   ```

### 2.3 바탕화면 바로가기 생성

1. 압축 해제한 폴더에서 `create_desktop_shortcut.bat` 파일을 **더블클릭**합니다.

2. 바탕화면에 "Korean Filename Normalizer" 아이콘이 생성됩니다.

3. 바로가기 아이콘에 마우스를 올리면 **버전 정보**가 표시됩니다.

---

<div style="page-break-after: always;"></div>

---

### 2.4 프로그램 실행

1. 바탕화면의 "Korean Filename Normalizer" 아이콘을 더블클릭합니다.

2. 프로그램이 시작되면 다음과 같은 메인 화면이 나타납니다.

<span class="info-icon">i</span>**참고**: 이 프로그램은 **무료**입니다. 사용자 등록 없이도 모든 기능을 사용할 수 있습니다.

## 3. 사용자 등록

### 3.1 체험판 등록

<span class="info-icon">i</span>**참고**: Korean Filename Normalizer는 **무료 앱**으로 사용자 등록이 필수가 아닙니다. 등록 없이도 모든 기능을 무제한으로 사용할 수 있습니다.

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

- Korean Filename Normalizer는 **무료 앱**입니다.
- 크레딧 제한이 없으며 무제한으로 사용 가능합니다.
- 크레딧 표시: `무제한`

---

<div style="page-break-after: always;"></div>

---

## 4. 기본 사용법

### 4.1 작업 폴더 선택

1. **"폴더 선택"** 버튼을 클릭합니다.

2. 자소분리된 한글 파일명을 가진 파일들이 있는 폴더를 선택합니다.

3. 선택한 폴더 경로가 표시됩니다.

### 4.2 미리보기

1. **"미리보기"** 버튼을 클릭합니다.

2. 변경될 파일명 목록이 표시됩니다:
   - 현재 파일명 (NFD)
   - 변환 후 파일명 (NFC)

3. 변환 대상 파일 수를 확인합니다.

<span class="info-icon">i</span>**참고**: 미리보기는 실제 변환을 수행하지 않으므로 안전하게 확인할 수 있습니다.

### 4.3 변환 실행

1. 미리보기로 변환 대상을 확인한 후 **"변환 실행"** 버튼을 클릭합니다.

2. 프로그램이 자동으로 다음 작업을 수행합니다:
   - 파일명의 NFD 인코딩 감지
   - NFC 형식으로 변환
   - 파일명 변경

### 4.4 진행 상황 확인

1. 진행률 바와 상태 메시지로 현재 작업 상황을 확인할 수 있습니다.

2. 처리된 파일 개수가 실시간으로 업데이트됩니다.

### 4.5 작업 완료

1. 모든 파일 처리가 완료되면 완료 메시지가 나타납니다.

2. 변환된 파일 수와 처리 결과가 표시됩니다.

---

<div style="page-break-after: always;"></div>

---

## 5. 크레딧 관리

### 5.1 크레딧 확인

- Korean Filename Normalizer는 **무료 앱**입니다.
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
| 하위 폴더 포함 | ON | 하위 폴더의 파일도 처리 |
| 폴더명도 변환 | OFF | 파일명뿐 아니라 폴더명도 변환 |
| 테스트 모드 | OFF | 실제 변환 없이 시뮬레이션 |
| 최상위 고정 | OFF | 앱 화면이 항상 위로 올라와 있게 설정 |

### 6.2 기술 설명

#### NFD vs NFC

| 형식 | 설명 | 예시 |
|------|------|------|
| NFD | 정규분해 (Mac 기본) | "가" → "ㄱ" + "ㅏ" |
| NFC | 정규합성 (Windows 기본) | "가" → "가" |

#### 변환 원리

```python
import unicodedata
nfc_name = unicodedata.normalize('NFC', nfd_name)
```

---

<div style="page-break-after: always;"></div>

---

## 7. 문제 해결

### 7.1 자주 묻는 질문 (FAQ)

#### Q1. 파일명이 변경되지 않아요.

**A1**: 다음 사항을 확인해주세요:
1. 이미 NFC 형식일 수 있음 (변환 불필요)
2. 미리보기에서 변환 대상 파일이 있는지 확인
3. 파일이 다른 프로그램에서 사용 중인지 확인

#### Q2. 권한 오류가 발생해요.

**A2**: 다음 방법을 시도해보세요:
1. 관리자 권한으로 프로그램 실행
2. 파일이 읽기 전용인지 확인
3. 네트워크 드라이브의 경우 권한 확인

#### Q3. 일부 파일만 변환되었어요.

**A3**: 다음 사항을 확인해주세요:
1. 변환 필요한 파일만 처리됨 (정상)
2. 파일이 사용 중인 경우 건너뜀
3. 하위 폴더 포함 옵션 확인

#### Q4. 폴더명도 변환하고 싶어요.

**A4**: 설정에서 "폴더명도 변환" 옵션을 활성화해주세요:
1. 설정 화면으로 이동
2. "폴더명도 변환" 옵션을 ON으로 변경
3. 변환 다시 실행

### 7.2 오류 메시지 해결

#### "파일 접근 권한 오류"

- **원인**: 파일 또는 폴더에 쓰기 권한 없음
- **해결**: 관리자 권한으로 프로그램 실행

#### "파일이 사용 중입니다"

- **원인**: 파일이 다른 프로그램에서 열려 있음
- **해결**: 해당 파일을 사용하는 프로그램 종료 후 재시도

#### "폴더를 찾을 수 없습니다"

- **원인**: 선택한 폴더가 삭제되었거나 이동됨
- **해결**: 폴더 경로 다시 선택

### 7.3 고객 지원

추가 지원이 필요한 경우 다음 채널로 문의해주세요:

- **이메일**: insung.lee@worksfree.co.kr
- **웹사이트**: https://worksfree.com/support
- **운영 시간**: 평일 09:00 - 18:00 (주말/공휴일 제외)

문의 시 다음 정보를 함께 제공해주시면 보다 신속한 지원이 가능합니다:
- 프로그램 버전 (바탕화면 바로가기 툴팁에서 확인)
- 오류 메시지 스크린샷

---

## 8. 주의사항

- **원본 백업**: 중요 파일은 미리 백업 권장
- **테스트 모드**: 먼저 테스트 모드로 확인 후 실행
- **파일 사용 중**: 사용 중인 파일은 변환 불가

---

<div style="page-break-after: always;"></div>

---

```
라이선스 및 저작권

© 2025 WorksFree. All rights reserved.

본 소프트웨어 및 문서의 무단 복제, 배포, 수정을 금지합니다.

```

---
