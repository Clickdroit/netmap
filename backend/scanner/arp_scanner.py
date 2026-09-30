import subprocess
import socket
import ipaddress
import time
import re
import os
import shutil
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Optional, Callable

from .platform_utils import is_windows, is_wsl, is_linux

# On Windows: ctypes SendARP
SendARP = None
if is_windows():
    try:
        import ctypes
        import struct
        SendARP = ctypes.windll.iphlpapi.SendARP
    except Exception:
        SendARP = None

def get_mac_sendarp_windows(ip: str) -> Optional[str]:
    """Uses Windows SendARP API to query the MAC address directly."""
    if not SendARP:
        return None
    try:
        import ctypes
        import struct
        dest_ip = socket.inet_aton(ip)
        dest_ip_int = struct.unpack("<I", dest_ip)[0]
        mac_addr = (ctypes.c_byte * 6)()
        mac_len = ctypes.c_ulong(6)

        res = SendARP(dest_ip_int, 0, ctypes.byref(mac_addr), ctypes.byref(mac_len))
        if res == 0:
            mac_str = ":".join(f"{b & 0xFF:02X}" for b in mac_addr)
            if mac_str != "00:00:00:00:00:00":
                return mac_str
    except Exception:
        pass
    return None

def fast_socket_probe(ip: str) -> bool:
    """
    Pure Python socket probe (UDP NetBIOS 137 + TCP SYN 80)
    Runs in < 50ms without spawning any external process.
    Forces the operating system to send an ARP request and populate ARP cache.
    """
    alive = False
    # 1. Quick UDP probe
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.05)
        s.sendto(b"\x13\x37\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x20CKAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\x00\x00\x21\x00\x01", (ip, 137))
        s.close()
    except Exception:
        pass

    # 2. Quick TCP probe
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.05)
        res = s.connect_ex((ip, 80))
        if res == 0:
            alive = True
        s.close()
    except Exception:
        pass

    return alive

def get_wsl_host_arp_table() -> Dict[str, str]:
    """Reads host Windows ARP cache from inside WSL via arp.exe."""
    cache = {}
    arp_bin = shutil.which("arp.exe") or "/mnt/c/WINDOWS/System32/arp.exe"
    if not os.path.exists(arp_bin) and not shutil.which("arp.exe"):
        return cache
    try:
        out = subprocess.check_output([arp_bin, "-a"], text=True, stderr=subprocess.DEVNULL, errors="ignore")
        matches = re.findall(r'(\d+\.\d+\.\d+\.\d+)\s+([0-9a-fA-F]{2}[-:][0-9a-fA-F]{2}[-:][0-9a-fA-F]{2}[-:][0-9a-fA-F]{2}[-:][0-9a-fA-F]{2}[-:][0-9a-fA-F]{2})', out)
        for ip, mac in matches:
            clean_mac = mac.replace("-", ":").upper()
            if clean_mac not in ("00:00:00:00:00:00", "FF:FF:FF:FF:FF:FF") and not ip.startswith("224.") and not ip.startswith("239.") and not ip.endswith(".255"):
                cache[ip] = clean_mac
    except Exception as e:
        print(f"[WSL ARP] Error reading arp.exe: {e}")
    return cache

