import threading
import time
import asyncio
from typing import Dict, List, Optional, Callable

class NetworkMonitor:
    def __init__(self, scanner_instance, broadcast_fn: Optional[Callable] = None):
        self.scanner = scanner_instance
        self.broadcast_fn = broadcast_fn
        self.is_running = False
        self.interval = 45  # seconds
        self._thread = None
        self._stop_event = threading.Event()
        self.known_devices: Dict[str, dict] = {}  # mac -> device info
        self.alerts: List[dict] = []

    def set_broadcast_fn(self, fn: Callable):
        self.broadcast_fn = fn

    def start(self, interval: int = 45):
        if self.is_running:
            return
        self.interval = max(15, interval)
        self.is_running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        print(f"[NetworkMonitor] Surveillance active démarrée (intervalle: {self.interval}s)")

    def stop(self):
        if not self.is_running:
            return
        self.is_running = False
        self._stop_event.set()
        print("[NetworkMonitor] Surveillance réseau arrêtée")

    def _monitor_loop(self):
        # Initial run to populate known devices if empty
        if not self.known_devices and self.scanner.last_results.get("devices"):
            for d in self.scanner.last_results["devices"]:
                mac = (d.get("mac") or "").upper()
                if mac and mac != "00:00:00:00:00:00":
                    self.known_devices[mac] = d

        while not self._stop_event.is_set():
            try:
                # Fast background scan
                results = self.scanner.scan(do_port_scan=False)
                current_devices = results.get("devices", [])
                current_time = time.strftime("%H:%M:%S")

                # Check for new devices (Rogue / New Device Detection)
                new_arrivals = []
                for d in current_devices:
                    mac = (d.get("mac") or "").upper()
                    if not mac or mac in ("00:00:00:00:00:00", "INCONNU (ROUTÉ)"):
                        continue
                    
                    if mac not in self.known_devices:
                        # New device found!
                        self.known_devices[mac] = d
                        alert = {
                            "id": f"alert_{int(time.time()*1000)}",
                            "timestamp": current_time,
                            "type": "new_device",
                            "device": d,
                            "title": "Nouvel équipement détecté !",
                            "message": f"Appareil {d.get('ip')} ({d.get('hostname') or d.get('vendor')}) a rejoint le réseau."
                        }
                        self.alerts.append(alert)
                        new_arrivals.append(alert)

                # Broadcast live updates if new devices found
                if self.broadcast_fn:
                    if new_arrivals:
                        for al in new_arrivals:
                            self.broadcast_fn({
                                "step": "alert",
                                "alert": al
                            })
                    # Periodic heartbeat with current count
                    self.broadcast_fn({
                        "step": "monitor_tick",
                        "online_count": len(current_devices),
                        "total_known": len(self.known_devices),
                        "timestamp": current_time
                    })

            except Exception as e:
                print(f"[NetworkMonitor] Erreur durant la boucle de surveillance : {e}")

            # Sleep with interruptible event
            self._stop_event.wait(self.interval)
