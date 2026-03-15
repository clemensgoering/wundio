"""
Wundio – Hardware Detection & Feature Flags
Detects Raspberry Pi model and enables/disables features accordingly.
"""

import os
import re
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# RAM thresholds in MB
RAM_FOR_LOCAL_LLM = 7000   # ~8GB Pi 5
RAM_FOR_CLOUD_AI  = 900    # Pi 4+ (min 1GB usable)


@dataclass
class HardwareProfile:
    model: str = "unknown"
    revision: str = "unknown"
    ram_mb: int = 0
    is_pi: bool = False
    pi_generation: int = 0  # 3, 4, 5 ...

    # Feature flags – set by detect()
    feature_spotify: bool = False
    feature_display_oled: bool = False
    feature_rfid: bool = False
    feature_buttons: bool = False
    feature_ai_local: bool = False
    feature_ai_cloud: bool = False
    feature_games_advanced: bool = False

    def to_dict(self) -> dict:
        return {
            "model": self.model,
            "ram_mb": self.ram_mb,
            "pi_generation": self.pi_generation,
            "features": {
                "spotify": self.feature_spotify,
                "display_oled": self.feature_display_oled,
                "rfid": self.feature_rfid,
                "buttons": self.feature_buttons,
                "ai_local": self.feature_ai_local,
                "ai_cloud": self.feature_ai_cloud,
                "games_advanced": self.feature_games_advanced,
            }
        }


def _read_model() -> str:
    paths = [
        "/proc/device-tree/model",
        "/sys/firmware/devicetree/base/model",
    ]
    for path in paths:
        try:
            with open(path, "r") as f:
                return f.read().strip().replace("\x00", "")
        except OSError:
            continue
    return "unknown"


def _read_ram_mb() -> int:
    try:
        with open("/proc/meminfo", "r") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    return int(line.split()[1]) // 1024
    except OSError:
        pass
    return 0


def _parse_generation(model: str) -> int:
    """Extract Pi generation number from model string."""
    m = re.search(r"Raspberry Pi (\d+)", model, re.IGNORECASE)
    if m:
        return int(m.group(1))
    if "zero" in model.lower():
        return 1
    return 0


def detect() -> HardwareProfile:
    profile = HardwareProfile()
    profile.model = _read_model()
    profile.ram_mb = _read_ram_mb()
    profile.is_pi = "raspberry pi" in profile.model.lower()
    profile.pi_generation = _parse_generation(profile.model)

    if not profile.is_pi:
        # Running on dev machine – enable all for local testing
        logger.warning("Not running on Raspberry Pi – enabling all features for dev mode.")
        profile.feature_spotify = True
        profile.feature_display_oled = True
        profile.feature_rfid = True
        profile.feature_buttons = True
        profile.feature_ai_local = False   # still off, needs Ollama
        profile.feature_ai_cloud = True
        profile.feature_games_advanced = True
        return profile

    # Always available on any Pi
    profile.feature_spotify = True
    profile.feature_display_oled = True
    profile.feature_rfid = True
    profile.feature_buttons = True

    # Pi 4+ gets advanced games and cloud AI
    if profile.pi_generation >= 4:
        profile.feature_games_advanced = True
        profile.feature_ai_cloud = True

    # Pi 5 with 8GB gets local LLM
    if profile.pi_generation >= 5 and profile.ram_mb >= RAM_FOR_LOCAL_LLM:
        profile.feature_ai_local = True

    logger.info(f"Hardware detected: {profile.model} | RAM: {profile.ram_mb}MB | Gen: {profile.pi_generation}")
    logger.info(f"Features: {profile.to_dict()['features']}")

    return profile


# Singleton – resolved once at startup
_profile: Optional[HardwareProfile] = None


def get_profile() -> HardwareProfile:
    global _profile
    if _profile is None:
        _profile = detect()
    return _profile
