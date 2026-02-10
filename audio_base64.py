#!/usr/bin/env python3
"""
Audio zu PNG Konverter

Dieses Programm liest Audiodateien im MP3- oder WAV-Format ein
und konvertiert deren Binärdaten in eine PNG-Bilddatei.

Die ursprünglichen Binärdaten werden verlustfrei in den Bildpixeln kodiert.
"""

import os
import sys
import struct
import argparse
from typing import Tuple, Optional
import zlib


def validate_mp3_header(data: bytes) -> bool:
    """
    Validiert ob die gegebenen Daten mit einem gültigen MP3-Header beginnen.
    
    Args:
        data: Binärdaten der Datei
        
    Returns:
        True wenn gültige MP3-Daten, False otherwise
    """
    if len(data) < 4:
        return False
    
    # MP3-Dateien können mit ID3-Tags beginnen (ID3v2 oder ID3v1)
    # ID3v2-Tags beginnen mit "ID3"
    if data[:3] == b'ID3':
        # ID3v2-Header prüfen (mindestens 10 Bytes)
        if len(data) < 10:
            return False
        
        # ID3v2-Header-Format: "ID3" + Version (2 Bytes) + Flags (1 Byte) + Size (4 Bytes)
        # Die Größe ist ein Synchsafe-Integer (7 Bits pro Byte)
        sync_size = data[6:10]
        header_size = (sync_size[0] << 21) | (sync_size[1] << 14) | (sync_size[2] << 7) | sync_size[3]
        total_tag_size = 10 + header_size
        
        if len(data) < total_tag_size + 4:  # Brauchen auch Platz für ersten Frame-Header
            # Fallback: Versuche trotzdem nach MP3-Frame zu suchen
            pass
        else:
            # Nach dem ID3v2-Tag sollte der erste MP3-Frame kommen
            data = data[total_tag_size:]
    
    # MP3-Frame-Header-Prüfung
    # Ein gültiger MP3-Frame-Header hat die Form:
    # 11 Bits: Frame Sync (alle 1)
    # 2 Bits: MPEG Audio Version ID
    # 2 Bits: Layer Description
    # 1 Bit: CRC Protection
    # 4 Bits: Bitrate Index
    # 2 Bits: Sampling Rate Index
    # 1 Bit: Padding
    # 1 Bit: Private
    # 2 Bits: Channel Mode
    
    for i in range(min(len(data) - 3, 100)):  # Suche in den ersten 100 Bytes nach Frame-Sync
        # Frame-Sync ist eine Folge von 11 Bits gesetzt (0xFFE in den ersten 11 Bits)
        # Dies erscheint als 0xFF gefolgt von 0xE? im Byte-Stream
        if data[i] == 0xFF:
            if i + 1 < len(data):
                second_byte = data[i + 1]
                # Prüfe ob die oberen 5 Bits 0x1E sind (11 gesetzte Bits)
                if (second_byte & 0xE0) == 0xE0:
                    # MPEG Version prüfen (Bits 3-4)
                    mpeg_version = (second_byte >> 3) & 0x03
                    if mpeg_version != 0x01:  # 0x01 ist reserviert
                        # Layer prüfen (Bits 1-2)
                        layer = (second_byte >> 1) & 0x03
                        if layer != 0x00:  # 0x00 ist reserviert
                            return True
    return False


def validate_wav_header(data: bytes) -> bool:
    """
    Validiert ob die gegebenen Daten mit einem gültigen WAV-Header beginnen.
    
    Args:
        data: Binärdaten der Datei
        
    Returns:
        True wenn gültige WAV-Daten, False otherwise
    """
    if len(data) < 44:  # WAV-Header ist mindestens 44 Bytes
        return False
    
    # RIFF-Header prüfen
    if data[:4] != b'RIFF':
        return False
    
    # Dateigröße (Little-Endian) - sollte mit Dateigröße minus 8 übereinstimmen
    file_size = struct.unpack('<I', data[4:8])[0]
    if file_size != len(data) - 8:
        # Warnung, aber nicht zwingend ein Fehler
        pass
    
    # WAVE-Format prüfen
    if data[8:12] != b'WAVE':
        return False
    
    # fmt -Chunk prüfen
    if data[12:16] != b'fmt ':
        return False
    
    # fmt -Chunk-Größe
    fmt_chunk_size = struct.unpack('<I', data[16:20])[0]
    
    # Audio-Format (1 = PCM)
    audio_format = struct.unpack('<H', data[20:22])[0]
    
    # Für WAV benötigen wir mindestens PCM (1) oder komprimierte Formate
    # Wir akzeptieren PCM und gängige komprimierte Formate
    valid_formats = [1, 7, 65534]  # 1=PCM, 7=Mu-Law, 65534=WAVE_FORMAT_EXTENSIBLE
    
    if audio_format not in valid_formats:
        # Für erweiterte Formate prüfen wir weiter
        if audio_format == 65534 and len(data) >= 68:
            # WAVE_FORMAT_EXTENSIBLE - prüfe GUID
            valid_formats_ext = [0x00000001, 0x00000006]  # PCM, IEEE float
            subtype_guid = data[40:44]
            if struct.unpack('<I', subtype_guid)[0] not in valid_formats_ext:
                return False
        else:
            return False
    
    return True


