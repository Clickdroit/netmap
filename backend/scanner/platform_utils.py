import sys
import os
import shutil

def is_windows() -> bool:
    return sys.platform == "win32"

def is_wsl() -> bool:
    if not sys.platform.startswith("linux"):
        return False
    if os.path.exists("/proc/version"):
        try:
            with open("/proc/version", "r", encoding="utf-8", errors="ignore") as f:
                content = f.read().lower()
                return "microsoft" in content or "wsl" in content
        except Exception:
            pass
    return False

def is_linux() -> bool:
    return sys.platform.startswith("linux")

def get_powershell_cmd() -> str:
    """Returns the powershell executable name depending on OS."""
    if is_windows():
        return "powershell"
    if is_wsl():
        # Check if powershell.exe is in PATH
        ps_path = shutil.which("powershell.exe")
        if ps_path:
            return ps_path
        # Common fallback path in WSL
        default_path = "/mnt/c/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe"
        if os.path.exists(default_path):
            return default_path
    return "powershell"

def has_windows_interop() -> bool:
    """True if running in WSL with access to Windows executables."""
    return is_wsl() and bool(shutil.which("powershell.exe") or shutil.which("arp.exe") or os.path.exists("/mnt/c/WINDOWS/System32/arp.exe"))
