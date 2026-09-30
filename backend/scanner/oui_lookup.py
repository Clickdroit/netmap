import json
import os
import re
import urllib.request
from typing import Optional

CACHE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "oui_cache.json")

# Embedded database of major network vendors (OUI - first 3 octets)
POPULAR_OUIS = {
    # Apple
    "00:03:93": "Apple", "00:05:02": "Apple", "00:0A:27": "Apple", "00:0A:95": "Apple",
    "00:11:24": "Apple", "00:14:51": "Apple", "00:16:CB": "Apple", "00:17:F2": "Apple",
    "00:19:E3": "Apple", "00:1B:63": "Apple", "00:1C:B3": "Apple", "00:1D:4F": "Apple",
    "00:1E:52": "Apple", "00:1E:C2": "Apple", "00:1F:5B": "Apple", "00:1F:F3": "Apple",
    "00:21:E9": "Apple", "00:22:41": "Apple", "00:23:12": "Apple", "00:23:32": "Apple",
    "00:23:6C": "Apple", "00:24:36": "Apple", "00:25:00": "Apple", "00:25:4B": "Apple",
    "00:26:08": "Apple", "00:26:4A": "Apple", "00:26:B0": "Apple", "04:0C:CE": "Apple",
    "04:15:52": "Apple", "04:54:53": "Apple", "08:70:45": "Apple", "0C:4D:E9": "Apple",
    "10:40:F3": "Apple", "14:10:9F": "Apple", "18:AF:61": "Apple", "20:A2:E4": "Apple",
    "28:CF:E9": "Apple", "34:36:3B": "Apple", "38:F9:D3": "Apple", "3C:07:54": "Apple",
    "40:6C:8F": "Apple", "48:60:5F": "Apple", "50:BC:96": "Apple", "54:26:96": "Apple",
    "60:F8:1D": "Apple", "70:56:81": "Apple", "78:4F:43": "Apple", "80:EA:96": "Apple",
    "88:66:5A": "Apple", "90:72:40": "Apple", "98:01:A7": "Apple", "A4:83:E7": "Apple",
    "AC:BC:32": "Apple", "B8:78:2E": "Apple", "BC:FE:D9": "Apple", "C8:2A:14": "Apple",
    "D0:81:7A": "Apple", "DC:A9:04": "Apple", "E0:B9:BA": "Apple", "F0:18:98": "Apple",

    # Samsung
    "00:07:AB": "Samsung", "00:12:47": "Samsung", "00:15:99": "Samsung", "00:16:6C": "Samsung",
    "00:1A:8A": "Samsung", "00:21:4C": "Samsung", "08:D4:6A": "Samsung", "10:1C:0C": "Samsung",
    "14:89:FD": "Samsung", "18:67:B0": "Samsung", "24:F5:AA": "Samsung", "30:07:4D": "Samsung",
    "38:0B:40": "Samsung", "40:4E:36": "Samsung", "50:85:69": "Samsung", "58:C5:CB": "Samsung",
    "64:16:66": "Samsung", "78:47:1D": "Samsung", "84:25:DB": "Samsung", "90:18:7C": "Samsung",
    "A8:7B:39": "Samsung", "B4:F1:DA": "Samsung", "C4:73:1E": "Samsung", "CC:07:AB": "Samsung",

    # Google
    "00:1A:11": "Google", "3C:5A:B4": "Google", "54:60:09": "Google", "94:EB:CD": "Google",
    "A4:77:33": "Google", "D8:6C:63": "Google", "E4:F0:42": "Google", "F4:F5:E8": "Google",

    # Espressif (IoT)
    "18:FE:34": "Espressif (IoT)", "24:0A:C4": "Espressif (IoT)", "24:62:AB": "Espressif (IoT)",
    "24:6F:28": "Espressif (IoT)", "24:B2:DE": "Espressif (IoT)", "2C:3A:E8": "Espressif (IoT)",
    "30:AE:A4": "Espressif (IoT)", "3C:61:05": "Espressif (IoT)", "3C:71:BF": "Espressif (IoT)",
    "48:3F:DA": "Espressif (IoT)", "48:55:19": "Espressif (IoT)", "5C:CF:7F": "Espressif (IoT)",
    "68:C6:3A": "Espressif (IoT)", "84:0D:8E": "Espressif (IoT)", "84:F3:EB": "Espressif (IoT)",
    "A4:CF:12": "Espressif (IoT)", "AC:67:B2": "Espressif (IoT)", "B4:E6:2D": "Espressif (IoT)",
    "C4:4F:33": "Espressif (IoT)", "CC:50:E3": "Espressif (IoT)", "D8:A0:1D": "Espressif (IoT)",

    # Raspberry Pi
    "28:CD:C1": "Raspberry Pi", "B8:27:EB": "Raspberry Pi", "DC:A6:32": "Raspberry Pi", "E4:5F:01": "Raspberry Pi",

    # Intel
    "00:02:B3": "Intel", "00:03:47": "Intel", "00:04:23": "Intel", "00:0E:0C": "Intel",
    "00:13:02": "Intel", "00:13:E8": "Intel", "00:15:00": "Intel", "00:19:D1": "Intel",
    "00:1B:21": "Intel", "00:1D:E0": "Intel", "00:21:5C": "Intel", "00:23:14": "Intel",
    "34:13:E8": "Intel", "38:7A:0E": "Intel", "3C:F8:62": "Intel", "48:51:B7": "Intel", "68:05:CA": "Intel",
    "7C:B0:C2": "Intel", "80:86:F2": "Intel", "84:A9:3E": "Intel", "8C:85:90": "Intel",
    "A4:4C:C8": "Intel", "B4:96:91": "Intel", "C8:F7:50": "Intel", "D0:65:78": "Intel", "E8:D8:D1": "Intel",

    # Hewlett Packard Enterprise / Aruba
    "10:4F:58": "HP Enterprise / Aruba", "00:01:E6": "HP", "00:01:E7": "HP", "00:02:A5": "HP",
    "00:08:02": "HP", "00:0B:CD": "HP", "00:0E:7F": "HP", "00:10:83": "HP", "00:11:0A": "HP",

    # AzureWave
    "20:0B:74": "AzureWave", "50:2E:91": "AzureWave", "90:74:AE": "AzureWave",

    # Routers / Boxes FAI / Networking
    "00:07:CB": "Freebox (Free)", "14:0C:76": "Freebox (Free)", "34:27:92": "Freebox (Free)",
    "68:A3:78": "Freebox (Free)", "70:FC:8F": "Freebox (Free)", "F4:CA:E5": "Freebox (Free)",
    "00:1A:2B": "Orange (Livebox)", "74:85:2A": "Orange (Livebox)", "A4:3E:51": "Orange (Livebox)",
    "AC:84:C6": "Orange (Livebox)", "BC:F6:85": "Orange (Livebox)", "E8:F1:B0": "Orange (Livebox)",
    "E4:5D:51": "SFR Box", "E4:F4:C6": "SFR Box", "50:78:B3": "Bouygues Telecom", "E0:A1:D7": "Bouygues Telecom",
    
    # Cisco
    "00:00:0C": "Cisco", "00:01:42": "Cisco", "00:01:43": "Cisco", "00:01:63": "Cisco",
    "00:01:64": "Cisco", "00:01:96": "Cisco", "00:01:97": "Cisco", "00:01:C7": "Cisco",

    # TP-Link
    "00:1D:0F": "TP-Link", "14:CC:20": "TP-Link", "18:A6:F7": "TP-Link", "1C:3B:F3": "TP-Link",
    "30:B5:C2": "TP-Link", "50:C7:BF": "TP-Link", "60:32:B1": "TP-Link", "74:05:A5": "TP-Link",
    "78:83:C8": "TP-Link", "84:16:F9": "TP-Link", "98:48:27": "TP-Link", "A0:F3:C1": "TP-Link",
    "C0:25:E9": "TP-Link", "D8:0D:17": "TP-Link", "E8:48:B8": "TP-Link", "F4:EC:38": "TP-Link",

    # Ubiquiti
    "00:15:6D": "Ubiquiti", "00:27:22": "Ubiquiti", "04:18:D6": "Ubiquiti", "18:E8:29": "Ubiquiti",
    "24:5A:4C": "Ubiquiti", "44:D9:E7": "Ubiquiti", "68:72:51": "Ubiquiti", "70:A7:41": "Ubiquiti",

    # Synology / QNAP
    "00:11:32": "Synology NAS", "00:08:9B": "QNAP NAS", "24:5E:BE": "QNAP NAS",

    # Printers
    "00:00:85": "Canon", "00:1E:8F": "Canon", "00:2B:67": "Canon", "18:0C:AC": "Canon", "74:81:14": "Canon",
    "00:00:48": "Epson", "00:26:AB": "Epson", "44:D2:44": "Epson", "AC:18:26": "Epson",
    "00:80:77": "Brother", "00:1B:A9": "Brother", "30:05:5C": "Brother", "B4:99:BA": "Brother"
}

