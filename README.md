# Audio Base64 Converter

Konvertiert Audiodateien (MP3/WAV) zu PNG-Bildern und umgekehrt.

## Unterstützte Dateiformate

- **Eingabe:** MP3, WAV
- **Ausgabe:** PNG (Graustufen oder RGB)

## Befehle

### Audio zu PNG konvertieren

```bash
# MP3 zu PNG (Graustufen, auto-generierter Dateiname)
python3 audio_base64.py audio.mp3

# WAV zu PNG mit Ausgabename
python3 audio_base64.py audio.wav output.png

# MP3/WAV zu PNG (RGB-Modus)
python3 audio_base64.py -c audio.mp3

# MP3/WAV zu PNG (RGB-Modus) mit Ausgabename
python3 audio_base64.py -c audio.wav output_color.png

# Mit verbose Ausgabe
python3 audio_base64.py -v audio.mp3 output.png
```

### PNG zu Audio konvertieren (Reverse)

```bash
# PNG zurück zu Audio (auto-generierter Dateiname)
python3 audio_base64.py -r audio.png

# PNG zurück zu Audio mit Ausgabename
python3 audio_base64.py -r audio.png audio_reconstructed.mp3

# PNG zurück zu Audio mit verbose Ausgabe
python3 audio_base64.py -rv audio.png output.mp3
```

### Hilfe anzeigen

```bash
cd /home/marian/nextcloud/github/checksum-1 && python3 -m pytest test_audio_base64.py -v 2>&1
```

### Test
```bash
cd /home/marian/nextcloud/github/checksum-1 && python3 -m pytest test_audio_base64.py -v 2>&1

```

## Optionen

| Option | Beschreibung |
|--------|--------------|
| `-r, --reverse` | Konvertiert PNG zurück zu Audio |
| `-c, --color` | Verwendet RGB-Farbmodus (3 Bytes/Pixel, speichert ~66% Platz) |
| `-v, --verbose` | Verbose Ausgabe |
| `-h, --help` | Hilfe anzeigen |

## Funktionsweise

- **MP3:** Keine zusätzliche Kompression (bereits komprimiert)
- **WAV:** Delta-Kodierung + Brotli/zlib Kompression für optimale Größe
- **Graustufen:** 1 Byte pro Pixel
- **RGB-Modus:** 3 Bytes pro Pixel (effizienter bei großen Dateien)