# Hardware-Validierung – Erster Aufbau

Ziel: Nachweisen, dass Wundio auf echter Hardware stabil läuft, bevor v1.0 und das
Gehäuse-Design starten. Jeder Abschnitt hat ein klares **Bestanden**-Kriterium.
Ergebnisse in der Tabelle am Ende eintragen.

Gilt für beide Bauvarianten aus [docs/build](build/README.md)
(„Stecken & Schrauben“ und „Löten“). Variante oben in der Ergebnistabelle notieren.

---

## 0. Vor dem ersten Start

- [ ] Aktuellen `main` nach GitHub pushen – der Installer lädt den Code von dort.
- [ ] Pi OS Lite flashen (Raspberry Pi Imager): Hostname `wundio`, SSH an,
      WLAN vorkonfigurieren (oder später über den Wundio-Hotspot).
- [ ] Spotify: im Premium-Familienabo ein eigenes Mitglied für die Box anlegen.

## 1. Aufbau (Strom aus!)

- [ ] Nach der Anleitung der gewählten Variante verkabeln:
      [Stecken & Schrauben](build/stecken-schrauben.md) oder [Löten](build/loeten.md).
- [ ] Zugtest: an jedem Kabel kräftig ziehen – nichts löst sich.
- [ ] Sichtprüfung: keine blanken Drähte, die sich berühren können.

## 2. Installation

```bash
curl -fsSL https://wundio.dev/install.sh | sudo bash
# Antworten je Variante: siehe docs/build/README.md (Installer-Antworten)
sudo reboot
```

- [ ] Installer endet ohne `[ERR ]`. Warnungen notieren.
- [ ] Nach dem Neustart: `systemctl is-active wundio-core` → `active`
- [ ] Web-UI erreichbar: `http://wundio.local:8000`

**Bestanden:** Installation ohne manuellen Eingriff.

## 3. Audio

```bash
aplay -l                                 # Karte "sndrpihifiberry" sichtbar
speaker-test -D default -c 2 -t wav -l 1 # "Front Left / Front Right" hörbar
amixer sset Master 30%                   # leiser
amixer sset Master 80%                   # lauter
```

- [ ] Ton hörbar, kein Knacken/Rauschen in Ruhe.
- [ ] Lautstärke ändert sich hörbar.
- [ ] Vol+/Vol− Taster ändern die Lautstärke.

**Bestanden:** Klarer Ton, Lautstärke über Software und Tasten regelbar.

## 4. RFID & Display

- [ ] Display zeigt beim Start „Wundio … Starting“, danach „Bereit“.
- [ ] Karte auflegen → Web-UI *RFID* zeigt die UID, Display „Unbekannter Tag“.
- [ ] 10× Karte auflegen/abnehmen → jeder Scan wird erkannt, kein Hänger.
- [ ] Diagnose ohne Web-UI: `sudo bash /opt/wundio/scripts/run-rfid.sh` zeigt die UIDs.
- [ ] Lesereichweite durch die Deckelwand (2 / 3 / 4 mm) – in mm notieren.
- [ ] M5Stack RFID 2: liest zuverlässig mit 3,3 V Versorgung? (Falls nicht: Ergebnis notieren,
      nicht eigenmächtig auf 5 V umklemmen.)
- [ ] Eine Karte an RC522 **und** RFID 2 testen (falls beide vorhanden) → gleiche UID.

**Bestanden:** Jeder Scan erkannt, Reaktion < 1 s.

## 5. Spotify-Anmeldung (kritischer Test)

- [ ] Display und Web-UI (*Einstellungen → Spotify-Konto der Box*) zeigen einen Code.
- [ ] Code auf `spotify.com/pair` eingeben → Web-UI zeigt „Mit Spotify verbunden“.
- [ ] Log prüfen: `journalctl -u wundio-core | grep -i go-librespot`
      – keine Fehler beim Lesen der `config.yml`.
- [ ] **`sudo reboot` → Box ist ohne neuen Code wieder angemeldet.**
- [ ] Strom ziehen und wieder anstecken → weiterhin angemeldet.

**Bestanden:** Nach Neustart und Stromausfall angemeldet, ohne Handy.
**Falls nicht:** `ls -la /var/lib/wundio/spotify/` (existiert `state.json`?) und Log sichern.

## 6. Karten abspielen

- [ ] In der Web-UI eine Karte mit einem Spotify-Link (Album) belegen.
- [ ] Karte auflegen → Wiedergabe startet in < 5 s.
- [ ] Play/Pause, Next, Prev funktionieren per Taster.
- [ ] Karte mit Playlist, mit Podcast (`open.spotify.com/show/...`) und mit Einzeltitel testen.

**Bestanden:** Alle vier Inhaltstypen starten per Karte.

## 7. Karten anlernen (kritischer Test)

- [ ] Eltern-Handy: Spotify-App → Gerät „Wundio“ wählen → Hörspiel-Album starten.
- [ ] Neue, unbekannte Karte auflegen → Display „Gespeichert: …“.
- [ ] In der Eltern-App auf ein anderes Gerät wechseln / Wiedergabe beenden.
- [ ] **Karte erneut auflegen → spielt auf dem Box-Konto.**
- [ ] Web-UI „Bestehende Karte neu belegen“ → Karte auflegen → neuer Inhalt gespeichert.
- [ ] Gegenprobe: private Playlist der Eltern anlernen und mit dem Box-Konto abspielen – Ergebnis notieren.

**Bestanden:** Angelernte Karte spielt danach ohne Eltern-Handy.

## 8. Unabhängigkeit von den Eltern

- [ ] Eltern hören auf ihrem eigenen Handy Spotify, gleichzeitig Karte an der Box → beide spielen weiter.
- [ ] Eltern-Handy aus / außer Haus → Karten funktionieren.

**Bestanden:** Box und Eltern stören sich nicht.

## 9. Robustheit

- [ ] 5× Strom während der Wiedergabe ziehen → Box startet jedes Mal sauber.
- [ ] Router aus, Box an, Router nach 2 min an → Box verbindet sich selbst, Karten gehen wieder.
- [ ] 8 h Dauerwiedergabe (Playlist auf Wiederholung) → keine Aussetzer, `vcgencmd measure_temp` < 75 °C.
- [ ] Bootzeit messen: Strom an → Karte spielbar (Sekunden notieren).

**Bestanden:** Keine manuelle Reparatur nötig.

---

## Ergebnisse

Variante: ☐ Stecken & Schrauben ☐ Löten · Pi-Modell: …

| # | Test | Ergebnis | Notizen |
|---|---|---|---|
| 2 | Installation | | |
| 3 | Audio | | |
| 4 | RFID & Display | | |
| 5 | Spotify-Anmeldung nach Neustart | | |
| 6 | Karten abspielen | | |
| 7 | Karten anlernen | | |
| 8 | Unabhängigkeit | | |
| 9 | Robustheit | | Bootzeit: … s |

Bei Fehlern: `sudo bash /opt/wundio/scripts/diagnose.sh` und
`journalctl -u wundio-core -n 200` sichern.

## Erkenntnisse für das Gehäuse

Beim Aufbau notieren – das sind die Eingangsdaten für das 3D-Design:

- Maße des Aufbaus (Pi + Verstärker + Kabelwege), Lautsprecher-Durchmesser und -Tiefe
- Lesedistanz RC522 durch 2 / 3 / 4 mm PLA (Testplatten drucken)
- Position und Durchmesser der Taster, Display-Ausschnitt
- Wärme: Temperatur im geschlossenen Testgehäuse nach 1 h Wiedergabe
- Zugang zu SD-Karte und Stromanschluss
