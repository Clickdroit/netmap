import socket
import subprocess
import json
import ipaddress
import re
import os
import shutil
from typing import Dict, List, Optional
from .platform_utils import is_windows, is_wsl, is_linux, get_powershell_cmd, has_windows_interop

def get_linux_interfaces() -> List[Dict]:
    """Detects interfaces on Linux using 'ip -j addr' and 'ip -j route'."""
    interfaces = []
    try:
        # Get routes
        routes_out = subprocess.check_output(["ip", "-j", "route"], text=True, stderr=subprocess.DEVNULL)
        routes = json.loads(routes_out) if routes_out.strip() else []
        default_gw = None
        default_dev = None
        for r in routes:
            if r.get("dst") == "default" and r.get("gateway"):
                default_gw = r.get("gateway")
                default_dev = r.get("dev")
                break

        # Get addresses
        addr_out = subprocess.check_output(["ip", "-j", "addr"], text=True, stderr=subprocess.DEVNULL)
        addrs = json.loads(addr_out) if addr_out.strip() else []
        
        for dev in addrs:
            ifname = dev.get("ifname", "")
            if ifname.startswith("lo") or dev.get("operstate") == "DOWN":
                continue
            for a in dev.get("addr_info", []):
                if a.get("family") == "inet" and not a.get("local", "").startswith("127."):
                    ip = a.get("local")
                    prefix = a.get("prefixlen", 24)
                    net = ipaddress.IPv4Network(f"{ip}/{prefix}", strict=False)
                    is_def = (ifname == default_dev)
                    gw = default_gw if is_def else None
                    
                    interfaces.append({
                        "alias": f"Linux ({ifname})",
                        "ip": ip,
                        "prefix": prefix,
                        "netmask": str(net.netmask),
                        "network_cidr": str(net),
                        "gateway": gw,
                        "total_hosts": net.num_addresses - 2 if net.num_addresses > 2 else 1,
                        "is_default": is_def,
                        "is_physical": not is_wsl()  # In WSL, eth0 is virtual NAT
                    })
    except Exception as e:
        print(f"[NetworkDetector] Linux detection error: {e}")
    return interfaces

def get_windows_interfaces_via_powershell(ps_cmd_name: str) -> List[Dict]:
    """Queries Windows interfaces via PowerShell (works on Windows and in WSL)."""
    interfaces = []
    try:
        ps_script = (
            "$ips = Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notlike '*Loopback*' -and $_.IPAddress -notlike '169.254*' }; "
            "$gws = Get-NetRoute -DestinationPrefix '0.0.0.0/0'; "
            "$res = foreach ($i in $ips) { "
            "  $gw = ($gws | Where-Object { $_.InterfaceAlias -eq $i.InterfaceAlias }).NextHop; "
            "  [PSCustomObject]@{ "
            "    Alias = $i.InterfaceAlias; "
            "    IP = $i.IPAddress; "
            "    Prefix = $i.PrefixLength; "
            "    Gateway = $gw "
            "  } "
            "}; "
            "$res | ConvertTo-Json -Compress"
        )
        
        cmd = [ps_cmd_name, "-NoProfile", "-Command", ps_script]
        output = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
        if output.strip():
            raw = json.loads(output.strip())
            items = raw if isinstance(raw, list) else [raw]
            for it in items:
                ip = it.get("IP")
                prefix = it.get("Prefix", 24)
                alias = it.get("Alias", "Adapter")
                gw = it.get("Gateway")
                if not ip or ip.startswith("169.254"):
                    continue
                try:
                    net = ipaddress.IPv4Network(f"{ip}/{prefix}", strict=False)
                    has_gw = bool(gw and gw != "0.0.0.0")
                    interfaces.append({
                        "alias": f"Hôte ({alias})" if is_wsl() else alias,
                        "ip": ip,
                        "prefix": prefix,
                        "netmask": str(net.netmask),
                        "network_cidr": str(net),
                        "gateway": gw if has_gw else None,
                        "total_hosts": net.num_addresses - 2 if net.num_addresses > 2 else 1,
                        "is_default": has_gw,
                        "is_physical": True
                    })
                except Exception:
                    pass
    except Exception as e:
        print(f"[NetworkDetector] PowerShell detection error: {e}")
    return interfaces

def get_network_interfaces() -> List[Dict]:
    """
    Returns active IPv4 network interfaces across Windows, WSL, and Linux.
    """
    interfaces = []
    
    # 1. If in WSL with Windows interop, query Windows host physical interfaces
    if has_windows_interop():
        ps_cmd = get_powershell_cmd()
        host_ifaces = get_windows_interfaces_via_powershell(ps_cmd)
        interfaces.extend(host_ifaces)
        
    # 2. If on pure Windows
    elif is_windows():
        interfaces.extend(get_windows_interfaces_via_powershell("powershell"))
        
    # 3. Linux interfaces (either pure Linux or WSL Linux eth0)
    if is_linux():
        linux_ifaces = get_linux_interfaces()
        # If in WSL, add Linux virtual interfaces with is_default=False so host physical LAN is prioritized
        if is_wsl() and interfaces:
            for l in linux_ifaces:
                l["is_default"] = False
        interfaces.extend(linux_ifaces)

    # 4. Fallback if nothing found
    if not interfaces:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            net = ipaddress.IPv4Network(f"{local_ip}/24", strict=False)
            interfaces.append({
                "alias": "Réseau Local par Défaut",
                "ip": local_ip,
                "prefix": 24,
                "netmask": "255.255.255.0",
                "network_cidr": str(net),
                "gateway": str(list(net.hosts())[-1]),
                "total_hosts": 254,
                "is_default": True,
                "is_physical": True
            })
        except Exception:
            pass

    return interfaces

def get_default_interface() -> Optional[Dict]:
    """Returns the primary interface (physical Wi-Fi/Ethernet LAN preferred)."""
    interfaces = get_network_interfaces()
    # First priority: is_default and is_physical
    for iface in interfaces:
        if iface.get("is_default") and iface.get("is_physical") and iface.get("gateway"):
            return iface
    # Second priority: any with gateway
    for iface in interfaces:
        if iface.get("gateway"):
            return iface
    return interfaces[0] if interfaces else None
