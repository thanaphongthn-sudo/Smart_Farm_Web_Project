@echo off
chcp 65001 >nul
title Smart Farm - Secure Login Server
cd /d "%~dp0"
echo ==========================================
echo   SMART FARM - REGISTER / LOGIN
echo ==========================================
echo.
py -3 -m pip install -r requirements.txt
if errorlevel 1 (
  echo ติดตั้งไลบรารีไม่สำเร็จ กรุณาตรวจสอบ Python และอินเทอร์เน็ต
  pause
  exit /b 1
)
if not exist ".env" (
  echo กำลังตั้งค่าการเชื่อมต่อ ESP32 ครั้งแรก...
  py -3 setup_login.py
  if errorlevel 1 pause
)
echo.
echo เปิดเว็บไซต์ที่ http://127.0.0.1:8000
echo อย่าปิดหน้าต่างนี้ขณะใช้งาน
echo กด Ctrl+C เพื่อหยุดเซิร์ฟเวอร์
echo.
py -3 app.py
pause
