import asyncio
import json
import csv
import io
import os
from typing import Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks, Response, Query
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.scanner import NetworkScanner
from backend.scanner.network_detector import get_network_interfaces, get_default_interface
from backend.scanner.diagnostics import (
    send_wake_on_lan, ping_device_live, scan_custom_ports_range,
    calculate_subnet_details, benchmark_dns_servers
)
from backend.scanner.device_store import device_store
from backend.scanner.monitor import NetworkMonitor

app = FastAPI(title="Net-Map", description="Network Scanner, Topology Mapper & Surveillance", version="1.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

scanner = NetworkScanner()
connected_websockets = set()
is_scanning = False
main_loop = None

def broadcast_sync(message: dict):
    """Bridge for background threads to broadcast to WebSocket clients."""
    if main_loop and connected_websockets:
        asyncio.run_coroutine_threadsafe(broadcast_ws(message), main_loop)

monitor = NetworkMonitor(scanner_instance=scanner, broadcast_fn=broadcast_sync)

class ScanRequest(BaseModel):
    network_cidr: Optional[str] = None
    gateway_ip: Optional[str] = None
    do_port_scan: bool = True

class CustomizeDeviceRequest(BaseModel):
    custom_name: Optional[str] = None
    notes: Optional[str] = None
    custom_category: Optional[str] = None

class MonitorConfigRequest(BaseModel):
    enabled: bool
    interval: int = 45

async def broadcast_ws(message: dict):
    """Sends JSON update to all connected WebSocket clients."""
    if not connected_websockets:
        return
    dead = set()
    for ws in list(connected_websockets):
        try:
            await ws.send_json(message)
        except Exception:
            dead.add(ws)
    for ws in dead:
        connected_websockets.discard(ws)

def run_scan_worker(cidr: Optional[str], gw: Optional[str], port_scan: bool, loop: asyncio.AbstractEventLoop):
    global is_scanning
    is_scanning = True

    def progress_cb(update: dict):
        asyncio.run_coroutine_threadsafe(broadcast_ws(update), loop)

    try:
        scanner.scan(
            network_cidr=cidr,
            gateway_ip=gw,
            do_port_scan=port_scan,
            progress_callback=progress_cb
        )
    finally:
        is_scanning = False

@app.on_event("startup")
async def startup_event():
    global main_loop
    main_loop = asyncio.get_running_loop()

# --- Network & Scan APIs ---
@app.get("/api/network/interfaces")
def get_interfaces():
    return {
        "interfaces": get_network_interfaces(),
        "default": get_default_interface()
    }

@app.get("/api/scan/status")
def get_status():
    return {
        "is_scanning": is_scanning,
        "is_monitoring": monitor.is_running,
        "monitor_interval": monitor.interval,
        "results": scanner.last_results
    }

@app.post("/api/scan/start")
async def start_scan(req: ScanRequest, background_tasks: BackgroundTasks):
    global is_scanning
    if is_scanning:
        return {"status": "busy", "message": "Un scan est déjà en cours."}

    loop = asyncio.get_running_loop()
    background_tasks.add_task(run_scan_worker, req.network_cidr, req.gateway_ip, req.do_port_scan, loop)
    return {"status": "started", "message": "Scan démarré"}

@app.get("/api/topology")
def get_topology():
    return scanner.last_results.get("topology", {})

@app.get("/api/devices")
def get_devices(category: Optional[str] = None, q: Optional[str] = None):
    devices = scanner.last_results.get("devices", [])
    if category and category != "all":
        devices = [d for d in devices if d.get("category") == category]
    if q:
        query = q.lower()
        devices = [
            d for d in devices
            if query in d.get("ip", "").lower()
            or query in d.get("mac", "").lower()
            or query in (d.get("display_name") or d.get("hostname") or "").lower()
            or query in d.get("vendor", "").lower()
        ]
    return {"devices": devices, "total": len(devices)}

# --- Diagnostics APIs (WOL, Live Ping, On-Demand Port Scan) ---
@app.post("/api/device/{mac}/wol")
def trigger_wol(mac: str):
    """Sends Wake-on-LAN magic packet to specified MAC."""
    return send_wake_on_lan(mac)

@app.get("/api/device/{ip}/ping")
def get_device_live_ping(ip: str):
    """Pings a device in real-time to measure latency and availability."""
    return ping_device_live(ip)

@app.get("/api/device/{ip}/scan-ports")
def scan_device_ports(ip: str, start: int = Query(1, ge=1, le=65535), end: int = Query(1024, ge=1, le=65535)):
    """Deep on-demand port scan for a selected device."""
    open_ports = scan_custom_ports_range(ip, start_port=start, end_port=end)
    return {"ip": ip, "start": start, "end": end, "open_ports": open_ports, "total_open": len(open_ports)}

@app.get("/api/diagnostics/dns-benchmark")
def get_dns_benchmark():
    """Benchmarks DNS query response times across major public DNS servers."""
    results = benchmark_dns_servers()
    return {"benchmark": results, "total": len(results)}

@app.get("/api/diagnostics/subnet-calculator")
def get_subnet_calculation(cidr: str = Query("192.168.1.0/24", description="CIDR network notation")):
    """Calculates network range, mask, broadcast and capacity for a CIDR subnet."""
    return calculate_subnet_details(cidr)


# --- Device Customization APIs ---
@app.post("/api/device/{mac}/customize")
def customize_device(mac: str, req: CustomizeDeviceRequest):
    """Saves user custom name and notes for a device."""
    res = device_store.set_customization(
        mac=mac,
        custom_name=req.custom_name,
        notes=req.notes,
        custom_category=req.custom_category
    )
    # Update active results in-memory
    for d in scanner.last_results.get("devices", []):
        if (d.get("mac") or "").upper() == mac.upper():
            device_store.apply_to_device(d)
    return {"status": "saved", "customization": res}

# --- Surveillance & Rogue Device Alerts APIs ---
@app.post("/api/monitor/toggle")
def toggle_monitor(req: MonitorConfigRequest):
    """Starts or stops continuous background network surveillance."""
    if req.enabled:
        monitor.start(interval=req.interval)
        return {"status": "started", "interval": monitor.interval, "message": "Surveillance active"}
    else:
        monitor.stop()
        return {"status": "stopped", "message": "Surveillance arrêtée"}

@app.get("/api/monitor/alerts")
def get_alerts():
    """Returns list of security alerts (rogue devices, new arrivals)."""
    return {"alerts": monitor.alerts, "total": len(monitor.alerts)}

@app.delete("/api/monitor/alerts")
def clear_alerts():
    """Clears alert list."""
    monitor.alerts.clear()
    return {"status": "cleared"}

# --- Export APIs ---
@app.get("/api/export/json")
def export_json():
    return Response(
        content=json.dumps(scanner.last_results, indent=2, ensure_ascii=False),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=netmap_export.json"}
    )

@app.get("/api/export/csv")
def export_csv():
    devices = scanner.last_results.get("devices", [])
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["IP", "MAC", "Nom Personnalise", "Nom d'hote", "Fabricant", "Categorie", "OS Estime", "Ports Ouverts", "Latence (ms)", "Notes"])
    for d in devices:
        ports_str = ", ".join([f"{p['port']}/{p['service']}" for p in d.get("open_ports", [])])
        writer.writerow([
            d.get("ip"),
            d.get("mac"),
            d.get("custom_name", ""),
            d.get("hostname"),
            d.get("vendor"),
            d.get("category_label"),
            d.get("os_info", {}).get("os_name", "Inconnu"),
            ports_str,
            d.get("latency_ms"),
            d.get("notes", "")
        ])
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=netmap_devices.csv"}
    )

