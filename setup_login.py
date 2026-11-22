import os, secrets, re
from werkzeug.security import generate_password_hash
BASE=os.path.dirname(os.path.abspath(__file__))
ino_path=os.path.join(BASE,"esp32_smartfarm.ino")
print("\\n=== ตั้งค่าการเชื่อมต่อ Smart Farm ===")
esp32_url=input("IP ของ ESP32 เช่น http://192.168.1.50: ").strip().rstrip("/")
if not esp32_url.startswith("http://"): raise SystemExit("กรุณาระบุ URL เป็น http:// ตามด้วย IP ของ ESP32")
api_key=secrets.token_urlsafe(32); secret_key=secrets.token_urlsafe(48)
with open(ino_path,"r",encoding="utf-8") as f: code=f.read()
pattern=r'const char\\* API_KEY = "[^"]*";'
if not re.search(pattern,code): raise SystemExit("ไม่พบตำแหน่ง API_KEY ในไฟล์ esp32_smartfarm.ino")
code=re.sub(pattern,'const char* API_KEY = "'+api_key+'";',code,count=1)
with open(ino_path,"w",encoding="utf-8") as f: f.write(code)
env=f"FLASK_SECRET_KEY={secret_key}\\nESP32_URL={esp32_url}\\nESP32_API_KEY={api_key}\\n"
with open(os.path.join(BASE,".env"),"w",encoding="utf-8") as f: f.write(env)
print("\\nตั้งค่าเสร็จแล้ว")
print("ขั้นตอนถัดไป: อัปโหลด esp32_smartfarm.ino ลง ESP32 ใหม่ แล้วเปิด START_SMARTFARM.bat")
print("สมัครสมาชิกและเข้าสู่ระบบได้จากหน้าเว็บ")
