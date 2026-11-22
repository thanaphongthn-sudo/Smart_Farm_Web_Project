@echo off
chcp 65001 >nul
title Smart Farm - Local Web Server
cd /d "%~dp0"
echo ==========================================
echo   SMART FARM - LOCAL WEB SERVER
echo ==========================================
echo.
echo เปิด Chrome หรือ Edge ไปที่:
echo http://127.0.0.1:8000
echo.
echo อย่าปิดหน้าต่างนี้ขณะใช้งานเว็บไซต์
echo กด Ctrl+C เพื่อหยุดเซิร์ฟเวอร์
echo.
py -3 -m http.server 8000 --bind 127.0.0.1
if errorlevel 1 (
  echo.
  echo ไม่พบ Python Launcher (py)
  echo ลองติดตั้ง Python หรือเปิดโฟลเดอร์นี้ใน VS Code แล้วใช้ Live Server
  pause
)
