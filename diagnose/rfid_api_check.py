#!/usr/bin/env python3
# Auf dem Pi ausfuehren: sudo /opt/wundio/venv/bin/python rfid_api_check.py
# Zeigt alle verfuegbaren Methoden des MFRC522-Readers

import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522

GPIO.setwarnings(False)
reader = SimpleMFRC522()

print("=== SimpleMFRC522 Methoden ===")
for m in sorted(dir(reader)):
    if not m.startswith("__"):
        print(f"  {m}")

print("")
print("=== reader.READER Methoden ===")
for m in sorted(dir(reader.READER)):
    if not m.startswith("__"):
        print(f"  {m}")

GPIO.cleanup()