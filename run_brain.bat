@echo off
:: 파이썬 스크립트가 있는 폴더로 이동 (경로에 공백이 있어서 따옴표 필수!)
cd /d "I:\Files\Coding\Automatic Knowledge Acquisition"

:: 안내 메시지 출력
echo ==========================================
echo 🧠 Brain is Starting... (v2.0 Batch Mode)
echo ==========================================

:: 파이썬 스크립트 실행
python brain.py

:: (선택 사항) 에러가 나서 꺼졌을 때 창이 바로 닫히지 않게 하려면 아래 주석을 푸세요.
:: pause