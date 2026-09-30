import time
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Optional, Callable

from .network_detector import get_network_interfaces, get_default_interface
from .arp_scanner import scan_network_arp
from .oui_lookup import get_vendor
from .host_resolver import resolve_hostname
from .port_scanner import scan_ports
from .device_classifier import classify_device
from .topology_builder import build_topology_graph
from .discovery_enricher import enrich_device_fingerprint
from .device_store import device_store

class NetworkScanner:
    def __init__(self):
        self.last_results = {
            "devices": [],
            "topology": {},
            "network_info": {},
            "scan_time": None,
            "status": "idle"
        }

    def enrich_host(self, host: Dict, gateway_ip: str, do_port_scan: bool = True) -> Dict:
        """Enriches basic host info with hostname, vendor, ports, fingerprinting, and classification."""
        ip = host["ip"]
        mac = host["mac"]
        is_gateway = (ip == gateway_ip)

        # 1. Vendor
        vendor = get_vendor(mac)

        # 2. Hostname
        host_info = resolve_hostname(ip)
        hostname = host_info["hostname"]

        # 3. Ports
        open_ports = []
        if do_port_scan:
            open_ports = scan_ports(ip, timeout=0.35)

        # 4. Fingerprinting (HTTP page title, SSDP, TTL OS)
        fingerprint = enrich_device_fingerprint(ip, open_ports)

        # Check if HTTP banner title gives a better name (e.g. "Freebox OS", "Synology DSM")
        if fingerprint.get("http_banners") and (not hostname or hostname == "Appareil Inconnu"):
            first_title = fingerprint["http_banners"][0].get("title")
            if first_title and len(first_title) < 40 and not any(bad in first_title.lower() for bad in ["index of", "404", "error", "untitled"]):
                hostname = first_title

        # 5. Classification
        classification = classify_device(
            ip=ip,
            mac=mac,
            vendor=vendor,
            hostname=hostname,
            open_ports=open_ports,
            is_gateway=is_gateway
        )

        dev_data = {
            "ip": ip,
            "mac": mac,
            "latency_ms": host.get("latency_ms", 1.0),
            "vendor": vendor,
            "hostname": hostname,
            "dns_name": host_info.get("dns_name"),
            "netbios_name": host_info.get("netbios_name"),
            "workgroup": host_info.get("workgroup"),
            "open_ports": open_ports,
            "http_banners": fingerprint.get("http_banners", []),
            "ssdp_info": fingerprint.get("ssdp_info"),
            "ttl": fingerprint.get("ttl"),
            "os_info": fingerprint.get("os_info", {"os_name": "Inconnu", "os_icon": "fa-laptop"}),
            "is_gateway": is_gateway,
            "category": classification["category"],
            "category_label": classification["label"],
            "icon": classification["icon"],
            "color": classification["color"]
        }

        # 6. Apply user customization (custom name, notes, etc.)
        device_store.apply_to_device(dev_data)
        return dev_data

    def scan(
        self,
        network_cidr: Optional[str] = None,
        gateway_ip: Optional[str] = None,
        do_port_scan: bool = True,
        progress_callback: Optional[Callable[[dict], None]] = None
    ) -> Dict:
        """Runs a complete network discovery and builds topology."""
        start_time = time.time()
        self.last_results["status"] = "scanning"

        # Detect default network if not provided
        if not network_cidr or not gateway_ip:
            default_iface = get_default_interface()
            if default_iface:
                network_cidr = network_cidr or default_iface["network_cidr"]
                gateway_ip = gateway_ip or default_iface["gateway"]
                local_ip = default_iface["ip"]
            else:
                network_cidr = network_cidr or "192.168.1.0/24"
                gateway_ip = gateway_ip or "192.168.1.1"
                local_ip = "127.0.0.1"
        else:
            default_iface = get_default_interface()
            local_ip = default_iface["ip"] if default_iface else None

        if progress_callback:
            progress_callback({
                "step": "arp_scan",
                "progress": 10,
                "message": f"Démarrage du scan ARP/Sockets sur {network_cidr}..."
            })

        # Step 1: Fast ARP / Probe Scan
        raw_hosts = scan_network_arp(
            network_cidr=network_cidr,
            max_workers=50,
            progress_callback=lambda cur, tot, msg: progress_callback({
                "step": "arp_scan",
                "progress": int(10 + (cur / max(tot, 1)) * 40),
                "message": msg
            }) if progress_callback else None
        )

        if progress_callback:
            progress_callback({
                "step": "enrichment",
                "progress": 55,
                "message": f"{len(raw_hosts)} appareils détectés. Analyse des services, empreintes et constructeurs..."
            })

        # Step 2: Concurrent host enrichment (DNS, NetBIOS, Ports, Fingerprinting)
        enriched_devices = []
        total_hosts = len(raw_hosts)
        processed = 0

        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_host = {
                executor.submit(self.enrich_host, h, gateway_ip, do_port_scan): h
                for h in raw_hosts
            }
            for future in future_to_host:
                processed += 1
                try:
                    res = future.result()
                    enriched_devices.append(res)
                    if progress_callback:
                        progress_callback({
                            "step": "enrichment",
                            "progress": int(55 + (processed / max(total_hosts, 1)) * 35),
                            "message": f"Identifié : {res['ip']} ({res.get('display_name') or res['hostname']})"
                        })
                except Exception as e:
                    print(f"Error enriching host: {e}")

        # Sort enriched devices by IP
        import ipaddress
        enriched_devices.sort(key=lambda d: ipaddress.IPv4Address(d["ip"]))

        if progress_callback:
            progress_callback({
                "step": "topology",
                "progress": 95,
                "message": "Génération de la cartographie réseau interactive..."
            })

        # Step 3: Build Topology
        topology = build_topology_graph(
            devices=enriched_devices,
            gateway_ip=gateway_ip,
            network_cidr=network_cidr,
            local_ip=local_ip
        )

        elapsed = round(time.time() - start_time, 2)
        
        results = {
            "devices": enriched_devices,
            "topology": topology,
            "network_info": {
                "network_cidr": network_cidr,
                "gateway_ip": gateway_ip,
                "local_ip": local_ip,
                "total_devices": len(enriched_devices),
                "duration_seconds": elapsed
            },
            "scan_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "status": "completed"
        }

        self.last_results = results

        if progress_callback:
            progress_callback({
                "step": "done",
                "progress": 100,
                "message": f"Scan terminé en {elapsed}s ! {len(enriched_devices)} appareils cartographiés.",
                "results": results
            })

        return results