_disk_cache = None

def _get_cache() -> dict:
    global _disk_cache
    if _disk_cache is None:
        _disk_cache = {}
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    _disk_cache = json.load(f)
            except Exception:
                _disk_cache = {}
    return _disk_cache

def _save_cache():
    if _disk_cache is not None:
        try:
            os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(_disk_cache, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

def normalize_mac(mac: str) -> str:
    """Standardizes MAC address to XX:XX:XX:XX:XX:XX format."""
    clean = re.sub(r'[^0-9A-Fa-f]', '', mac).upper()
    if len(clean) == 12:
        return ':'.join(clean[i:i+2] for i in range(0, 12, 2))
    return mac.upper()

def fetch_online_oui(prefix: str) -> Optional[str]:
    """Queries online OUI database API with quick timeout and caches result."""
    clean_prefix = prefix.replace(":", "-")
    url = f"https://api.maclookup.app/v2/macs/{clean_prefix}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Net-Map/1.0"})
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            company = data.get("company")
            if company:
                return company.strip()
    except Exception:
        pass
    return None

def get_vendor(mac: str) -> str:
    """Returns the manufacturer name for a given MAC address."""
    if not mac:
        return "Inconnu"
        
    normalized = normalize_mac(mac)
    prefix_3 = normalized[:8]  # e.g. "00:11:22"
    
    # 1. Embedded fast lookup
    if prefix_3 in POPULAR_OUIS:
        return POPULAR_OUIS[prefix_3]
        
    # 2. Check randomized / private MAC addresses (bit 1 of first byte set)
    try:
        first_byte = int(normalized[:2], 16)
        if (first_byte & 0x02) != 0:
            return "Appareil Mobile (MAC Aléatoire)"
    except Exception:
        pass

    # 3. Disk cache
    cache = _get_cache()
    if prefix_3 in cache:
        return cache[prefix_3]

    # 4. Fallback online lookup
    online_vendor = fetch_online_oui(prefix_3)
    if online_vendor:
        cache[prefix_3] = online_vendor
        _save_cache()
        return online_vendor
        
    return "Fabricant non répertorié"
