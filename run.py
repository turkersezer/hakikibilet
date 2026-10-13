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
    print(f">> [NET ROTA] Baslatiliyor...")
    print(f">> Tarayicidan erisim: http://localhost:{settings.PORT}")
    print(f">> Swagger API Dokumantasyonu: http://localhost:{settings.PORT}/docs")
    reload_flag = "--reload" in sys.argv
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=reload_flag)
