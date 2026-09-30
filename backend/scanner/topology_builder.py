from typing import List, Dict
from .device_store import device_store

def build_topology_graph(
    devices: List[Dict],
    gateway_ip: str,
    network_cidr: str,
    local_ip: str = None
) -> Dict:
    """
    Constructs the Vis.js compatible nodes and edges for the network topology.
    Supports Force-Directed, Hierarchical Tree, and Radial layouts.
    """
    nodes = []
    edges = []
    
    # 1. Add WAN / Internet Node
    nodes.append({
        "id": "node_internet",
        "label": "Internet\n(WAN)",
        "shape": "icon",
        "icon": {
            "face": "FontAwesome",
            "code": "\uf0c2",  # Cloud
            "size": 50,
            "color": "#38bdf8"
        },
        "color": {
            "background": "#0369a1",
            "border": "#38bdf8"
        },
        "group": "internet",
        "level": 0,
        "title": "Connexion Internet Externe"
    })

    # Find or create gateway node
    gateway_device = next((d for d in devices if d.get("is_gateway")), None)
    gateway_id = f"node_{gateway_ip.replace('.', '_')}" if gateway_ip else "node_gateway"
    
    gw_label = f"Passerelle / Routeur\n{gateway_ip}"
    if gateway_device:
        device_store.apply_to_device(gateway_device)
        d_name = gateway_device.get("display_name") or gateway_device.get("hostname")
        if d_name and d_name != "Appareil Inconnu":
            gw_label = f"{d_name}\n({gateway_ip})"
        
    nodes.append({
        "id": gateway_id,
        "label": gw_label,
        "shape": "icon",
        "icon": {
            "face": "FontAwesome",
            "code": "\uf233",  # Server / Router
            "size": 48,
            "color": "#3b82f6"
        },
        "color": {
            "background": "#1e3a8a",
            "border": "#60a5fa"
        },
        "group": "gateway",
        "level": 1,
        "device_info": gateway_device or {
            "ip": gateway_ip,
            "is_gateway": True,
            "category": "router",
            "vendor": "Passerelle Principale"
        },
        "title": f"Passerelle Réseau : {gateway_ip}"
    })

    # Edge WAN -> Gateway
    edges.append({
        "from": "node_internet",
        "to": gateway_id,
        "label": "WAN",
        "color": {"color": "#38bdf8", "highlight": "#67e8f9"},
        "dashes": False,
        "width": 3,
        "arrows": "to"
    })

    # FontAwesome icons lookup
    ICON_MAP = {
        "router": "\uf233",    # server/router
        "server": "\uf233",    # server
        "computer": "\uf108",  # desktop
        "mobile": "\uf3cd",    # mobile-alt
        "printer": "\uf02f",   # print
        "iot": "\uf2db",       # microchip
        "tv": "\uf26c",        # tv
        "console": "\uf11b",   # gamepad
        "unknown": "\uf6ff"    # network-wired
    }

    # 2. Add Device Nodes
    for dev in devices:
        ip = dev["ip"]
        if ip == gateway_ip:
            continue  # Gateway node already added
            
        # Apply user customization if any (custom name, notes)
        device_store.apply_to_device(dev)

        node_id = f"node_{ip.replace('.', '_')}"
        category = dev.get("category", "unknown")
        fa_code = ICON_MAP.get(category, "\uf6ff")
        color = dev.get("color", "#64748b")
        
        display_name = dev.get("display_name") or dev.get("hostname")
        if not display_name or display_name == "Appareil Inconnu":
            display_name = dev.get("vendor", ip)
            
        if len(display_name) > 18:
            display_name = display_name[:16] + "..."
                
        is_me = (ip == local_ip)
        label_text = f"{display_name}\n{ip}"
        if is_me:
            label_text = f"★ Mon PC ★\n{display_name}\n{ip}"

        nodes.append({
            "id": node_id,
            "label": label_text,
            "shape": "icon",
            "icon": {
                "face": "FontAwesome",
                "code": fa_code,
                "size": 38 if not is_me else 44,
                "color": "#ec4899" if is_me else color
            },
            "color": {
                "background": "#1e293b",
                "border": color
            },
            "group": category,
            "level": 2,
            "device_info": dev,
            "title": f"<b>{dev.get('display_name', 'Inconnu')}</b><br>IP: {ip}<br>MAC: {dev.get('mac')}<br>Fabricant: {dev.get('vendor')}"
        })

        # Edge from Gateway to Device
        latency_text = f"{dev.get('latency_ms', 1)} ms"
        edges.append({
            "from": gateway_id,
            "to": node_id,
            "label": latency_text,
            "color": {"color": "#475569", "highlight": "#38bdf8"},
            "width": 1.5 if not is_me else 2.5,
            "arrows": ""
        })

    return {
        "nodes": nodes,
        "edges": edges,
        "network_cidr": network_cidr,
        "gateway_ip": gateway_ip,
        "total_nodes": len(nodes),
        "total_edges": len(edges)
    }
