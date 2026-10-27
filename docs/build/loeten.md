# Variante „Löten“

Günstige Breakout-Boards, die Stiftleisten werden selbst angelötet. Werkzeug:
Lötkolben (ca. 330 °C), bleifreies Lötzinn mit Flussmittel, Seitenschneider,
Abisolierzange.

## Einkaufsliste

Zusätzlich zu den [gemeinsamen Teilen](README.md#gemeinsam-für-beide-varianten):

| Teil | Wofür | Hinweis |
|---|---|---|
| MAX98357A I2S Breakout | Verstärker | mit Schraubklemme für den Lautsprecher |
| RC522 RFID-Modul | Kartenleser | meist mit losen Stiftleisten |
| OLED 0,96" SSD1306 I2C | Anzeige | |
| GPIO Screw Terminal HAT **oder** Lochraster-Platine | stabile Verteilung | Terminal HAT erspart die meisten Lötstellen am Pi |
| Litze 0,25 mm², Schrumpfschlauch | Verbindungen | |
| Arcade-Taster-Kabel mit Flachsteckern (2,8 mm) | Taster | 5 Stück |
| M2.5 Abstandshalter-Set | Montage | |

## Löten

1. Stiftleisten an MAX98357A, RC522 und (falls nötig) OLED anlöten – kurze Seite in die Platine, jede Lötstelle glänzend und kegelförmig.
2. Für die fertige Box keine losen Dupont-Kabel: Litzen **direkt an die Stifte löten** und mit Schrumpfschlauch isolieren, oder in die Schraubklemmen eines Terminal HAT führen.

## Verkabelung

| Bauteil | Pin | Raspberry Pi (BCM / physischer Pin) |
|---|---|---|
| MAX98357A | VIN / GND | 5V (Pin 2) / GND (Pin 6) |
| | BCLK / LRC / DIN | BCM18 (Pin 12) / BCM19 (Pin 35) / BCM21 (Pin 40) |
| | SD / GAIN | offen lassen (Mono-Mix, 9 dB) |
| RC522 | 3.3V / GND | 3.3V (Pin 1) – **nicht 5 V** / GND (Pin 20) |
| | SDA / SCK / MOSI / MISO / RST | BCM8 (24) / BCM11 (23) / BCM10 (19) / BCM9 (21) / BCM25 (22) |
| OLED | VCC / GND / SDA / SCL | 3.3V (17) / GND (9) / BCM2 (3) / BCM3 (5) |
| Taster (gegen GND) | Play/Pause · Vor · Zurück · Lauter · Leiser | BCM17 (11) · BCM27 (13) · BCM22 (15) · BCM23 (16) · BCM24 (18) |

Lautsprecher an die Schraubklemme des MAX98357A.

## Software

```bash
curl -fsSL https://wundio.dev/install.sh | sudo bash
```
Antworten: Display **1** (OLED SSD1306) · RFID **1** (RC522) · Audio **2** (MAX98357A).
Danach `sudo reboot` und die [Hardware-Validierung](../hardware-validation.md) durchgehen.
