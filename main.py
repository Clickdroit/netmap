import sys
import os
import webbrowser
import threading
import time
import subprocess
import shutil
import uvicorn

def is_wsl() -> bool:
    if not sys.platform.startswith("linux"):
        return False
    if os.path.exists("/proc/version"):
        try:
            with open("/proc/version", "r", encoding="utf-8", errors="ignore") as f:
                return "microsoft" in f.read().lower() or "wsl" in f.read().lower()
        except Exception:
            pass
    return False

def open_browser():
    time.sleep(1.2)
    url = "http://localhost:8000"
    print(f"\n[Net-Map] Interface disponible sur : {url}")
    
    # Try WSL specific opener first
    if is_wsl():
        for cmd_tool in ["wslview", "cmd.exe", "/mnt/c/WINDOWS/System32/cmd.exe"]:
            if shutil.which(cmd_tool) or os.path.exists(cmd_tool):
                try:
                    if "cmd.exe" in cmd_tool:
                        subprocess.run([cmd_tool, "/c", "start", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    else:
                        subprocess.run([cmd_tool, url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return
                except Exception:
                    pass

    # Standard browser open
    try:
        webbrowser.open(url)
    except Exception:
        pass

if __name__ == "__main__":
    print("=" * 60)
    print("           Net-Map • Scanner Réseau & Topologie           ")
    print("=" * 60)
    print("[*] Démarrage du serveur web local sur le port 8000...")
    
    # Open browser in a separate thread
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Run Uvicorn server (host 0.0.0.0 so both WSL and Windows host can access http://localhost:8000)
    uvicorn.run("backend.app:app", host="0.0.0.0", port=8000, reload=False)
