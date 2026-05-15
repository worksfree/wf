@echo off
:: ================================================================
::  deploy.bat  —  더블클릭으로 NAS 배포
::  PowerShell 실행 정책 우회 포함
:: ================================================================
chcp 65001 > nul
PowerShell -NoProfile -ExecutionPolicy Bypass -File "%~dp0deploy.ps1"
