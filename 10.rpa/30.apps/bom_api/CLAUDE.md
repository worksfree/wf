# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 개요

**bom_api** — SolidWorks COM API(`win32com.client`)를 직접 사용하여 어셈블리(.sldasm) BOM을 추출하고 부품 썸네일 이미지를 포함한 Excel 파일을 생성하는 실험적/프로토타입 모듈.

`bom_exporter`(pywinauto GUI 자동화)와 달리 SolidWorks COM 인터페이스를 직접 호출하는 API 방식.

## 실행

`automation.py` 상단의 설정값 수정 후 직접 실행:

```python
ASSEMBLY_FOLDER = r"경로\assemblies"   # .sldasm 파일이 있는 폴더
OUTPUT_XLSX = r"경로\bom_with_thumbs.xlsx"
THUMBNAIL_FOLDER = r"경로\thumbnails"
SOLIDWORKS_VISIBLE = True
```

```powershell
pip install pywin32 openpyxl pillow
python automation.py
```

## 동작

`automation.py` 단일 파일:
1. `win32com.client.Dispatch("SldWorks.Application")`으로 SolidWorks 인스턴스 생성
2. `.sldasm` 파일 열기 (`OpenDoc6` 또는 `OpenDoc` fallback)
3. BOM 데이터 추출 및 부품 썸네일 캡처
4. `openpyxl`로 Excel 파일에 BOM + 이미지 삽입

## 참고

- GUI 없는 스크립트. WorksFree 앱 크레딧/등록 시스템과 연동되어 있지 않음
- `bom_exporter` 앱의 COM API 방식 검토용 프로토타입으로 사용됨
- `thumbnails/` 폴더에 PNG 이미지 임시 저장 후 Excel에 삽입
