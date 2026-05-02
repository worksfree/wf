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

# DWG Classifier 사용자 매뉴얼

> **버전**: v0.8.4
> **최종 업데이트**: 2026-01-21
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

### 1.1 DWG Classifier란?

DWG Classifier는 엑셀 파일에 정의된 도면 번호(도번)와 분류 정보를 기반으로, 지정된 폴더 내의 DWG/DXF 파일들을 자동으로 분류하여 정리해주는 프로그램입니다.

예를 들어, 수천 개의 도면 파일이 하나의 폴더에 혼재되어 있을 때, 엑셀에 정의된 "가공분류" 또는 "제조사" 등의 기준으로 자동 분류하여 폴더별로 정리할 수 있습니다.

### 1.2 주요 기능

- <span class="check-icon">✓</span>엑셀 파일 기반 분류 규칙 정의
- <span class="check-icon">✓</span>DWG/DXF 파일 자동 스캔 및 매칭
- <span class="check-icon">✓</span>분류 기준별 폴더 자동 생성 및 파일 정리
- <span class="check-icon">✓</span>복사 또는 이동 모드 선택 가능
- <span class="check-icon">✓</span>매칭되지 않은 파일 별도 관리
- <span class="check-icon">✓</span>분류 결과 리포트 생성
- <span class="check-icon">✓</span>크레딧 기반 사용량 관리

### 1.3 시스템 요구사항

- **운영체제**: Windows 10/11 (64bit)
- **메모리**: 4GB RAM 이상
- **디스크 공간**: 500MB 이상
- **필수 파일**: 분류 규칙이 정의된 엑셀 파일 (.xlsx)

---

<div style="page-break-after: always;"></div>

---

## 2. 설치 및 실행

### 2.1 프로그램 다운로드

1. WorksFree 공식 웹사이트 또는 제공받은 링크에서 압축 파일을 다운로드합니다.

2. 다운로드를 받으면 `dwg_classifier_vX.X.X.X_portable.zip` 형식의 파일이 저장됩니다.

<!-- 이미지 영역: 다운로드 화면 캡처 -->
<div style="border: 2px dashed #ccc; padding: 40px; text-align: center; margin: 10px 0; background: #f9f9f9;">
  <span style="color: #999;">[이미지: 다운로드 화면]</span>
</div>

### 2.2 압축 해제

