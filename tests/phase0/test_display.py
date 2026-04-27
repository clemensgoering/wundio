"""
Display service tests – factory pattern, all three drivers, fallback behaviour.
"""


class TestDisplay:
    """Tests for the display factory and all three display drivers."""

    # ── Factory ───────────────────────────────────────────────────────────────

    def test_factory_none_returns_null_display(self, monkeypatch):
        """DISPLAY_TYPE=none → NullDisplay, no hardware imports attempted."""
        import services.display as dm
        from unittest.mock import MagicMock

        mock_cfg = MagicMock()
        mock_cfg.display_type = "none"
        monkeypatch.setattr(dm, "get_settings", lambda: mock_cfg)
        dm._display = None

        d = dm.get_display()
        assert isinstance(d, dm.NullDisplay)

    def test_factory_empty_returns_null_display(self, monkeypatch):
        """DISPLAY_TYPE='' (unset) → NullDisplay."""
        import services.display as dm
        from unittest.mock import MagicMock

        mock_cfg = MagicMock()
        mock_cfg.display_type = ""
        monkeypatch.setattr(dm, "get_settings", lambda: mock_cfg)
        dm._display = None

        assert isinstance(dm.get_display(), dm.NullDisplay)

    def test_factory_oled_returns_oled_display(self, monkeypatch):
        """DISPLAY_TYPE=oled → OledDisplay instance."""
        import services.display as dm
        from unittest.mock import MagicMock

        mock_cfg = MagicMock()
        mock_cfg.display_type    = "oled"
        mock_cfg.display_model   = "ssd1306"
        mock_cfg.display_i2c_address = 0x3C
        mock_cfg.display_i2c_bus = 1
        mock_cfg.display_width   = 128
        mock_cfg.display_height  = 64
        monkeypatch.setattr(dm, "get_settings", lambda: mock_cfg)
        dm._display = None

        assert isinstance(dm.get_display(), dm.OledDisplay)

    def test_factory_tft_returns_tft_display(self, monkeypatch):
        """DISPLAY_TYPE=tft → TftDisplay instance."""
        import services.display as dm
        from unittest.mock import MagicMock

        mock_cfg = MagicMock()
        mock_cfg.display_type   = "tft"
        mock_cfg.display_model  = "st7735"
        mock_cfg.display_spi_bus = 0
        mock_cfg.display_spi_dev = 1
        mock_cfg.display_dc_pin  = 16
        mock_cfg.display_rst_pin = 20
        mock_cfg.display_width   = 128
        mock_cfg.display_height  = 160
        monkeypatch.setattr(dm, "get_settings", lambda: mock_cfg)
        dm._display = None

        assert isinstance(dm.get_display(), dm.TftDisplay)

    def test_factory_unknown_type_falls_back_to_null(self, monkeypatch):
        """Unknown DISPLAY_TYPE → NullDisplay with a warning, no crash."""
        import services.display as dm
        from unittest.mock import MagicMock

        mock_cfg = MagicMock()
        mock_cfg.display_type = "e_ink"
        monkeypatch.setattr(dm, "get_settings", lambda: mock_cfg)
        dm._display = None

        assert isinstance(dm.get_display(), dm.NullDisplay)

    def test_factory_config_error_falls_back_to_null(self, monkeypatch):
        """Config read error → NullDisplay, no crash."""
        import services.display as dm
        monkeypatch.setattr(dm, "get_settings", lambda: (_ for _ in ()).throw(RuntimeError("cfg fail")))
        dm._display = None

        assert isinstance(dm.get_display(), dm.NullDisplay)

    # ── Singleton ─────────────────────────────────────────────────────────────

    def test_singleton_returns_same_instance(self):
        from services.display import get_display
        assert get_display() is get_display()

    # ── NullDisplay ───────────────────────────────────────────────────────────

    def test_null_display_setup_always_true(self):
        from services.display import NullDisplay
        d = NullDisplay()
        assert d.setup() is True
        assert d.available is True

    def test_null_display_all_screens_safe(self):
        from services.display import NullDisplay
        d = NullDisplay()
        d.setup()
        d.show_boot("1.0.0")
        d.show_idle("Bereit")
        d.show_user_login("Max")
        d.show_playing("Song", "Artist", "Max")
        d.show_setup("Wundio-Setup", "192.168.50.1")
        d.show_error("Fehler!")
        d.clear()
        d.teardown()

    def test_null_display_no_emoji_param(self):
        """show_user_login takes only name – no emoji argument."""
        from services.display import NullDisplay
        import inspect
        sig = inspect.signature(NullDisplay.show_user_login)
        params = list(sig.parameters.keys())
        assert "emoji" not in params, (
            "emoji parameter was removed from show_user_login – "
            "it was never used in practice"
        )

    # ── OledDisplay ───────────────────────────────────────────────────────────

    def test_oled_setup_without_hardware_returns_false(self):
        from services.display import OledDisplay
        d = OledDisplay()
        result = d.setup()
        assert result is False          # luma.oled stub raises → not available
        assert d.available is False

    def test_oled_available_matches_setup_return(self):
        from services.display import OledDisplay
        d = OledDisplay()
        result = d.setup()
        assert result == d.available

    def test_oled_all_screens_safe_without_hardware(self):
        from services.display import OledDisplay
        d = OledDisplay()
        d.setup()   # will fail gracefully without hardware
        d.show_boot("0.2.0")
        d.show_idle("Bereit")
        d.show_user_login("Emma")
        d.show_playing("Bohemian Rhapsody", "Queen", "Emma")
        d.show_setup("Wundio-Setup", "192.168.50.1")
        d.show_error("Test-Fehler")
        d.clear()
        d.teardown()

    def test_oled_sh1106_model_accepted(self):
        """OledDisplay accepts model='sh1106' without raising."""
        from services.display import OledDisplay
        d = OledDisplay(model="sh1106")
        result = d.setup()   # fails without hardware, must not raise
        assert isinstance(result, bool)

    # ── TftDisplay ────────────────────────────────────────────────────────────

    def test_tft_setup_without_hardware_returns_false(self):
        from services.display import TftDisplay
        d = TftDisplay()
        result = d.setup()
        assert result is False
        assert d.available is False

    def test_tft_all_screens_safe_without_hardware(self):
        from services.display import TftDisplay
        d = TftDisplay()
        d.setup()
        d.show_boot("0.2.0")
        d.show_idle("Bereit")
        d.show_user_login("Lena")
        d.show_playing("Imagine", "John Lennon")
        d.show_setup("Wundio-Setup", "192.168.50.1")
        d.show_error("TFT-Fehler")
        d.clear()
        d.teardown()

    def test_tft_ili9341_model_accepted(self):
        from services.display import TftDisplay
        d = TftDisplay(model="ili9341")
        result = d.setup()
        assert isinstance(result, bool)

    # ── BaseDisplay interface ─────────────────────────────────────────────────

    def test_all_drivers_implement_base_interface(self):
        """Every driver must be a subclass of BaseDisplay."""
        from services.display import BaseDisplay, NullDisplay, OledDisplay, TftDisplay
        for cls in (NullDisplay, OledDisplay, TftDisplay):
            assert issubclass(cls, BaseDisplay), f"{cls.__name__} must subclass BaseDisplay"

    def test_show_user_login_signature_no_emoji(self):
        """All drivers: show_user_login(name) – emoji param must not exist."""
        import inspect
        from services.display import NullDisplay, OledDisplay, TftDisplay
        for cls in (NullDisplay, OledDisplay, TftDisplay):
            sig = inspect.signature(cls.show_user_login)
            assert "emoji" not in sig.parameters, (
                f"{cls.__name__}.show_user_login must not have an emoji parameter"
            )