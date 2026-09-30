import socket
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict

COMMON_PORTS = {
    21: "FTP",
    22: "SSH",
    23: "Telnet",
    53: "DNS",
    80: "HTTP",
    135: "MSRPC",
    139: "NetBIOS",
    443: "HTTPS",
    445: "SMB",
    631: "IPP (Printer)",
    3389: "RDP",
    5000: "NAS / Web",
    8000: "HTTP Dev",
    8080: "HTTP Alt",
    8443: "HTTPS Alt",
    9100: "RAW Printer"
}

def check_port(ip: str, port: int, timeout: float = 0.4) -> bool:
    """Tries to connect to a specific TCP port."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            res = s.connect_ex((ip, port))
            return res == 0
    except Exception:
        return False

def scan_ports(ip: str, ports: List[int] = None, max_workers: int = 16, timeout: float = 0.35) -> List[Dict]:
    """Scans common TCP ports on the given IP address."""
    if ports is None:
        ports = list(COMMON_PORTS.keys())
        
    open_ports = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(check_port, ip, port, timeout): port for port in ports}
        for future in futures:
            port = futures[future]
            try:
                if future.result():
                    open_ports.append({
                        "port": port,
                        "service": COMMON_PORTS.get(port, "Unknown")
                    })
            except Exception:
                pass
                
    return sorted(open_ports, key=lambda x: x["port"])
