# UTF-8 인코딩 설정
chcp 65001 | Out-Null
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

# 앱 실행
Set-Location "d:\drive_files\10.worksfree\10.rpa\30.apps\bom_exporter"
& "C:\Users\USER\AppData\Local\Python\pythoncore-3.14-64\python.exe" -u ui_main.py