def get_linux_arp_table() -> Dict[str, str]:
    """Reads Linux /proc/net/arp and 'ip neigh'."""
    cache = {}
    if os.path.exists("/proc/net/arp"):
        try:
            with open("/proc/net/arp", "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()[1:]
                for line in lines:
                    parts = line.split()
                    if len(parts) >= 4:
                        ip = parts[0]
                        mac = parts[3].upper()
                        if mac != "00:00:00:00:00:00" and len(mac) == 17:
                            cache[ip] = mac
        except Exception:
            pass

    try:
        out = subprocess.check_output(["ip", "neigh"], text=True, stderr=subprocess.DEVNULL)
        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 5 and "lladdr" in parts:
                ip = parts[0]
                idx = parts.index("lladdr")
                if idx + 1 < len(parts):
                    mac = parts[idx + 1].upper()
                    if mac != "00:00:00:00:00:00" and len(mac) == 17:
                        cache[ip] = mac
    except Exception:
        pass
    return cache

def get_windows_arp_cache() -> Dict[str, str]:
    """Reads Windows ARP table."""
    cache = {}
    try:
        out = subprocess.check_output(["arp", "-a"], text=True, stderr=subprocess.DEVNULL)
        matches = re.findall(r'(\d+\.\d+\.\d+\.\d+)\s+([0-9a-fA-F]{2}[-:][0-9a-fA-F]{2}[-:][0-9a-fA-F]{2}[-:][0-9a-fA-F]{2}[-:][0-9a-fA-F]{2}[-:][0-9a-fA-F]{2})', out)
        for ip, mac in matches:
            clean_mac = mac.replace("-", ":").upper()
            if clean_mac not in ("00:00:00:00:00:00", "FF:FF:FF:FF:FF:FF") and not ip.startswith("224.") and not ip.startswith("239.") and not ip.endswith(".255"):
                cache[ip] = clean_mac
    except Exception:
        pass
    return cache

def probe_single_ip(ip: str) -> Optional[Dict]:
    """Probes a single IP address."""
    start_t = time.perf_counter()
    
    if is_windows() and SendARP:
        mac = get_mac_sendarp_windows(ip)
        latency_ms = round((time.perf_counter() - start_t) * 1000, 2)
        if mac:
            return {"ip": ip, "mac": mac, "latency_ms": max(latency_ms, 0.5)}
        return None
    else:
        # Linux or WSL: fast non-blocking socket probe
        alive = fast_socket_probe(ip)
        latency_ms = round((time.perf_counter() - start_t) * 1000, 2)
        return {"ip": ip, "mac": None, "alive": alive, "latency_ms": max(latency_ms, 0.5)}

def scan_network_arp(
    network_cidr: str,
    max_workers: int = 50,
    progress_callback: Optional[Callable[[int, int, str], None]] = None
) -> List[Dict]:
    """
    Scans the given network with parallel probes.
    Resolves MAC addresses across Windows, WSL, and native Linux.
    """
    try:
        net = ipaddress.IPv4Network(network_cidr, strict=False)
        hosts = [str(ip) for ip in net.hosts()]
    except Exception as e:
        print(f"[ARP Scanner] Invalid network {network_cidr}: {e}")
        return []

    total = len(hosts)
    discovered_map = {}
    completed = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(probe_single_ip, ip): ip for ip in hosts}
        for future in futures:
            completed += 1
            ip = futures[future]
            try:
                res = future.result()
                if res and (res.get("mac") or res.get("alive")):
                    discovered_map[ip] = res
                    if progress_callback:
                        progress_callback(completed, total, f"Sonde envoyée vers {ip}...")
                else:
                    if progress_callback and completed % 35 == 0:
                        progress_callback(completed, total, f"Balayage du sous-réseau... ({completed}/{total})")
            except Exception:
                pass

    # Collect ARP caches from appropriate OS sources
    arp_entries = {}
    if is_wsl():
        arp_entries.update(get_linux_arp_table())
        arp_entries.update(get_wsl_host_arp_table())
    elif is_linux():
        arp_entries.update(get_linux_arp_table())
    else:
        arp_entries.update(get_windows_arp_cache())

    # Merge MAC addresses and ARP cache into discovered hosts
    for ip, mac in arp_entries.items():
        try:
            if ipaddress.IPv4Address(ip) in net:
                if ip in discovered_map:
                    discovered_map[ip]["mac"] = mac
                else:
                    discovered_map[ip] = {
                        "ip": ip,
                        "mac": mac,
                        "latency_ms": 1.0
                    }
        except Exception:
            pass

    # Build final list of hosts having an IP and MAC
    results = []
    for ip, data in discovered_map.items():
        mac = data.get("mac")
        if mac:
            results.append({
                "ip": ip,
                "mac": mac,
                "latency_ms": data.get("latency_ms", 1.0)
            })

    # Sort numerically by IP
    results.sort(key=lambda d: ipaddress.IPv4Address(d["ip"]))
    return results