@app.get("/api/export/markdown")
def export_markdown():
    devices = scanner.last_results.get("devices", [])
    gateway = scanner.last_results.get("gateway", {})
    md = [
        "# ?? Net-Map Network Inventory & Audit Report",
        f"- **Network CIDR:** {scanner.last_results.get('network_cidr', 'N/A')}",
        f"- **Gateway:** {gateway.get('ip', 'N/A')} ({gateway.get('vendor', 'N/A')})",
        f"- **Total Devices Discovered:** {len(devices)}\n",
        "| IP | MAC | Hostname / Display | Vendor | Category | Open Ports |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |"
    ]
    for d in devices:
        name = d.get("custom_name") or d.get("hostname") or "Unknown"
        ports = ", ".join([str(p['port']) for p in d.get("open_ports", [])]) or "None"
        md.append(f"| `{d.get('ip')}` | `{d.get('mac')}` | {name} | {d.get('vendor', 'N/A')} | {d.get('category_label', 'N/A')} | {ports} |")

    return Response(
        content="\n".join(md),
        media_type="text/markdown",
        headers={"Content-Disposition": "attachment; filename=netmap_report.md"}
    )


# --- WebSocket Stream ---
@app.websocket("/ws/scan")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_websockets.add(websocket)
    try:
        await websocket.send_json({
            "step": "status",
            "is_scanning": is_scanning,
            "is_monitoring": monitor.is_running,
            "alerts_count": len(monitor.alerts),
            "last_results": scanner.last_results
        })
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        connected_websockets.discard(websocket)
    except Exception:
        connected_websockets.discard(websocket)

# Static files
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
