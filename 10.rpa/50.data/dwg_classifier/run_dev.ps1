# DWG Classifier - 개발 모드 실행 스크립트
# UTF-8 인코딩 설정 및 개발 환경 실행

# UTF-8 인코딩 설정
chcp 65001 | Out-Null
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

# 앱 실행
Set-Location "d:\drive_files\10.worksfree\10.rpa\50.data\dwg_classifier"
& "C:\Users\USER\AppData\Local\Python\pythoncore-3.14-64\python.exe" -u ui_main.py
