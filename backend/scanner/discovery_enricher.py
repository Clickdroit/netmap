import socket
import re
import urllib.request
import ssl
from typing import Dict, Optional, Tuple

# Ignore SSL verification for local device self-signed certificates
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

def fetch_http_banner(ip: str, port: int, timeout: float = 1.0) -> Optional[Dict]:
    """
    Connects to HTTP/HTTPS service on target IP and extracts:
    - HTML <title>
    - Web Server header (nginx, Apache, lighttpd, etc.)
    """
    protocol = "https" if port in (443, 8443) else "http"
    url = f"{protocol}://{ip}:{port}/"
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) NetMap/1.0",
                "Accept": "text/html,application/xhtml+xml,*/*"
            }
        )
        with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as resp:
            server_header = resp.headers.get("Server", "").strip()
            # Read first 8KB to find title
            content = resp.read(8192).decode("utf-8", errors="ignore")
            title_match = re.search(r"<title[^>]*>([^<]+)</title>", content, re.IGNORECASE)
            title = title_match.group(1).strip() if title_match else None
            
            if title or server_header:
                return {
                    "url": url,
                    "title": title,
                    "server": server_header
                }
    except Exception:
        pass
    return None

def query_ssdp_device(ip: str, timeout: float = 0.5) -> Optional[str]:
    """
    Sends a targeted SSDP M-SEARCH query to unicast IP on port 1900.
    Returns device friendly name or server string if available.
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        msearch = (
            "M-SEARCH * HTTP/1.1\r\n"
            "HOST: 239.255.255.250:1900\r\n"
            "MAN: \"ssdp:discover\"\r\n"
            "MX: 1\r\n"
            "ST: ssdp:all\r\n\r\n"
        ).encode("utf-8")
        sock.sendto(msearch, (ip, 1900))
        data, _ = sock.recvfrom(2048)
        sock.close()
        text = data.decode("utf-8", errors="ignore")
        server_match = re.search(r"SERVER:\s*([^\r\n]+)", text, re.IGNORECASE)
        if server_match:
            return server_match.group(1).strip()
    except Exception:
        pass
    return None

def detect_os_from_ttl(ttl: int) -> Dict[str, str]:
    """
    Deduces approximate Operating System from IP TTL value:
    - 64 (or <= 64): Linux / Android / macOS / iOS
    - 128 (65 to 128): Windows
    - 255 (> 128): Cisco / Routers / Solaris
    """
    if ttl <= 0:
        return {"os_name": "Inconnu", "os_icon": "fa-question"}
    if ttl <= 64:
        return {"os_name": "Linux / Android / macOS", "os_icon": "fa-brands fa-linux"}
    elif ttl <= 128:
        return {"os_name": "Windows OS", "os_icon": "fa-brands fa-windows"}
    else:
        return {"os_name": "Équipement Réseau (Routeur/Cisco)", "os_icon": "fa-solid fa-server"}

def get_ip_ttl(ip: str, timeout: float = 0.4) -> Optional[int]:
    """Pings or connects to obtain IP packet TTL."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((ip, 80))
        ttl = s.getsockopt(socket.IPPROTO_IP, socket.IP_TTL)
        s.close()
        return ttl
    except Exception:
        pass
    return None

def enrich_device_fingerprint(ip: str, open_ports: list) -> Dict:
    """
    Combines HTTP banner grabbing, SSDP UPnP queries, and TTL analysis.
    """
    http_banners = []
    ports_num = [p.get("port") for p in open_ports if isinstance(p, dict)]
    
    # Try web ports for title grabbing
    web_ports = [p for p in (80, 443, 8080, 5000, 8443, 8000) if p in ports_num]
    for port in web_ports[:2]:  # Test max 2 web ports for speed
        banner = fetch_http_banner(ip, port)
        if banner:
            http_banners.append(banner)
            
    # SSDP check
    ssdp_info = query_ssdp_device(ip)

    # TTL analysis
    ttl = get_ip_ttl(ip)
    os_info = detect_os_from_ttl(ttl) if ttl else {"os_name": "Non déterminé", "os_icon": "fa-laptop"}

    return {
        "http_banners": http_banners,
        "ssdp_info": ssdp_info,
        "ttl": ttl,
        "os_info": os_info
    }
