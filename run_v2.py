import sys
import uvicorn
from app.config import settings

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

if __name__ == "__main__":
    port = 8145
    print(f">> [HAKIKI BILET - YENI NESIL PORTAL V2] Baslatiliyor...")
    print(f">> Tarayicidan erisim: http://localhost:{port}")
    uvicorn.run("app.main:app", host=settings.HOST, port=port, reload=False)