def validate_audio_file(filepath: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Validiert eine Audiodatei und gibt den Dateityp zurück.
    
    Args:
        filepath: Pfad zur Audiodatei
        
    Returns:
        Tuple aus (Dateityp: 'mp3' oder 'wav' oder None, Fehlermeldung oder None)
    """
    if not os.path.exists(filepath):
        return None, f"Fehler: Datei '{filepath}' existiert nicht."
    
    if not os.path.isfile(filepath):
        return None, f"Fehler: '{filepath}' ist keine reguläre Datei."
    
    file_size = os.path.getsize(filepath)
    if file_size == 0:
        return None, "Fehler: Datei ist leer."
    
    # Maximale Dateigröße für den Speicher (100 MB)
    max_size = 100 * 1024 * 1024
    if file_size > max_size:
        return None, f"Fehler: Datei ist zu groß ({file_size} Bytes). Maximale Größe: {max_size} Bytes."
    
    # Datei lesen
    try:
        with open(filepath, 'rb') as f:
            header = f.read(100)  # Lese Header für Validierung
    except IOError as e:
        return None, f"Fehler beim Lesen der Datei: {e}"
    
    # Prüfe Dateierweiterung
    ext = os.path.splitext(filepath)[1].lower()
    if ext not in ['.mp3', '.wav']:
        return None, f"Fehler: Nicht unterstütztes Dateiformat '{ext}'. Unterstützt werden nur .mp3 und .wav."
    
    # Validiere basierend auf Inhalt
    if ext == '.mp3':
        if validate_mp3_header(header):
            return 'mp3', None
        else:
            return None, "Fehler: Datei hat keine gültige MP3-Struktur."
    
    elif ext == '.wav':
        if validate_wav_header(header):
            return 'wav', None
        else:
            return None, "Fehler: Datei hat keine gültige WAV-Struktur."
    
    return None, "Fehler: Unbekannter Fehler bei der Validierung."


def bytes_to_png_data(audio_data: bytes, color: bool = False) -> Tuple[bytes, Tuple[int, int]]:
    """
    Konvertiert Binärdaten in PNG-Bilddaten.
    
    Die Binärdaten werden in ein Bild kodiert. Bei Graustufen (Standard)
    repräsentiert jedes Pixel einen Byte-Wert (0-255). Bei RGB-Farbe werden
    3 Bytes pro Pixel kodiert (R, G, B), was Speicherplatz spart.
    
    Args:
        audio_data: Binärdaten der Audiodatei
        color: Wenn True, wird RGB-Farbmodus verwendet (3 Bytes/Pixel)
               Wenn False, wird Graustufen verwendet (1 Byte/Pixel)
        
    Returns:
        Tuple aus (PNG-Bilddaten, (Breite, Höhe))
    """
    # Füge Prüfsumme und Länge hinzu, um verlustfreie Dekodierung zu ermöglichen
    length = len(audio_data)
    checksum = zlib.crc32(audio_data) & 0xFFFFFFFF
    
    # Header mit Längencode: [Länge (8 Bytes)][Prüfsumme (4 Bytes)][Farbmodus (1 Byte)][Daten...]
    header = struct.pack('<Q', length) + struct.pack('<I', checksum) + struct.pack('B', 1 if color else 0)
    data_with_header = header + audio_data
    
    # Maximale Bildbreite
    max_width = 1024
    
    if color:
        # RGB-Modus: 3 Bytes pro Pixel
        bytes_per_pixel = 3
        # Berechne Anzahl benötigter Pixel
        total_pixels = (len(data_with_header) + bytes_per_pixel - 1) // bytes_per_pixel
        width = min(max_width, total_pixels)
        height = (total_pixels + width - 1) // width
        
        # Erstelle Bild-Pixel-Daten (RGB)
        pixels = bytearray(width * height * bytes_per_pixel)
        pixels[:len(data_with_header)] = data_with_header
        
        # PNG-Header erstellen (8-byte PNG signature)
        png_signature = b'\x89PNG\r\n\x1a\n'
        
        # IHDR-Chunk (Bildinformationen - RGB: Color Type 2)
        ihdr_data = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
        ihdr_crc = zlib.crc32(b'IHDR' + ihdr_data) & 0xFFFFFFFF
        ihdr_chunk = struct.pack('>I', 13) + b'IHDR' + ihdr_data + struct.pack('>I', ihdr_crc)
        
        # IDAT-Chunk (Bilddaten - komprimiert)
        # Filtertype 0 (None) für jede Zeile
        raw_data = b''
        for row in range(height):
            row_start = row * width * bytes_per_pixel
            row_end = min(row_start + width * bytes_per_pixel, len(pixels))
            filter_byte = b'\x00'  # Filter Type: None
            row_data = bytes(pixels[row_start:row_end])
            raw_data += filter_byte + row_data
        
        compressed_data = zlib.compress(raw_data, 9)
        idat_crc = zlib.crc32(b'IDAT' + compressed_data) & 0xFFFFFFFF
        idat_chunk = struct.pack('>I', len(compressed_data)) + b'IDAT' + compressed_data + struct.pack('>I', idat_crc)
        
        # IEND-Chunk (Ende der PNG-Datei)
        iend_crc = zlib.crc32(b'IEND') & 0xFFFFFFFF
        iend_chunk = struct.pack('>I', 0) + b'IEND' + struct.pack('>I', iend_crc)
        
        # Zusammenfügen aller Chunks
        png_data = png_signature + ihdr_chunk + idat_chunk + iend_chunk
        
    else:
        # Graustufen-Modus: 1 Byte pro Pixel (Original-Verhalten)
        total_pixels = len(data_with_header)
        width = min(max_width, total_pixels)
        height = (total_pixels + width - 1) // width
        
        # Erstelle Bild-Pixel-Daten (Graustufen)
        pixels = bytearray(width * height)
        pixels[:len(data_with_header)] = data_with_header
        
        # PNG-Header erstellen (8-byte PNG signature)
        png_signature = b'\x89PNG\r\n\x1a\n'
        
        # IHDR-Chunk (Bildinformationen)
        ihdr_data = struct.pack('>IIBBBBB', width, height, 8, 0, 0, 0, 0)
        ihdr_crc = zlib.crc32(b'IHDR' + ihdr_data) & 0xFFFFFFFF
        ihdr_chunk = struct.pack('>I', 13) + b'IHDR' + ihdr_data + struct.pack('>I', ihdr_crc)
        
        # IDAT-Chunk (Bilddaten - komprimiert)
        # Filtertype 0 (None) für jede Zeile
        raw_data = b''
        for row in range(height):
            row_start = row * width
            row_end = min(row_start + width, len(pixels))
            filter_byte = b'\x00'  # Filter Type: None
            row_data = bytes(pixels[row_start:row_end])
            raw_data += filter_byte + row_data
        
        compressed_data = zlib.compress(raw_data, 9)
        idat_crc = zlib.crc32(b'IDAT' + compressed_data) & 0xFFFFFFFF
        idat_chunk = struct.pack('>I', len(compressed_data)) + b'IDAT' + compressed_data + struct.pack('>I', idat_crc)
        
        # IEND-Chunk (Ende der PNG-Datei)
        iend_crc = zlib.crc32(b'IEND') & 0xFFFFFFFF
        iend_chunk = struct.pack('>I', 0) + b'IEND' + struct.pack('>I', iend_crc)
        
        # Zusammenfügen aller Chunks
        png_data = png_signature + ihdr_chunk + idat_chunk + iend_chunk
    
    return png_data, (width, height)


def png_data_to_bytes(png_data: bytes) -> bytes:
    """
    Rekonstruiert die Original-Binärdaten aus PNG-Bilddaten.
    
    Args:
        png_data: PNG-Bilddaten
        
    Returns:
        Rekonstruierte Binärdaten
        
    Raises:
        ValueError: Wenn die Dekodierung fehlschlägt
    """
    import io
    try:
        import png
    except ImportError:
        # Fallback: Manuelle PNG-Dekodierung
        return manual_png_decode(png_data)
    
    try:
        # PNG mit pypng-Bibliothek dekodieren
        reader = png.Reader(bytes=png_data)
        width, height, pixels, info = reader.read_flat()
        
        # Prüfe Farbtyp
        color_type = info.get('greyscale', True) if info.get('greyscale') is not None else True
        
        if 'alpha' in info and info['alpha']:
            bytes_per_pixel = 2 if color_type else 4
        else:
            bytes_per_pixel = 1 if color_type else 3
        
        # Konvertiere in Byte-Array
        pixel_data = bytes(pixels)
        
        # Entferne Filter-Bytes (jede Zeile beginnt mit einem Filter-Byte)
        data = bytearray()
        row_size = width * bytes_per_pixel
        for i in range(height):
            row_start = i * (row_size + 1)
            # Lese nur bis zum Ende der Zeile
            row_end = min(row_start + 1 + row_size, len(pixel_data))
            row = pixel_data[row_start + 1:row_end]
            
            # Bei RGB/RGBA: Extrahiere nur jeden 3./4. Byte für Graustufen-Kompatibilität
            if not color_type:
                # Konvertiere RGB/RGBA zu einem kontinuierlichen Byte-Stream
                for j in range(width):
                    if bytes_per_pixel == 3:
                        data.append(row[j * 3])     # Nur Rot-Kanal
                    else:  # bytes_per_pixel == 4
                        data.append(row[j * 4])     # Nur Rot-Kanal (igno  Alpha)
            else:
                data.extend(row)
        
        # Extrahiere Header mit Längencode und Farbmodus
        if len(data) < 13:
            raise ValueError("Daten sind zu kurz für Header")
        
        length = struct.unpack('<Q', data[:8])[0]
        checksum = struct.unpack('<I', data[8:12])[0]
        color_mode = data[12]  # 0 = Graustufen, 1 = RGB
        
        # Schneide auf die erwartete Länge zu
        audio_data = data[13:13+length]
        
        # Prüfe Länge
        if len(audio_data) != length:
            raise ValueError(f"Längenkollision: erwartet {length}, erhalten {len(audio_data)}")
        
        # Prüfe Prüfsumme
        calculated_checksum = zlib.crc32(audio_data) & 0xFFFFFFFF
        if calculated_checksum != checksum:
            raise ValueError(f"Prüfsummenfehler: erwartet {checksum}, erhalten {calculated_checksum}")
        
        return bytes(audio_data)
        
    except Exception as e:
        # Versuche manuelle Dekodierung
        return manual_png_decode(png_data)


def manual_png_decode(png_data: bytes) -> bytes:
    """
    Manuelle PNG-Dekodierung ohne externe Bibliotheken.
    
    Args:
        png_data: PNG-Bilddaten
        
    Returns:
        Rekonstruierte Binärdaten
    """
    # PNG-Signature prüfen
    if png_data[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError("Ungültige PNG-Signatur")
    
    # IHDR-Chunk finden
    pos = 8
    width = height = 0
    bit_depth = color_type = 0
    
    while pos < len(png_data):
        chunk_length = struct.unpack('>I', png_data[pos:pos+4])[0]
        chunk_type = png_data[pos+4:pos+8]
        
        if chunk_type == b'IHDR':
            width = struct.unpack('>I', png_data[pos+8:pos+12])[0]
            height = struct.unpack('>I', png_data[pos+12:pos+16])[0]
            bit_depth = png_data[pos+16]
            color_type = png_data[pos+17]
        
        elif chunk_type == b'IDAT':
            compressed_data = png_data[pos+8:pos+8+chunk_length]
            raw_data = zlib.decompress(compressed_data)
            
            # Bestimme Bytes pro Pixel basierend auf Color Type
            if color_type == 0:  # Grayscale
                bytes_per_pixel = 1
            elif color_type == 2:  # RGB
                bytes_per_pixel = 3
            elif color_type == 4:  # Grayscale + Alpha
                bytes_per_pixel = 2
            elif color_type == 6:  # RGB + Alpha
                bytes_per_pixel = 4
            else:
                bytes_per_pixel = 1
            
            expected_row_size = width * bytes_per_pixel
            
            # Entferne Filter-Bytes und konvertiere zu kontinuierlichem Byte-Stream
            data = bytearray()
            for i in range(height):
                row_start = i * (expected_row_size + 1)
                row_data = raw_data[row_start+1:row_start+1+expected_row_size]
                
                # Extrahiere nur den ersten Kanal (R bei RGB, Grauwert bei Grayscale)
                for j in range(width):
                    if color_type == 2 or color_type == 6:
                        # RGB/RGBA -> Extrahiere nur jeden 3./4. Byte
                        if color_type == 2:
                            data.append(row_data[j * 3])     # R-Kanal
                        else:  # RGBA
                            data.append(row_data[j * 4])     # R-Kanal
                    else:
                        # Grayscale -> direkt übernehmen
                        data.append(row_data[j])
            
            # Extrahiere Header mit Längencode und Farbmodus
            if len(data) < 13:
                raise ValueError("Daten sind zu kurz für Header")
            
            length = struct.unpack('<Q', data[:8])[0]
            checksum = struct.unpack('<I', data[8:12])[0]
            color_mode = data[12]  # 0 = Graustufen, 1 = RGB
            
            # Schneide auf die erwartete Länge zu
            audio_data = data[13:13+length]
            
            # Prüfe Länge
            if len(audio_data) != length:
                raise ValueError(f"Längenkollision: erwartet {length}, erhalten {len(audio_data)}")
            
            # Prüfe Prüfsumme
            calculated_checksum = zlib.crc32(audio_data) & 0xFFFFFFFF
            if calculated_checksum != checksum:
                raise ValueError(f"Prüfsummenfehler: erwartet {checksum}, erhalten {calculated_checksum}")
            
            return bytes(audio_data)
        
        elif chunk_type == b'IEND':
            break
        
        pos += 12 + chunk_length
    
    raise ValueError("IDAT-Chunk nicht gefunden")


def convert_audio_to_png(input_path: str, output_path: Optional[str] = None, verbose: bool = False, color: bool = False) -> bool:
    """
    Konvertiert eine Audiodatei (MP3/WAV) in ein PNG-Bild.
    
    Args:
        input_path: Pfad zur Eingabe-Audiodatei
        output_path: Pfad zur Ausgabe-PNG-Datei (optional, auto-generiert wenn None)
        verbose: Verbose Ausgabe aktivieren
        color: Wenn True, wird RGB-Farbmodus verwendet (3 Bytes/Pixel)
               Wenn False, wird Graustufen verwendet (1 Byte/Pixel)
        
    Returns:
        True bei Erfolg, False bei Fehler
    """
    print(f"=== Audio zu PNG Konverter ===")
    print(f"Eingabedatei: {input_path}")
    
    # Validiere Eingabedatei
    file_type, error = validate_audio_file(input_path)
    if error:
        print(error)
        return False
    
    assert file_type is not None, "file_type sollte nach erfolgreicher Validierung nicht None sein"
    print(f"Dateityp erkannt: {file_type.upper()}")
    print(f"Farbmodus: {'RGB (farbig)' if color else 'Graustufen'}")
    
    # Dateigröße anzeigen
    file_size = os.path.getsize(input_path)
    print(f"Dateigröße: {file_size:,} Bytes ({file_size / 1024:.2f} KB)")
    
    # Lies gesamte Audiodatei
    try:
        with open(input_path, 'rb') as f:
            audio_data = f.read()
    except IOError as e:
        print(f"Fehler beim Lesen der Audiodatei: {e}")
        return False
    
    print(f"Daten gelesen: {len(audio_data):,} Bytes")
    
    # Generiere Ausgabepfad wenn nicht angegeben
    if output_path is None:
        base_name = os.path.splitext(input_path)[0]
        suffix = '_color' if color else ''
        output_path = f"{base_name}{suffix}.png"
    
    print(f"Ausgabedatei: {output_path}")
    
    # Konvertiere zu PNG
    print("Konvertiere Binärdaten zu PNG...")
    png_data, dimensions = bytes_to_png_data(audio_data, color=color)
    width, height = dimensions
    
    # Berechne erwartete Pixel-Anzahl und Größenvergleich
    header = struct.pack('<Q', len(audio_data)) + struct.pack('<I', zlib.crc32(audio_data) & 0xFFFFFFFF) + struct.pack('B', 1 if color else 0)
    data_with_header = header + audio_data
    expected_pixels = (len(data_with_header) + (3 if color else 1) - 1) // (3 if color else 1)
    grayscale_pixels = len(data_with_header)
    
    print(f"Bilddimensionen: {width} x {height} Pixel ({expected_pixels:,} Pixel)")
    print(f"PNG-Größe: {len(png_data):,} Bytes")
    
    if color:
        print(f"Platzersparnis: ~{66}% weniger Pixel gegenüber Graustufen")
    
    # Schreibe PNG-Datei
    try:
        with open(output_path, 'wb') as f:
            f.write(png_data)
        print(f"PNG-Datei erfolgreich gespeichert: {output_path}")
    except IOError as e:
        print(f"Fehler beim Schreiben der PNG-Datei: {e}")
        return False
    
    print("=== Konvertierung erfolgreich abgeschlossen ===")
    return True


def convert_png_to_audio(input_path: str, output_path: Optional[str] = None, verbose: bool = False) -> bool:
    """
    Rekonstruiert eine Audiodatei aus einem PNG-Bild.
    
    Args:
        input_path: Pfad zur Eingabe-PNG-Datei
        output_path: Pfad zur Ausgabe-Audiodatei (optional, auto-generiert wenn None)
        verbose: Verbose Ausgabe aktivieren
        
    Returns:
        True bei Erfolg, False bei Fehler
    """
    print(f"=== PNG zu Audio Konverter ===")
    print(f"Eingabedatei: {input_path}")
    
    # Validiere PNG-Datei
    if not os.path.exists(input_path):
        print(f"Fehler: Datei '{input_path}' existiert nicht.")
        return False
    
    # Lies PNG-Datei
    try:
        with open(input_path, 'rb') as f:
            png_data = f.read()
    except IOError as e:
        print(f"Fehler beim Lesen der PNG-Datei: {e}")
        return False
    
    print(f"PNG-Daten gelesen: {len(png_data):,} Bytes")
    
    # Dekodiere PNG zu Audiodaten
    print("Dekodiere PNG zu Binärdaten...")
    try:
        audio_data = png_data_to_bytes(png_data)
    except ValueError as e:
        print(f"Fehler bei der Dekodierung: {e}")
        return False
    
    print(f"Audio-Daten rekonstruiert: {len(audio_data):,} Bytes")
    
    # Generiere Ausgabepfad wenn nicht angegeben
    if output_path is None:
        base_name = os.path.splitext(input_path)[0]
        output_path = f"{base_name}_reconstructed.mp3"
    
    print(f"Ausgabedatei: {output_path}")
    
    # Schreibe Audiodatei
    try:
        with open(output_path, 'wb') as f:
            f.write(audio_data)
        print(f"Audiodatei erfolgreich gespeichert: {output_path}")
    except IOError as e:
        print(f"Fehler beim Schreiben der Audiodatei: {e}")
        return False
    
    print("=== Rekonstruktion erfolgreich abgeschlossen ===")
    return True


def main():
    """Hauptfunktion für Kommandozeilen-Ausführung."""
    parser = argparse.ArgumentParser(
        description='Konvertiert Audiodateien (MP3/WAV) zu PNG-Bildern und umgekehrt.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Beispiele:
  %(prog)s audio.mp3                    # Konvertiert MP3 zu PNG (Graustufen)
  %(prog)s audio.wav output.png        # Konvertiert WAV zu PNG mit Ausgabename
  %(prog)s --color audio.mp3            # Konvertiert MP3 zu farbigem PNG (RGB)
  %(prog)s --reverse audio.png         # Rekonstruiert Audio aus PNG
  %(prog)s -r audio.png audio_rec.mp3  # Rekonstruiert Audio mit Ausgabename
'''
    )
    
    parser.add_argument('input', nargs='?', help='Eingabedatei (Audio oder PNG)')
    parser.add_argument('output', nargs='?', help='Ausgabedatei (optional)')
    parser.add_argument('-r', '--reverse', action='store_true',
                        help='Konvertiert PNG zurück zu Audio')
    parser.add_argument('-c', '--color', action='store_true',
                        help='Verwendet RGB-Farbmodus (3 Bytes/Pixel, speichert ~66%% Platz)')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Verbose Ausgabe')
    
    args = parser.parse_args()
    
    if not args.input:
        parser.print_help()
        return 1
    
    if args.reverse:
        return 0 if convert_png_to_audio(args.input, args.output, args.verbose) else 1
    else:
        return 0 if convert_audio_to_png(args.input, args.output, args.verbose, args.color) else 1


if __name__ == '__main__':
    sys.exit(main())
