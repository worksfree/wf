@echo off
chcp 65001 >nul
REM WorksFree 전체 설정 초기화 (.wf_rpa 폴더 전체 삭제)
call "%~dp0setup_worksfree.bat" /reset-all
