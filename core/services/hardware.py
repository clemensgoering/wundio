"""
Wundio – Hardware Detection & Feature Flags
Detects Raspberry Pi model and enables/disables features accordingly.

Tier mapping:
  Tier 1 Essential  – Pi 3B+ / Pi 4 (2 GB)   – Phases 0–3, Cloud AI on Pi 4+
  Tier 2 Standard   – Pi 4 (4 GB)             – All phases 0–3 stable, Cloud AI
  Tier 3 Full-Stack – Pi 5 (8 GB) + NVMe      – All phases + Local LLM
"""

import re
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# RAM thresholds (MB)
RAM_FOR_LOCAL_LLM  = 7000   # Pi 5 8 GB
RAM_FOR_CLOUD_AI   = 900    # Pi 4+ (≥ 1 GB usable)
RAM_FOR_ADV_GAMES  = 900    # Pi 4+


@dataclass
class HardwareProfile:
    model: str = "unknown"
    revision: str = "unknown"
    ram_mb: int = 0
    is_pi: bool = False
    pi_generation: int = 0   # 3, 4, 5

    # Resolved hardware config (from wundio.env via detect())
    rfid_type:  str = "rc522"   # "rc522" | "pn532"
    audio_type: str = "usb"     # "usb" | "i2s_max98357" | "hifiberry"

    # Feature flags
    feature_spotify:        bool = False
    feature_display_oled:   bool = False
    feature_rfid:           bool = False
    feature_buttons:        bool = False
    feature_ai_local:       bool = False
    feature_ai_cloud:       bool = False
    feature_games_advanced: bool = False

    # Tier label for UI / docs
    @property
    def tier(self) -> str:
        if self.pi_generation >= 5 and self.ram_mb >= RAM_FOR_LOCAL_LLM:
            return "full-stack"
        if self.pi_generation >= 4 and self.ram_mb >= RAM_FOR_CLOUD_AI:
            return "standard"
        return "essential"

    def to_dict(self) -> dict:
        return {
            "model":          self.model,
            "ram_mb":         self.ram_mb,
            "pi_generation":  self.pi_generation,
            "tier":           self.tier,
            "rfid_type":      self.rfid_type,
            "audio_type":     self.audio_type,
            "features": {
                "spotify":         self.feature_spotify,
                "display_oled":    self.feature_display_oled,
                "rfid":            self.feature_rfid,
                "buttons":         self.feature_buttons,
                "ai_local":        self.feature_ai_local,
                "ai_cloud":        self.feature_ai_cloud,
                "games_advanced":  self.feature_games_advanced,
            },
        }


# ── System reads ───────────────────────────────────────────────────────────────

def _read_model() -> str:
    for path in ("/proc/device-tree/model", "/sys/firmware/devicetree/base/model"):
        try:
            with open(path) as f:
                return f.read().strip().replace("\x00", "")
        except OSError:
            continue
    return "unknown"


def _read_ram_mb() -> int:
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    return int(line.split()[1]) // 1024
    except OSError:
        pass
    return 0


def _parse_generation(model: str) -> int:
    m = re.search(r"Raspberry Pi (\d+)", model, re.IGNORECASE)
    if m:
        return int(m.group(1))
    if "zero" in model.lower():
        return 1
    return 0


# ── Feature gating ─────────────────────────────────────────────────────────────

def _apply_feature_flags(profile: HardwareProfile) -> None:
    """
    Feature availability by tier:

    Essential  (Pi 3 / Pi 4 2GB):
      Phases 0–3: Spotify, RFID, Buttons, Display, Voice (Whisper tiny/small)
      Cloud AI: Pi 4 only
      Local LLM: ✗

    Standard (Pi 4 4GB):
      All Essential features
      Cloud AI: ✓
      Advanced Games: ✓
      Local LLM: ✗ (RAM insufficient, no NVMe)

    Full-Stack (Pi 5 8GB + NVMe):
      All Standard features
      Local LLM (Ollama llama3.2:3b): ✓
      Phase 4+5: ✓
    """
    # Base: all Pi models
    profile.feature_spotify      = True
    profile.feature_rfid         = True
    profile.feature_display_oled = True
    profile.feature_buttons      = True

    # Pi 4+ unlocks Cloud AI and Advanced Games
    if profile.pi_generation >= 4 and profile.ram_mb >= RAM_FOR_CLOUD_AI:
        profile.feature_ai_cloud        = True
        profile.feature_games_advanced  = True

    # Pi 5 + 8 GB unlocks Local LLM (NVMe check is runtime, not at detection)
    if profile.pi_generation >= 5 and profile.ram_mb >= RAM_FOR_LOCAL_LLM:
        profile.feature_ai_local = True


# ── Main detect ────────────────────────────────────────────────────────────────

def detect() -> HardwareProfile:
    profile = HardwareProfile()
    profile.model         = _read_model()
    profile.ram_mb        = _read_ram_mb()
    profile.is_pi         = "raspberry pi" in profile.model.lower()
    profile.pi_generation = _parse_generation(profile.model)

    # Read RFID and Audio type from config (set by installer)
    try:
        from config import get_settings
        cfg = get_settings()
        profile.rfid_type  = getattr(cfg, "rfid_type",  "rc522").lower()
        profile.audio_type = getattr(cfg, "audio_type", "usb").lower()
    except Exception:
        pass

    if not profile.is_pi:
        # Dev machine – enable all features except Local LLM
        logger.warning("Not running on Raspberry Pi – dev mode (all features except ai_local)")
        profile.feature_spotify      = True
        profile.feature_display_oled = True
        profile.feature_rfid         = True
        profile.feature_buttons      = True
        profile.feature_ai_cloud     = True
        profile.feature_games_advanced = True
        profile.feature_ai_local     = False
        return profile

    _apply_feature_flags(profile)

    logger.info(
        f"Hardware: {profile.model} | RAM: {profile.ram_mb} MB | "
        f"Gen: {profile.pi_generation} | Tier: {profile.tier} | "
        f"RFID: {profile.rfid_type} | Audio: {profile.audio_type}"
    )
    logger.info(f"Features: {profile.to_dict()['features']}")
    return profile


# ── Singleton ──────────────────────────────────────────────────────────────────

_profile: Optional[HardwareProfile] = None


def get_profile() -> HardwareProfile:
    global _profile
    if _profile is None:
        _profile = detect()
    return _profile