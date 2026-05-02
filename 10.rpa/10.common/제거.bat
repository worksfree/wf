@echo off
chcp 65001 >nul
REM WorksFree 앱 제거 (바로가기 + 설정 삭제)
call "%~dp0setup_worksfree.bat" /uninstall
