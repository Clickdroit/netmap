import json
import os
from typing import Dict, Optional

STORE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "devices_store.json")

class DeviceStore:
    def __init__(self):
        self._data = {}
        self.load()

    def load(self):
        if os.path.exists(STORE_PATH):
            try:
                with open(STORE_PATH, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
            except Exception:
                self._data = {}
        else:
            self._data = {}

    def save(self):
        try:
            os.makedirs(os.path.dirname(STORE_PATH), exist_ok=True)
            with open(STORE_PATH, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[DeviceStore] Error saving: {e}")

    def get_customization(self, mac: str) -> Optional[Dict]:
        clean_mac = (mac or "").upper()
        return self._data.get(clean_mac)

    def set_customization(self, mac: str, custom_name: Optional[str] = None, notes: Optional[str] = None, custom_category: Optional[str] = None) -> Dict:
        clean_mac = (mac or "").upper()
        if not clean_mac:
            return {}
        if clean_mac not in self._data:
            self._data[clean_mac] = {}
        if custom_name is not None:
            self._data[clean_mac]["custom_name"] = custom_name.strip()
        if notes is not None:
            self._data[clean_mac]["notes"] = notes.strip()
        if custom_category is not None:
            self._data[clean_mac]["custom_category"] = custom_category.strip()
        self.save()
        return self._data[clean_mac]

    def apply_to_device(self, device: Dict) -> Dict:
        """Applies saved customization to a scanned device dictionary."""
        mac = (device.get("mac") or "").upper()
        custom = self.get_customization(mac)
        if custom:
            if custom.get("custom_name"):
                device["custom_name"] = custom["custom_name"]
                device["display_name"] = custom["custom_name"]
            if custom.get("notes"):
                device["notes"] = custom["notes"]
            if custom.get("custom_category"):
                device["custom_category"] = custom["custom_category"]
        if "display_name" not in device:
            device["display_name"] = device.get("hostname") or device.get("vendor") or device.get("ip")
        return device

device_store = DeviceStore()
