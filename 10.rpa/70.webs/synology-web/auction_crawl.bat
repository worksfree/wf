@echo off
:: ================================================================
::  auction_crawl.bat  —  경매지도 데이터 수집 & NAS 업로드
::  더블클릭으로 실행
:: ================================================================
chcp 65001 > nul
PowerShell -NoProfile -ExecutionPolicy Bypass -File "%~dp0auction_crawl.ps1"