1. 다운로드한 ZIP 파일을 원하는 위치에서 압축 해제합니다.
   - **권장 경로**: `C:\WorksFree\dwg_classifier` 또는 `D:\WorksFree\dwg_classifier`
   - <span class="warning-icon">!</span>**주의**: 경로에 다음 문자들을 사용하지 마세요
     - Windows 파일시스템 금지 문자: `*` `:` `?` `"` `<` `>` `|` `/` `\`
     - 특수기호: `★` `◈` `☞` `〉` `⅓` `⅔` `①` 등
     - <span class="cross-icon">×</span>잘못된 예: `C:\Work★Free\dwg`, `D:\Apps◈DC`
     - <span class="check-icon">✓</span>올바른 예: `C:\WorksFree\dwg_classifier`, `D:\Apps\dwg_classifier`

2. 압축 해제 후 폴더 구조:
   ```
   dwg_classifier_vX.X.X_portable/
   ├── dwg_classifier.exe         # 실행 파일
   ├── setup_worksfree.bat        # 초기 설정 스크립트
   ├── 바로가기_생성.bat           # 바탕화면 바로가기 생성
   ├── 설정_초기화.bat             # 앱 설정 초기화
   ├── 전체_초기화.bat             # 전체 초기화 (등록정보 포함)
   ├── 등록정보_동기화.bat         # 서버 동기화
   ├── 제거.bat                   # 프로그램 제거
   └── _internal/                 # 필수 라이브러리
   ```

<!-- 이미지 영역: 폴더 구조 캡처 -->
<div style="border: 2px dashed #ccc; padding: 40px; text-align: center; margin: 10px 0; background: #f9f9f9;">
  <span style="color: #999;">[이미지: 압축 해제 후 폴더 구조]</span>
</div>

### 2.3 초기 설정

1. 압축 해제한 폴더에서 `setup_worksfree.bat` 파일을 **더블클릭**합니다.

2. 이 스크립트는 다음 작업을 자동으로 수행합니다:
   - 바탕화면 바로가기 생성
   - 사용자 설정 폴더 초기화 (`%USERPROFILE%\.wf_rpa\dwg_classifier`)

<!-- 이미지 영역: setup_worksfree.bat 실행 화면 -->
<div style="border: 2px dashed #ccc; padding: 40px; text-align: center; margin: 10px 0; background: #f9f9f9;">
  <span style="color: #999;">[이미지: 초기 설정 스크립트 실행]</span>
</div>

---

<div style="page-break-after: always;"></div>

---

3. 바탕화면에 "DWG Classifier" 아이콘이 생성됩니다.

<!-- 이미지 영역: 바탕화면 아이콘 -->
<div style="border: 2px dashed #ccc; padding: 40px; text-align: center; margin: 10px 0; background: #f9f9f9;">
  <span style="color: #999;">[이미지: 바탕화면 바로가기 아이콘]</span>
</div>

4. 바로가기 아이콘에 마우스를 올리면 **버전 정보**가 표시됩니다.

### 2.4 프로그램 실행

1. 바탕화면의 "DWG Classifier" 아이콘을 더블클릭합니다.

2. 프로그램이 시작되면 다음과 같은 메인 화면이 나타납니다.

   <span class="warning-icon">!</span>**주의**: 사용자 등록 전에는 크레딧 없음으로 나옵니다. 사용자 등록 후에 체험판 크레딧도 사용이 가능합니다.

<!-- 이미지 영역: 메인 화면 (미등록 상태) -->
<div style="border: 2px dashed #ccc; padding: 40px; text-align: center; margin: 10px 0; background: #f9f9f9;">
  <span style="color: #999;">[이미지: 메인 화면 - 등록 전 상태]</span>
</div>

---

<div style="page-break-after: always;"></div>

---

## 3. 사용자 등록

### 3.1 체험판 등록

프로그램을 처음 실행하면 사용자 등록이 필요합니다.

1. 메인 화면 하단의 **"등 록"** 버튼을 클릭합니다.

<!-- 이미지 영역: 등록 버튼 위치 -->
<div style="border: 2px dashed #ccc; padding: 40px; text-align: center; margin: 10px 0; background: #f9f9f9;">
  <span style="color: #999;">[이미지: 메인 화면 - 등록 버튼 강조]</span>
</div>

2. 등록 버튼을 클릭하면 다음과 같이 등록 창이 나타납니다.

<!-- 이미지 영역: 등록 폼 -->
<div style="border: 2px dashed #ccc; padding: 40px; text-align: center; margin: 10px 0; background: #f9f9f9;">
  <span style="color: #999;">[이미지: 등록 정보 입력 화면]</span>
</div>

3. 등록을 위해 필요한 정보를 입력합니다. 실제 사용중인 이메일을 입력합니다.(인증코드 수신 및 확인용)
   - **이름**: 사용자 이름 (선택 항목)
   - **연락처**: 전화번호 (선택 항목)
   - **이메일**: 유효한 이메일 주소 (필수 항목)

4. 이메일을 입력한 후 **"인증코드 받기"** 버튼을 클릭합니다.

5. 방금 입력한 본인 이메일의 수신함으로 가서 **6자리 인증코드**를 확인합니다.

6. 인증코드를 입력합니다. <span class="warning-icon">!</span>**주의**: 인증코드는 1회용이며 5분 경과 후 인증이 불가능합니다.

7. 인증코드를 입력한 후 **"등록하기"** 버튼을 클릭합니다.

8. 등록이 완료되면 등록창은 잠시 후 사라지고 메인 앱에서 **"등 록"** 버튼은 **"설 정"** 버튼으로 변경됩니다.

<!-- 이미지 영역: 등록 완료 후 화면 -->
<div style="border: 2px dashed #ccc; padding: 40px; text-align: center; margin: 10px 0; background: #f9f9f9;">
  <span style="color: #999;">[이미지: 등록 완료 후 메인 화면]</span>
</div>

### 3.2 체험판 크레딧

- 체험판 등록 시 **무료 크레딧**이 제공됩니다.
- 크레딧은 1개 파일 분류당 정해진 크레딧씩 차감됩니다.
- 메인 화면 하단에서 **잔여 크레딧**을 확인할 수 있습니다.

---

<div style="page-break-after: always;"></div>

---

## 4. 기본 사용법

### 4.1 작업 흐름 개요

DWG Classifier의 기본 작업 흐름은 다음과 같습니다:

```
1. DWG/DXF 파일이 있는 폴더 선택
       ↓
