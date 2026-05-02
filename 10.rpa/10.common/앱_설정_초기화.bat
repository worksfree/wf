@echo off
chcp 65001 >nul
REM WorksFree 현재 앱 설정 초기화
call "%~dp0setup_worksfree.bat" /reset-app
