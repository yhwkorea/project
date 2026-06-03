@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Aim Trainer 서버 시작 중...
start "AimTrainerServer" /min python serve.py
timeout /t 1 >nul
start "" http://localhost:8731/index.html
echo 브라우저가 열렸습니다. 이 창은 닫아도 됩니다 (서버는 별도 창에서 실행 중).
timeout /t 2 >nul