2. 스캔 시작 (파일 목록 로드)
       ↓
3. 분류 규칙 엑셀 파일 선택
       ↓
4. 분류 시작 (파일 정리 실행)
       ↓
5. 결과 확인
```

### 4.2 엑셀 파일 준비

분류를 위해서는 도면 번호와 분류 기준이 정의된 엑셀 파일이 필요합니다.

**엑셀 파일 형식 예시:**

| 도번 | 가공분류 | 비고 |
|------|---------|------|
| DRW0001 | 선반가공 | - |
| DRW0002 | 밀링가공 | - |
| DRW0003 | 용접 | - |
| DRW0004 | 선반가공 | - |
| ... | ... | ... |

<span class="info-icon">i</span>**참고**:
- "도번" 열: DWG 파일명과 매칭되는 도면 번호
- "가공분류" 열: 분류 기준 (폴더명으로 사용됨)
- 열 이름은 설정에서 변경 가능합니다.

### 4.3 DWG 폴더 선택

1. **"폴더 선택"** 버튼을 클릭합니다.

<!-- 이미지 영역: 폴더 선택 버튼 -->
<div style="border: 2px dashed #ccc; padding: 40px; text-align: center; margin: 10px 0; background: #f9f9f9;">
  <span style="color: #999;">[이미지: 폴더 선택 버튼 위치]</span>
</div>

2. DWG/DXF 파일이 있는 폴더를 선택합니다.

<!-- 이미지 영역: 폴더 선택 대화상자 -->
<div style="border: 2px dashed #ccc; padding: 40px; text-align: center; margin: 10px 0; background: #f9f9f9;">
  <span style="color: #999;">[이미지: 폴더 선택 대화상자]</span>
</div>

3. 선택한 폴더 경로가 화면에 표시됩니다.

### 4.4 파일 스캔

1. 폴더를 선택한 후, **"스캔"** 토글 버튼을 켭니다.

<!-- 이미지 영역: 스캔 토글 버튼 -->
<div style="border: 2px dashed #ccc; padding: 40px; text-align: center; margin: 10px 0; background: #f9f9f9;">
  <span style="color: #999;">[이미지: 스캔 토글 버튼]</span>
</div>

2. 프로그램이 지정된 폴더에서 DWG/DXF 파일을 검색합니다.

3. 스캔 결과가 화면에 표시됩니다:
   - 발견된 DWG/DXF 파일 수
   - 파일 목록 미리보기

<!-- 이미지 영역: 스캔 결과 -->
<div style="border: 2px dashed #ccc; padding: 40px; text-align: center; margin: 10px 0; background: #f9f9f9;">
  <span style="color: #999;">[이미지: 스캔 결과 화면]</span>
</div>

---

<div style="page-break-after: always;"></div>

---

### 4.5 엑셀 파일 선택

1. 스캔이 완료된 후, **"엑셀 선택"** 버튼을 클릭합니다.

<!-- 이미지 영역: 엑셀 선택 버튼 -->
<div style="border: 2px dashed #ccc; padding: 40px; text-align: center; margin: 10px 0; background: #f9f9f9;">
  <span style="color: #999;">[이미지: 엑셀 선택 버튼 위치]</span>
</div>

2. 분류 규칙이 정의된 엑셀 파일(.xlsx)을 선택합니다.

3. 여러 개의 엑셀 파일을 선택할 수 있습니다. (Ctrl 또는 Shift 키 사용)

4. 선택된 엑셀 파일 목록이 화면에 표시됩니다.

<!-- 이미지 영역: 엑셀 파일 목록 -->
<div style="border: 2px dashed #ccc; padding: 40px; text-align: center; margin: 10px 0; background: #f9f9f9;">
  <span style="color: #999;">[이미지: 선택된 엑셀 파일 목록]</span>
</div>

5. 프로그램이 엑셀 파일에서 도면 번호 및 분류 정보를 읽고, 스캔된 파일과 매칭합니다:
   - 매칭된 파일 수
   - 미매칭 파일 수

### 4.6 분류 시작

1. 스캔이 완료되면 **"분류시작"** 버튼이 활성화됩니다.

2. **"분류시작"** 버튼을 클릭합니다.

<!-- 이미지 영역: 분류시작 버튼 -->
<div style="border: 2px dashed #ccc; padding: 40px; text-align: center; margin: 10px 0; background: #f9f9f9;">
  <span style="color: #999;">[이미지: 분류시작 버튼]</span>
</div>

3. 프로그램이 분류 작업을 수행합니다:
   - 분류 기준별 폴더 자동 생성
   - 파일 복사 또는 이동 (설정에 따라)
   - 진행률 표시

---

<div style="page-break-after: always;"></div>

---

### 4.7 분류 결과 확인

1. 분류가 완료되면 결과 요약 팝업이 나타납니다.

<!-- 이미지 영역: 분류 완료 팝업 -->
<div style="border: 2px dashed #ccc; padding: 40px; text-align: center; margin: 10px 0; background: #f9f9f9;">
  <span style="color: #999;">[이미지: 분류 완료 결과 팝업]</span>
</div>

2. 분류된 폴더 구조 예시:
   ```
   [출력 폴더]/
   ├── 선반가공/
   │   ├── DRW0001.dwg
   │   └── DRW0004.dwg
   ├── 밀링가공/
   │   └── DRW0002.dwg
   ├── 용접/
   │   └── DRW0003.dwg
   └── _미분류/
       └── DRW9999.dwg  (엑셀에 없는 파일)
   ```

3. **"폴더 열기"** 버튼으로 분류된 폴더를 확인할 수 있습니다.

---

<div style="page-break-after: always;"></div>

---

## 5. 크레딧 관리

### 5.1 크레딧 확인

- 메인 화면 하단에서 현재 크레딧을 확인할 수 있습니다.
- 표시 형식:
  - 체험판 크레딧만 있는 경우: `체험판: 9,000`
  - 충전 크레딧만 있는 경우: `충전: 9,000`
  - 둘 다 있는 경우: `체험판: 900/충전: 20,000`

### 5.2 크레딧 차감

- 파일 1개 분류 시 설정된 크레딧이 차감됩니다.
- 기본 설정: 파일당 50 크레딧
- 차감 순서: 체험판 크레딧 → 충전 크레딧

### 5.3 크레딧 부족 시

1. 크레딧이 부족한 경우 경고 메시지가 나타납니다.

<!-- 이미지 영역: 크레딧 부족 경고 -->
<div style="border: 2px dashed #ccc; padding: 40px; text-align: center; margin: 10px 0; background: #f9f9f9;">
  <span style="color: #999;">[이미지: 크레딧 부족 경고 팝업]</span>
</div>

2. **"예(Y)"** 버튼 클릭 시: 보유한 크레딧이 전부 소진될 때까지 작업 진행
3. **"아니오(N)"** 버튼 클릭 시: 작업 취소

### 5.4 크레딧 구매

크레딧은 다음 채널에서 구매할 수 있습니다:

#### 네이버 스마트스토어 <span style="color: red;">(준비중)</span>
- URL: [https://smartstore.naver.com/worksfree](https://smartstore.naver.com/worksfree)
- 결제 방법: 네이버페이, 신용카드, 계좌이체

#### WorksFree 공식 웹사이트 <span style="color: red;">(준비중)</span>
- URL: [https://worksfree.com](https://worksfree.com)
- 결제 방법: 신용카드, 계좌이체

### 5.5 크레딧 업데이트

크레딧을 구매한 후:

1. 메인 화면의 **"업데이트"** 버튼을 클릭합니다.

2. 프로그램이 서버에서 최신 크레딧 정보를 가져옵니다.

3. 업데이트가 완료되면 잔여 크레딧이 갱신됩니다.

---

<div style="page-break-after: always;"></div>

---

## 6. 고급 기능

### 6.1 설정 화면

등록 완료 후 **"설 정"** 버튼을 클릭하면 설정 화면이 나타납니다.

<!-- 이미지 영역: 설정 화면 -->
<div style="border: 2px dashed #ccc; padding: 40px; text-align: center; margin: 10px 0; background: #f9f9f9;">
  <span style="color: #999;">[이미지: 설정 화면]</span>
</div>

설정 화면에서 다음 옵션을 변경할 수 있습니다:

| 설정 항목 | 설명 | 기본값 |
|----------|------|--------|
| **도번 열** | 엑셀에서 도면 번호가 있는 열 이름 | 도번 |
| **분류 열** | 엑셀에서 분류 기준이 있는 열 이름 | 가공분류 |
| **시트 이름** | 엑셀에서 읽어올 시트 이름 | 구매요청 |
| **파일 확장자** | 분류 대상 파일 확장자 | .dwg, .DWG |
| **파일 처리 모드** | 복사(copy) 또는 이동(move) | copy |
| **정확한 매칭** | 파일명 정확히 일치 여부 | 사용 |
| **부분 매칭** | 파일명 일부 포함 여부 | 사용 |
| **대소문자 구분** | 파일명 대소문자 구분 | 미사용 |
| **최상위 고정** | 앱 창이 항상 위에 표시 | 사용 |
| **출력 폴더** | 분류된 파일이 저장될 폴더 | (선택 폴더) |

### 6.2 윈도우 위치 저장 (Alt+G)

1. 앱 창을 원하는 위치로 이동합니다.
2. `Alt + G` 키를 누릅니다.
3. 창 위치가 저장되며, 다음 실행 시 같은 위치에서 시작합니다.

### 6.3 유틸리티 BAT 파일

| 파일명 | 기능 |
|--------|------|
| `바로가기_생성.bat` | 바탕화면 바로가기 재생성 |
| `설정_초기화.bat` | 앱 설정만 초기화 (등록정보 유지) |
| `전체_초기화.bat` | 모든 설정 및 등록정보 초기화 |
| `등록정보_동기화.bat` | 서버와 등록정보 동기화 |
| `제거.bat` | 바로가기 및 설정 파일 제거 |

---

<div style="page-break-after: always;"></div>

---

## 7. 문제 해결

### 7.1 자주 묻는 질문 (FAQ)

#### Q1. 엑셀 파일을 선택했는데 도면 번호가 인식되지 않아요.

**A1**: 다음 사항을 확인해주세요:
1. 엑셀 파일의 시트 이름이 설정과 일치하는지 확인 (기본: "구매요청")
2. 도번 열 이름이 설정과 일치하는지 확인 (기본: "도번")
3. 첫 번째 행이 헤더(열 이름)인지 확인

#### Q2. 일부 파일만 분류되고 나머지는 미분류 폴더로 갑니다.

**A2**: 다음 방법을 시도해보세요:
1. 파일명과 엑셀의 도번이 정확히 일치하는지 확인
2. 설정에서 "부분 매칭" 옵션 활성화
3. 설정에서 "대소문자 구분" 옵션 비활성화
4. 파일 확장자가 설정된 확장자 목록에 포함되는지 확인

#### Q3. 크레딧을 구매했는데 업데이트가 안 돼요.

**A3**: 다음 순서로 진행해주세요:
1. 인터넷 연결 확인
2. **"업데이트"** 버튼 클릭
3. 1~2분 정도 대기
4. 그래도 안 되면 프로그램 재시작 후 다시 시도
5. 계속 문제가 있으면 고객센터로 문의

#### Q4. 프로그램이 실행되지 않아요.

**A4**: 다음 사항을 확인해주세요:
1. Windows 10/11 64bit 환경인지 확인
2. 압축 해제 경로에 특수문자가 없는지 확인
3. 관리자 권한으로 실행 시도
4. 바이러스 백신 프로그램에서 예외 처리

### 7.2 오류 메시지 해결

#### "하드웨어 정보 불일치"

- **원인**: 최초 등록한 컴퓨터와 다른 컴퓨터에서 실행
- **해결**:
  1. 다른 이메일로 현재 컴퓨터에서 새로 등록
  2. 신규 등록은 체험판 크레딧이 제공됨
  3. 체험판 크레딧 소진 후 신규 크레딧 구매

#### "크레딧 매니저가 초기화되지 않았습니다"

- **원인**: 서버 연결 문제 또는 프로그램 오류
- **해결**:
  1. 프로그램 재시작
  2. 인터넷 연결 확인
  3. 방화벽 설정 확인

#### "엑셀 파일 읽기 실패"

- **원인**: 엑셀 파일 형식 오류 또는 손상
- **해결**:
  1. 엑셀 파일이 .xlsx 형식인지 확인
  2. 파일이 다른 프로그램에서 열려있지 않은지 확인
  3. 엑셀에서 파일을 다시 저장

### 7.3 고객 지원

추가 지원이 필요한 경우 다음 채널로 문의해주세요:

- **이메일**: support@worksfree.co.kr
- **웹사이트**: https://worksfree.com/support
- **운영 시간**: 평일 09:00 - 18:00 (주말/공휴일 제외)

문의 시 다음 정보를 함께 제공해주시면 보다 신속한 지원이 가능합니다:
- 프로그램 버전 (바탕화면 바로가기 툴팁에서 확인)
- 오류 메시지 스크린샷
- 사용 중인 엑셀 파일 형식 정보

---

<div style="page-break-after: always;"></div>

---

## 부록

### A. 키보드 단축키

| 단축키 | 기능 |
|--------|------|
| `Alt+G` | 창 위치/크기 저장 |
| `Esc` | 진행 중인 작업 중단 |

### B. 파일 구조

```
[출력 폴더]/
├── [분류1]/                    # 분류 기준별 폴더
│   ├── file1.dwg
│   └── file2.dwg
├── [분류2]/
│   └── file3.dwg
├── _미분류/                    # 매칭되지 않은 파일
│   └── unknown.dwg
└── classification_report.txt   # 분류 결과 리포트
```

### C. 지원 파일 형식

- **입력**: .dwg, .dxf, .DWG, .DXF
- **분류 규칙**: .xlsx (Excel 2007 이상)

### D. 버전 이력

- **v0.8.4** (2026-01-21)
  - 6개 BAT 유틸리티 스크립트 추가
  - 등록정보 동기화 기능 추가
  - UI 안정성 향상

- **v0.8.0** (2025-12-XX)
  - 초기 릴리스
  - 엑셀 기반 DWG 파일 분류 기능

---

```
라이선스 및 저작권

© 2026 WorksFree. All rights reserved.

본 소프트웨어 및 문서의 무단 복제, 배포, 수정을 금지합니다.
```

---
