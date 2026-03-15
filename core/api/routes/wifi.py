"""
Wundio – /api/wifi routes
Configures wpa_supplicant and triggers reconnect.
"""
import asyncio
import logging
import subprocess
from fastapi import APIRouter
from pydantic import BaseModel

from database import get_setting, set_setting, log_event

router = APIRouter(tags=["wifi"])
logger = logging.getLogger(__name__)

WPA_CONF = "/etc/wpa_supplicant/wpa_supplicant.conf"


class WifiConfig(BaseModel):
    ssid: str
    password: str
    country: str = "DE"


@router.post("/configure")
async def configure_wifi(cfg: WifiConfig):
    """
    Write wpa_supplicant.conf and reconnect.
    Called from the Web UI Settings page after the user provides SSID + password.
    """
    conf = f"""ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country={cfg.country}

network={{
    ssid="{cfg.ssid}"
    psk="{cfg.password}"
    key_mgmt=WPA-PSK
}}
"""
    try:
        with open(WPA_CONF, "w") as f:
            f.write(conf)

        # Reload – best effort, may fail in dev/mock mode
        subprocess.run(["wpa_cli", "-i", "wlan0", "reconfigure"], capture_output=True)
        set_setting("wifi_ssid",       cfg.ssid)
        set_setting("wifi_configured", "true")
        set_setting("hotspot_active",  "false")
        log_event("wifi", f"WiFi configured: {cfg.ssid}")
        return {"ok": True, "ssid": cfg.ssid}
    except OSError:
        # Running as non-root in dev mode
        log_event("wifi", f"WiFi mock configure: {cfg.ssid}", level="WARN")
        set_setting("wifi_ssid",       cfg.ssid)
        set_setting("wifi_configured", "true")
        return {"ok": True, "ssid": cfg.ssid, "note": "mock – no root access"}


@router.get("/status")
async def wifi_status():
    return {
        "configured": get_setting("wifi_configured") == "true",
        "ssid":       get_setting("wifi_ssid"),
        "hotspot":    get_setting("hotspot_active") == "true",
    }
