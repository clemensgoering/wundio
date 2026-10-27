# Variante „Stecken & Schrauben“ (ohne Löten)

Alle Verbindungen sind geschraubt oder rasten ein. Werkzeug: kleiner
Schlitz-Schraubendreher, Abisolierzange, Crimpzange für Aderendhülsen.

## Einkaufsliste

Zusätzlich zu den [gemeinsamen Teilen](README.md#gemeinsam-für-beide-varianten):

| Teil | Wofür | Hinweis |
|---|---|---|
| GPIO Screw Terminal HAT (z. B. 52Pi / Seeed) | alle Kabel festschrauben | Muss oben eine durchgeführte Stiftleiste haben |
| Adafruit Speaker Bonnet | Verstärker, Lautsprecher per Schraubklemme | Version mit **vorgelöteter** Buchsenleiste kaufen |
| M5Stack Unit RFID 2 (WS1850S) | Kartenleser | inkl. Grove-Kabel |
| OLED 0,96" SSD1306 I2C | Anzeige | mit **vorgelöteter** Stiftleiste kaufen |
| Arcade-Taster-Kabel mit Flachsteckern (2,8 mm) | Taster anschließen | 5 Stück |
| Litze 0,25 mm², 4 Farben | OLED-Verbindung | |
| Aderendhülsen 0,25 mm² + 0,5 mm² und Crimpzange | feste Kabelenden | Set mit Zange ca. 15–20 € |
| M2.5 Abstandshalter-Set (Messing/Nylon) | Pi + HATs verschrauben | |

## Aufbau

```
  Adafruit Speaker Bonnet    ← Lautsprecher (Schraubklemme)
  GPIO Screw Terminal HAT    ← Taster, RFID, OLED (Schraubklemmen)
  Raspberry Pi
```

### 1. Stapel montieren (Strom aus!)

1. Abstandshalter in die vier Löcher des Pi schrauben.
2. Screw Terminal HAT auf die GPIO-Leiste stecken, gerade und ganz herunterdrücken. Mit Abstandshaltern verschrauben.
3. Speaker Bonnet oben auf die Stiftleiste des Terminal HAT stecken und verschrauben.

> Die Klemmen **GPIO18, GPIO19, GPIO21** gehören jetzt dem Verstärker – dort nichts anschließen.

### 2. Aderendhülsen – so geht's

1. Litze 8 mm abisolieren, Drähte leicht verdrillen.
2. Aderendhülse aufschieben, bis keine Drähte mehr herausschauen.
3. Mit der Crimpzange zusammendrücken. Zugtest: kräftig ziehen – darf nicht abgehen.
4. In die Klemme stecken, Schraube fest anziehen, nochmals ziehen.

### 3. Kartenleser (M5Stack RFID 2)

Ein Ende des Grove-Kabels abschneiden, die vier Adern mit Aderendhülsen versehen.
**Belegung am Aufdruck der Unit ablesen, nicht nach Kabelfarbe** – Farben unterscheiden sich je nach Hersteller.

| Unit | Klemme am Terminal HAT |
|---|---|
| GND | GND |
| 5V | **3V3** (nicht 5 V – schützt die Pi-Eingänge) |
| SDA | GPIO2 (SDA) |
| SCL | GPIO3 (SCL) |

Den Leser später direkt unter die Deckelwand (2–3 mm) setzen – Lesereichweite < 2 cm.

### 4. Display (OLED)

| OLED | Klemme |
|---|---|
| GND | GND |
| VCC | 3V3 |
| SDA | GPIO2 (SDA) – teilt sich die Klemme mit dem Kartenleser |
| SCL | GPIO3 (SCL) – teilt sich die Klemme mit dem Kartenleser |

Zwei Adern in einer Klemme: beide in **eine** Doppel-Aderendhülse crimpen.
Am OLED: Buchsen-Steckkabel auf die Stiftleiste, Stecker danach mit einem Tropfen
Heißkleber oder Schrumpfschlauch sichern.

### 5. Taster

Jeder Taster hat zwei Anschlüsse. Flachstecker auf den Taster, das andere Ende mit Aderendhülse in die Klemme:

| Taster | Klemme | zweiter Anschluss |
|---|---|---|
| Play/Pause | GPIO17 | GND |
| Vor | GPIO27 | GND |
| Zurück | GPIO22 | GND |
| Lauter | GPIO23 | GND |
| Leiser | GPIO24 | GND |

Alle GND-Leitungen der Taster dürfen zusammen in GND-Klemmen (je Klemme max. 2 Adern).

### 6. Lautsprecher

Lautsprecherkabel an die Schraubklemme des Speaker Bonnet (`+` / `−`, ein Kanal reicht).

### 7. Software

```bash
curl -fsSL https://wundio.dev/install.sh | sudo bash
```
Antworten: Display **1** (OLED SSD1306) · RFID **3** (M5Stack RFID 2) · Audio **2** (MAX98357A / Speaker Bonnet).
Danach `sudo reboot` und die [Hardware-Validierung](../hardware-validation.md) durchgehen.
