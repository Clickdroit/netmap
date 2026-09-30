from typing import List, Dict

def classify_device(
    ip: str,
    mac: str,
    vendor: str,
    hostname: str,
    open_ports: List[Dict],
    is_gateway: bool = False
) -> Dict:
    """
    Classifies the device into a category (router, server, computer, mobile, printer, iot, tv, console)
    and determines an appropriate icon and label.
    """
    ports_set = {p["port"] for p in open_ports}
    vendor_lower = (vendor or "").lower()
    host_lower = (hostname or "").lower()
    
    # 1. Gateway / Router detection
    if is_gateway or any(k in vendor_lower for k in ["cisco", "tp-link", "netgear", "ubiquiti", "freebox", "orange", "livebox", "sfr box", "bouygues", "arcadyan", "sagemcom", "technicolor"]):
        if is_gateway or 53 in ports_set or "box" in host_lower or "router" in host_lower:
            return {
                "category": "router",
                "label": "Passerelle / Routeur",
                "icon": "router",
                "color": "#3b82f6"  # Blue
            }

    # 2. Printers
    if 9100 in ports_set or 631 in ports_set or any(k in vendor_lower for k in ["canon", "epson", "brother", "xerox", "ricoh"]) or ("hp" in vendor_lower and "print" in host_lower):
        return {
            "category": "printer",
            "label": "Imprimante Réseau",
            "icon": "printer",
            "color": "#10b981"  # Emerald
        }

    # 3. Gaming consoles
    if "playstation" in vendor_lower or "xbox" in vendor_lower or "nintendo" in vendor_lower or "ps5" in host_lower or "ps4" in host_lower or "xbox" in host_lower:
        return {
            "category": "console",
            "label": "Console de Jeux",
            "icon": "gamepad",
            "color": "#ec4899"  # Pink
        }

    # 4. Smart TV / Streaming
    if any(k in host_lower for k in ["tv", "bravia", "chromecast", "firetv", "appletv", "shield", "roku"]) or "smart tv" in vendor_lower or "sonos" in vendor_lower:
        return {
            "category": "tv",
            "label": "Smart TV / Multimédia",
            "icon": "tv",
            "color": "#8b5cf6"  # Purple
        }

    # 5. NAS & Servers
    if any(k in vendor_lower for k in ["synology", "qnap"]) or (22 in ports_set and (80 in ports_set or 443 in ports_set or 5000 in ports_set or 8080 in ports_set)):
        return {
            "category": "server",
            "label": "Serveur / NAS",
            "icon": "server",
            "color": "#f59e0b"  # Amber
        }

    # 6. Workstations / Computers (Windows / Mac / Linux PC)
    if 3389 in ports_set or 445 in ports_set or 139 in ports_set or 135 in ports_set or any(k in vendor_lower for k in ["dell", "lenovo", "acer", "msi", "asus", "microsoft"]):
        return {
            "category": "computer",
            "label": "Ordinateur / PC",
            "icon": "desktop",
            "color": "#06b6d4"  # Cyan
        }

    # 7. Mobile devices (Smartphone / Tablet)
    if "aléatoire" in vendor_lower or any(k in vendor_lower for k in ["samsung", "xiaomi", "huawei"]) or ("apple" in vendor_lower and not (445 in ports_set or 3389 in ports_set)):
        return {
            "category": "mobile",
            "label": "Smartphone / Tablette",
            "icon": "mobile",
            "color": "#a855f7"  # Purple-500
        }

    # 8. IoT / Embedded devices
    if "iot" in vendor_lower or "espressif" in vendor_lower or "philips hue" in vendor_lower or "raspberry" in vendor_lower or "tuya" in vendor_lower:
        return {
            "category": "iot",
            "label": "Objet Connecté (IoT)",
            "icon": "cpu",
            "color": "#14b8a6"  # Teal
        }

    # Default fallback
    return {
        "category": "unknown",
        "label": "Périphérique Réseau",
        "icon": "network",
        "color": "#64748b"  # Slate
    }
