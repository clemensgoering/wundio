"""
tests/phase0/test_hardware.py – Hardware profile detection and feature-gating.
"""
import pytest


class TestHardwareProfile:
    def test_dev_machine_has_all_features_except_ai_local(self):
        from services.hardware import detect
        profile = detect()
        if profile.is_pi:
            pytest.skip("Running on actual Pi – dev-machine test not applicable")
        assert profile.feature_spotify is True
        assert profile.feature_rfid is True
        assert profile.feature_ai_local is False

    @pytest.mark.parametrize("gen,ram,expect_cloud", [
        (3, 1024, False),
        (4, 2048, True),
        (4, 4096, True),
        (5, 8192, True),
    ])
    def test_cloud_ai_gating(self, gen, ram, expect_cloud):
        from services.hardware import HardwareProfile, _apply_feature_flags
        p = HardwareProfile(
            model=f"Raspberry Pi {gen}", ram_mb=ram,
            is_pi=True, pi_generation=gen,
        )
        _apply_feature_flags(p)
        assert p.feature_ai_cloud == expect_cloud

    @pytest.mark.parametrize("gen,ram,expected_tier", [
        (3, 1024,  "essential"),
        (4, 2048,  "standard"),
        (4, 4096,  "standard"),
        (5, 4096,  "standard"),
        (5, 8192,  "full-stack"),
    ])
    def test_tier_labels(self, gen, ram, expected_tier):
        from services.hardware import HardwareProfile
        p = HardwareProfile(
            model=f"Raspberry Pi {gen}", ram_mb=ram,
            is_pi=True, pi_generation=gen,
        )
        assert p.tier == expected_tier

    def test_rfid_type_defaults_to_rc522(self):
        from services.hardware import HardwareProfile
        assert HardwareProfile().rfid_type == "rc522"

    def test_audio_type_defaults_to_usb(self):
        from services.hardware import HardwareProfile
        assert HardwareProfile().audio_type == "usb"