import socket
import time
import subprocess
import re
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor

from .platform_utils import is_windows

def send_wake_on_lan(mac: str, broadcast_ip: str = "255.255.255.255", port: int = 9) -> Dict:
    """
    Sends a Wake-on-LAN (WOL) Magic Packet to wake up a remote machine.
    Magic packet format: 6 bytes of 0xFF followed by 16 repetitions of target MAC.
    """
    clean_mac = re.sub(r'[^0-9A-Fa-f]', '', mac)
    if len(clean_mac) != 12:
        return {"success": False, "message": f"Adresse MAC invalide : {mac}"}

    mac_bytes = bytes.fromhex(clean_mac)
    magic_packet = b"\xff" * 6 + mac_bytes * 16

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.sendto(magic_packet, (broadcast_ip, port))
            # Also send to port 7 (echo) for maximum router compatibility
            sock.sendto(magic_packet, (broadcast_ip, 7))
        return {
            "success": True,
            "mac": mac,
            "message": f"Paquet magique Wake-on-LAN envoyé avec succès à {mac} !"
        }
    except Exception as e:
        return {"success": False, "message": f"Erreur lors de l'envoi du paquet WOL : {str(e)}"}

def ping_device_live(ip: str, count: int = 1) -> Dict:
    """
    Performs a live latency ping to the target IP.
    Returns round-trip time in milliseconds.
    """
    t0 = time.perf_counter()
    alive = False
    
    # Method 1: Socket connect on port 80/443/53/135
    for test_port in [80, 443, 135, 445, 53, 22]:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.3)
            res = s.connect_ex((ip, test_port))
            s.close()
            if res == 0:
                alive = True
                break
        except Exception:
            pass

    # Method 2: System ping fallback
    if not alive:
        try:
            ping_cmd = ["ping", "-n", "1", "-w", "500", ip] if is_windows() else ["ping", "-c", "1", "-W", "1", ip]
            res = subprocess.run(ping_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=1.0)
            alive = (res.returncode == 0)
        except Exception:
            pass

    rtt_ms = round((time.perf_counter() - t0) * 1000, 2)
    return {
        "ip": ip,
        "alive": alive,
        "rtt_ms": max(rtt_ms, 0.5) if alive else None,
        "timestamp": time.strftime("%H:%M:%S")
    }

def scan_custom_ports_range(ip: str, start_port: int = 1, end_port: int = 1024, max_workers: int = 50) -> List[Dict]:
    """
    Scans a specified port range on a single device on-demand.
    """
    start_port = max(1, min(start_port, 65535))
    end_port = max(start_port, min(end_port, 65535))
    
    open_ports = []
    
    def check(p):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.25)
                if s.connect_ex((ip, p)) == 0:
                    try:
                        svc = socket.getservbyport(p, "tcp")
                    except Exception:
                        svc = "Service TCP"
                    return {"port": p, "service": svc}
        except Exception:
            pass
        return None

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = executor.map(check, range(start_port, end_port + 1))
        for r in results:
            if r:
                open_ports.append(r)
                
    return sorted(open_ports, key=lambda x: x["port"])

def calculate_subnet_details(cidr: str) -> Dict:
    """
    Computes IPv4 subnet network address, netmask, broadcast, host ranges, and usable capacity.
    """
    import ipaddress
    try:
        net = ipaddress.IPv4Network(cidr, strict=False)
        hosts = list(net.hosts())
        return {
            "valid": True,
            "cidr": str(net),
            "network_address": str(net.network_address),
            "broadcast_address": str(net.broadcast_address),
            "netmask": str(net.netmask),
            "hostmask": str(net.hostmask),
            "prefixlen": net.prefixlen,
            "total_addresses": net.num_addresses,
            "usable_hosts": len(hosts),
            "first_host": str(hosts[0]) if hosts else str(net.network_address),
            "last_host": str(hosts[-1]) if hosts else str(net.broadcast_address)
        }
    except Exception as e:
        return {
            "valid": False,
            "cidr": cidr,
            "error": str(e)
        }

def benchmark_dns_servers(test_domain: str = "google.com") -> List[Dict]:
    """
    Benchmarks DNS resolution latency across major public DNS providers.
    """
    import time
    DNS_PROVIDERS = [
        {"name": "Cloudflare", "ip": "1.1.1.1"},
        {"name": "Google Public DNS", "ip": "8.8.8.8"},
        {"name": "Quad9", "ip": "9.9.9.9"},
        {"name": "OpenDNS", "ip": "208.67.222.222"},
    ]

    results = []
    for provider in DNS_PROVIDERS:
        t0 = time.perf_counter()
        success = False
        try:
            # Test direct UDP socket connection on DNS port 53
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.settimeout(1.0)
                s.connect((provider["ip"], 53))
                # Send minimal DNS query header for test_domain
                s.send(b"\xaa\xbb\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x06google\x03com\x00\x00\x01\x00\x01")
                resp = s.recv(512)
                if len(resp) > 0:
                    success = True
        except Exception:
            pass

        latency = round((time.perf_counter() - t0) * 1000, 2)
        results.append({
            "name": provider["name"],
            "ip": provider["ip"],
            "latency_ms": latency if success else None,
            "status": "ONLINE" if success else "TIMEOUT"
        })

    # Sort fastest first (putting None at the end)
    return sorted(results, key=lambda x: (x["latency_ms"] is None, x["latency_ms"] or 9999))

