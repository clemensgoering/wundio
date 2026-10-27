"""
Phase 0 – M5Stack Unit RFID 2 (WS1850S over I2C) driver
"""
from unittest.mock import patch

import pytest


class FakeWS1850S:
    """Minimal MFRC522-register emulation behind an smbus2-like interface."""

    ADDRESS = 0x28

    def __init__(self, uid=(0x04, 0xA3, 0xF2, 0x1B), card_present=True, version=0x15, bad_bcc=False):
        self.regs = {0x37: version, 0x14: 0x80, 0x0D: 0x00, 0x04: 0x00, 0x06: 0x00}
        self.fifo_in: list[int] = []
        self.fifo_out: list[int] = []
        self.uid = list(uid)
        self.card_present = card_present
        self.bad_bcc = bad_bcc
        self.closed = False

    def write_byte_data(self, addr, reg, value):
        assert addr == self.ADDRESS
        if reg == 0x09:                       # FIFODataReg
            self.fifo_in.append(value)
            return
        if reg == 0x0A and value & 0x80:      # flush FIFO
            self.fifo_in, self.fifo_out = [], []
            return
        if reg == 0x04 and value == 0x7F:     # clear IRQ flags
            self.regs[0x04] = 0x00
            return
        self.regs[reg] = value
        if reg == 0x0D and value & 0x80 and self.regs.get(0x01) == 0x0C:
            self._transceive()

    def _transceive(self):
        cmd, self.fifo_in = self.fifo_in, []
        if not self.card_present:
            self.regs[0x04] = 0x01            # timer IRQ – nobody answered
            return
        if cmd == [0x26]:                     # REQA → ATQA
            self.fifo_out = [0x04, 0x00]
        elif cmd == [0x93, 0x20]:             # anticollision CL1 → UID + BCC
            bcc = self.uid[0] ^ self.uid[1] ^ self.uid[2] ^ self.uid[3]
            self.fifo_out = self.uid + [bcc ^ 0xFF if self.bad_bcc else bcc]
        self.regs[0x04] = 0x30

    def read_byte_data(self, addr, reg):
        assert addr == self.ADDRESS
        if reg == 0x0A:
            return len(self.fifo_out)
        if reg == 0x09:
            return self.fifo_out.pop(0)
        return self.regs.get(reg, 0x00)

    def close(self):
        self.closed = True


def _driver(chip: FakeWS1850S):
    import sys, types
    from services.rfid import Rfid2Driver
    fake_mod = types.ModuleType("smbus2")
    fake_mod.SMBus = lambda bus: chip
    d = Rfid2Driver()
    with patch.dict(sys.modules, {"smbus2": fake_mod}), patch("time.sleep"):
        assert d.setup() is True
    return d


class TestRfid2Driver:
    def test_reads_uid_with_bcc_like_rc522(self):
        d = _driver(FakeWS1850S())
        assert d.available is True
        # 4 UID bytes + BCC (0x04^0xA3^0xF2^0x1B = 0x4E), same format as RC522Driver
        assert d.read_uid_blocking() == "04A3F21B4E"

    def test_no_card_returns_none(self):
        assert _driver(FakeWS1850S(card_present=False)).read_uid_blocking() is None

    def test_corrupt_bcc_is_rejected(self):
        assert _driver(FakeWS1850S(bad_bcc=True)).read_uid_blocking() is None

    def test_antenna_switched_on_and_off(self):
        chip = FakeWS1850S()
        d = _driver(chip)
        assert chip.regs[0x14] & 0x03 == 0x03
        d.teardown()
        assert chip.regs[0x14] & 0x03 == 0
        assert chip.closed is True

    def test_missing_reader_fails_gracefully(self):
        import sys, types
        from services.rfid import Rfid2Driver
        fake_mod = types.ModuleType("smbus2")
        fake_mod.SMBus = lambda bus: FakeWS1850S(version=0xFF)
        d = Rfid2Driver()
        with patch.dict(sys.modules, {"smbus2": fake_mod}), patch("time.sleep"):
            assert d.setup() is False
        assert d.available is False
        assert d.read_uid_blocking() is None

    def test_without_smbus2_installed(self):
        import sys
        from services.rfid import Rfid2Driver
        with patch.dict(sys.modules, {"smbus2": None}):
            assert Rfid2Driver().setup() is False

    def test_factory_selects_rfid2(self, monkeypatch):
        from config import get_settings
        from services import rfid as rfid_mod
        cfg = get_settings()
        monkeypatch.setattr(cfg, "rfid_type", "rfid2")
        assert isinstance(rfid_mod._build_driver_from_config(), rfid_mod.Rfid2Driver)
