# Wundio bauen – Varianten

Wundio verkauft keine Bauteile. Wir zeigen zwei erprobte Wege, eine Box zu bauen –
du entscheidest, was zu dir passt. Beide Varianten laufen mit derselben Software;
der Installer fragt, welche Teile du verwendest.

| | [Stecken & Schrauben](stecken-schrauben.md) | [Löten](loeten.md) |
|---|---|---|
| Für wen | Eltern ohne Elektronik-Erfahrung | Bastler mit Lötkolben |
| Werkzeug | Schraubendreher, Crimpzange für Aderendhülsen | Lötkolben, Lötzinn, Seitenschneider |
| Verbindungen | Schraubklemmen + Aderendhülsen, rastende Stecker | gelötet / Schraubklemmen |
| Haltbarkeit in der Kinderbox | sehr gut (nichts kann abrutschen) | sehr gut, wenn sauber gelötet |
| Bauteilkosten | etwas höher (fertige Module) | günstiger (lose Breakout-Boards) |
| Zeitaufwand | ca. 1–2 h | ca. 2–3 h |

Nicht empfohlen für die fertige Box: lose Dupont-Steckkabel ohne Sicherung –
sie lösen sich bei Erschütterung (Box fällt runter, Kind schüttelt sie).

## Installer-Antworten

| Frage im Installer | Stecken & Schrauben | Löten |
|---|---|---|
| Display | 1) OLED SSD1306 | 1) OLED SSD1306 |
| RFID-Reader | 3) M5Stack RFID 2 | 1) RC522 |
| Audio | 2) MAX98357A (Speaker Bonnet) | 2) MAX98357A |

Danach: `sudo reboot`, dann die [Hardware-Validierung](../hardware-validation.md) durchgehen.

## Gemeinsam für beide Varianten

- Raspberry Pi 3B+ oder 4 (2 GB reichen), offizielles Netzteil
- microSD 32 GB (A1, „Endurance“ empfohlen)
- Passiver Lautsprecher 4 Ω, 3–5 W
- RFID-Karten oder -Sticker 13,56 MHz (MIFARE Classic 1K oder NTAG215), 30–50 Stück
- 5 Arcade-Taster 24 mm oder 30 mm (Play/Pause, Vor, Zurück, Lauter, Leiser)
- USB-C-Einbaubuchse (Panel-Mount) mit kurzem Kabel – das Kind steckt nie direkt am Pi ein
- Gehäuse (3D-Druck, PETG empfohlen) – Druckdateien folgen

Preise ändern sich – bitte vor dem Kauf vergleichen.

## Kindersicherheit (beide Varianten)

- Elektronik vollständig im Gehäuse, Deckel mit Torx- oder Sicherheitsschrauben.
- Keine abnehmbaren Kleinteile außen; Taster rasten fest ein.
- Jedes Kabel mit Zugentlastung (Kabelbinder am Gehäuse), damit keine Kraft auf Klemmen/Lötstellen wirkt.
- Lüftungsschlitze schmal halten (keine Finger-/Stiftöffnungen).
- Nur das Original-Netzteil verwenden. Kein Akku ohne Schutzschaltung.
