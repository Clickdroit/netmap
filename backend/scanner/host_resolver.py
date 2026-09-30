import socket
import struct
from typing import Optional, Tuple

def resolve_dns(ip: str) -> Optional[str]:
    """Tries standard reverse DNS lookup."""
    try:
        hostname, _, _ = socket.gethostbyaddr(ip)
        if hostname and hostname != ip:
            return hostname
    except Exception:
        pass
    return None

def query_netbios_name(ip: str, timeout: float = 0.5) -> Tuple[Optional[str], Optional[str]]:
    """
    Sends an NBNS (NetBIOS Name Service) Node Status request on UDP port 137.
    Returns (computer_name, workgroup).
    Works on Windows PCs, Linux/Samba servers, NAS, etc.
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        
        # NetBIOS Node Status query for "*" (wildcard)
        # Encoded name for "*\x00..." -> "CKAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        # Header: Transaction ID 0x1337, Flags 0x0000, 1 Question, 0 Answers, 0 Auth, 0 Add
        header = b"\x13\x37\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00"
        query_name = b"\x20CKAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\x00"
        query_type_class = b"\x00\x21\x00\x01"  # Type NBSTAT (0x21), Class IN (0x01)
        packet = header + query_name + query_type_class
        
        sock.sendto(packet, (ip, 137))
        data, _ = sock.recvfrom(1024)
        sock.close()
        
        # Check if response has answers
        if len(data) > 56:
            # Number of names is at offset 56
            num_names = data[56]
            offset = 57
            computer_name = None
            workgroup = None
            
            for _ in range(num_names):
                if offset + 18 > len(data):
                    break
                raw_name = data[offset:offset+15].decode("ascii", errors="ignore").strip()
                name_type = data[offset+15]
                flags = struct.unpack(">H", data[offset+16:offset+18])[0]
                is_group = bool(flags & 0x8000)
                
                # Type 0x00: Workstation / Machine Name if unique, or Workgroup if group
                if name_type == 0x00:
                    if not is_group and not computer_name:
                        computer_name = raw_name
                    elif is_group and not workgroup:
                        workgroup = raw_name
                elif name_type == 0x20 and not computer_name:
                    # File Server Service
                    computer_name = raw_name
                    
                offset += 18
                
            return (computer_name, workgroup)
    except Exception:
        pass
        
    return (None, None)

def resolve_hostname(ip: str) -> dict:
    """Combines DNS and NetBIOS to get the cleanest possible device name."""
    nb_name, workgroup = query_netbios_name(ip)
    dns_name = resolve_dns(ip)
    
    primary_name = nb_name or dns_name or "Appareil Inconnu"
    return {
        "hostname": primary_name,
        "dns_name": dns_name,
        "netbios_name": nb_name,
        "workgroup": workgroup
    }
