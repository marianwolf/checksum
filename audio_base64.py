#!/usr/bin/env python3
"""
Audio zu PNG Konverter

Dieses Programm liest Audiodateien im MP3- oder WAV-Format ein
und konvertiert deren Binärdaten in eine PNG-Bilddatei.

Die ursprünglichen Binärdaten werden verlustfrei in den Bildpixeln kodiert.

Funktionen:
- Audio zu PNG Konvertierung
- Unterstützung für MP3 und WAV
- Komprimierungsalgorithmus (zlib)
- Adaptives PNG-Filter-System
"""

import os
import sys
import struct
import argparse
import zlib
from typing import Tuple, Optional, List, Callable, Dict, Any
from io import BytesIO

# ============================================================================
# KONSTANTEN
# ============================================================================

# PNG Signatur
PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'

# Komprimierungstypen
COMPRESSION_NONE = 255
COMPRESSION_ZLIB = 0

# RGB Modus
RGB_INTERLEAVED_DISABLED = 0
RGB_INTERLEAVED_ENABLED = 1

# Maximale Dateigröße für den Speicher (100 MB)
MAX_FILE_SIZE = 100 * 1024 * 1024

# PNG Filtertypen
FILTER_NONE = 0
FILTER_SUB = 1
FILTER_UP = 2
FILTER_AVERAGE = 3
FILTER_PAETH = 4


# ============================================================================
# HILFSFUNKTIONEN
# ============================================================================

def validate_png_signature(png_data: bytes) -> bool:
    """
    Validiert die PNG-Signatur.
    
    Args:
        png_data: PNG-Binärdaten
        
    Returns:
        True wenn gültige PNG-Signatur, False otherwise
    """
    return png_data[:8] == PNG_SIGNATURE


def calculate_crc32(data: bytes) -> int:
    """
    Berechnet den CRC32-Wert für Daten.
    
    Args:
        data: Binärdaten
        
    Returns:
        CRC32-Wert als Integer
    """
    return zlib.crc32(data) & 0xFFFFFFFF


def parse_ihdr_chunk(data: bytes) -> Dict[str, int]:
    """
    Parst einen IHDR-Chunk und gibt die Bildinformationen zurück.
    
    Args:
        data: IHDR-Chunk-Daten (17 Bytes)
        
    Returns:
        Dictionary mit Bildinformationen
    """
    if len(data) < 13:
        raise ValueError("IHDR-Chunk ist zu kurz")
    
    width = struct.unpack('>I', data[0:4])[0]
    height = struct.unpack('>I', data[4:8])[0]
    bit_depth = data[8]
    color_type = data[9]
    compression = data[10]
    filter_method = data[11]
    interlace = data[12]
    
    # Validiere bekannte Einschränkungen
    if width == 0 or height == 0:
        raise ValueError("Ungültige Bilddimensionen")
    
    if bit_depth != 8:
        raise ValueError(f"Nur 8-Bit Farbtiefe wird unterstützt, erhalten: {bit_depth}")
    
    valid_color_types = {2, 6}  # RGB, RGBA
    if color_type not in valid_color_types:
        raise ValueError(f"Nicht unterstützter Farbtyp: {color_type}")
    
    if compression != 0:
        raise ValueError(f"Unbekannte Komprimierungsmethode: {compression}")
    
    if filter_method != 0:
        raise ValueError(f"Unbekannte Filter-Methode: {filter_method}")
    
    return {
        'width': width,
        'height': height,
        'bit_depth': bit_depth,
        'color_type': color_type,
        'compression': compression,
        'filter_method': filter_method,
        'interlace': interlace
    }


def get_bytes_per_pixel(color_type: int) -> int:
    """
    Gibt die Anzahl der Bytes pro Pixel basierend auf dem Farbtyp zurück.
    
    Args:
        color_type: PNG-Farbtyp (2=RGB, 6=RGBA)
        
    Returns:
        Bytes pro Pixel
    """
    color_type_map = {
        2: 3,  # RGB
        6: 4   # RGBA
    }
    return color_type_map.get(color_type, 3)


# ============================================================================
# MP3 UND WAV VALIDIERUNG
# ============================================================================

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
        header_size = (sync_size[0] << 21) | (sync_size[1] << 14) | \
                      (sync_size[2] << 7) | sync_size[3]
        total_tag_size = 10 + header_size
        
        if len(data) < total_tag_size + 4:
            pass
        else:
            data = data[total_tag_size:]
    
    # MP3-Frame-Header-Prüfung
    for i in range(min(len(data) - 3, 100)):
        if data[i] == 0xFF:
            if i + 1 < len(data):
                second_byte = data[i + 1]
                if (second_byte & 0xE0) == 0xE0:
                    mpeg_version = (second_byte >> 3) & 0x03
                    if mpeg_version != 0x01:
                        layer = (second_byte >> 1) & 0x03
                        if layer != 0x00:
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
    if len(data) < 44:
        return False
    
    # RIFF-Header prüfen
    if data[:4] != b'RIFF':
        return False
    
    # WAVE-Format prüfen
    if data[8:12] != b'WAVE':
        return False
    
    # fmt -Chunk prüfen
    if data[12:16] != b'fmt ':
        return False
    
    # Audio-Format (1 = PCM)
    audio_format = struct.unpack('<H', data[20:22])[0]
    
    # Für WAV benötigen wir mindestens PCM (1) oder komprimierte Formate
    valid_formats = [1, 7, 65534]
    
    if audio_format not in valid_formats:
        if audio_format == 65534 and len(data) >= 68:
            valid_formats_ext = [0x00000001, 0x00000006]
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
    
    if file_size > MAX_FILE_SIZE:
        return None, (f"Fehler: Datei ist zu groß ({file_size} Bytes). "
                     f"Maximale Größe: {MAX_FILE_SIZE} Bytes.")
    
    try:
        with open(filepath, 'rb') as f:
            header = f.read(100)
    except IOError as e:
        return None, f"Fehler beim Lesen der Datei: {e}"
    
    ext = os.path.splitext(filepath)[1].lower()
    if ext not in ['.mp3', '.wav']:
        return None, (f"Fehler: Nicht unterstütztes Dateiformat '{ext}'. "
                      f"Unterstützt werden nur .mp3 und .wav.")
    
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


# ============================================================================
# PNG-FILTERFUNKTIONEN
# ============================================================================

def apply_png_filter(row_data: bytes, prev_row: bytes, filter_type: int) -> bytes:
    """
    Wendet einen PNG-Filter auf eine Zeile an.
    
    Args:
        row_data: Original-Zeilendaten
        prev_row: Vorherige Zeile (kann leer sein)
        filter_type: Zu verwendender Filter-Typ
        
    Returns:
        Gefilterte Zeilendaten mit Filter-Byte am Anfang
    """
    filter_byte = bytes([filter_type])
    
    if filter_type == FILTER_NONE:
        return filter_byte + row_data
    
    elif filter_type == FILTER_SUB:
        result = bytearray([FILTER_SUB])
        for i in range(len(row_data)):
            left = row_data[i - 1] if i > 0 else 0
            result.append((row_data[i] - left) & 0xFF)
        return bytes(result)
    
    elif filter_type == FILTER_UP:
        result = bytearray([FILTER_UP])
        for i in range(len(row_data)):
            up = prev_row[i] if i < len(prev_row) else 0
            result.append((row_data[i] - up) & 0xFF)
        return bytes(result)
    
    elif filter_type == FILTER_AVERAGE:
        result = bytearray([FILTER_AVERAGE])
        for i in range(len(row_data)):
            left = row_data[i - 1] if i > 0 else 0
            up = prev_row[i] if i < len(prev_row) else 0
            avg = (left + up) // 2
            result.append((row_data[i] - avg) & 0xFF)
        return bytes(result)
    
    elif filter_type == FILTER_PAETH:
        result = bytearray([FILTER_PAETH])
        for i in range(len(row_data)):
            left = row_data[i - 1] if i > 0 else 0
            up = prev_row[i] if i < len(prev_row) else 0
            upleft = prev_row[i - 1] if i > 0 and i < len(prev_row) else 0
            
            p = left + up - upleft
            pa = abs(p - left)
            pb = abs(p - up)
            pc = abs(p - upleft)
            
            if pa <= pb and pa <= pc:
                pred = left
            elif pb <= pc:
                pred = up
            else:
                pred = upleft
            
            result.append((row_data[i] - pred) & 0xFF)
        return bytes(result)
    
    return filter_byte + row_data


def find_best_filter(row_data: bytes, prev_row: bytes,
                     compression_func: Callable[[bytes], bytes]) -> Tuple[int, int, bytes]:
    """
    Findet den optimalen PNG-Filter für eine Zeile.
    
    Args:
        row_data: Original-Zeilendaten
        prev_row: Vorherige Zeile
        compression_func: Funktion zur Komprimierung
        
    Returns:
        Tuple aus (Filter-Typ, komprimierte Größe, gefilterte Daten)
    """
    best_type = 0
    best_size: int | float = float('inf')
    best_filtered: bytes = b''
    
    for filter_type in range(5):
        filtered = apply_png_filter(row_data, prev_row, filter_type)
        try:
            compressed = compression_func(filtered)
            if len(compressed) < best_size:
                best_size = len(compressed)
                best_type = filter_type
                best_filtered = filtered
        except Exception:
            continue
    
    return best_type, int(best_size), best_filtered


# ============================================================================
# KOMPRIMIERUNG
# ============================================================================

def compress_data(data: bytes, compression_type: int,
                   file_type: str = 'wav') -> Tuple[bytes, int]:
    """
    Komprimiert Daten mit dem angegebenen Algorithmus.
    
    Args:
        data: Zu komprimierende Daten
        compression_type: Gewünschter Komprimierungstyp
        file_type: Dateityp für Optimierung
        
    Returns:
        Tuple aus (komprimierte_daten, compression_type)
    """
    if compression_type == COMPRESSION_ZLIB:
        return zlib.compress(data, 9), compression_type
    
    return data, COMPRESSION_NONE


# ============================================================================
# PNG ERSTELLUNG (ENCODING)
# ============================================================================

def bytes_to_png_data(audio_data: bytes,
                      file_type: str = 'mp3') -> Tuple[bytes, Tuple[int, int]]:
    """
    Konvertiert Binärdaten in PNG-Bilddaten.
    
    Args:
        audio_data: Binärdaten der Audiodatei
        file_type: Dateityp ('mp3' oder 'wav') für optimale Komprimierung
        
    Returns:
        Tuple aus (PNG-Bilddaten, (Breite, Höhe))
    """
    # Komprimiere die Audiodaten
    compressed_audio, compression_type = compress_data(
        audio_data, COMPRESSION_ZLIB, file_type
    )
    
    # Füge Header hinzu
    original_length = len(audio_data)
    checksum = calculate_crc32(audio_data)
    
    header = (
        struct.pack('<Q', original_length) +
        struct.pack('<I', checksum) +
        struct.pack('B', compression_type)
    )
    data_with_header = header + compressed_audio
    
    # RGB-Modus (3 Bytes/Pixel)
    bytes_per_pixel = 3
    total_pixels = len(data_with_header)
    width = min(1024, total_pixels)
    height = (total_pixels + width - 1) // width
    
    pixels = bytearray(width * height * bytes_per_pixel)
    pixels[:len(data_with_header)] = data_with_header
    
    png_signature = PNG_SIGNATURE
    ihdr_data = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
    ihdr_crc = calculate_crc32(b'IHDR' + ihdr_data)
    ihdr_chunk = struct.pack('>I', 13) + b'IHDR' + ihdr_data + \
                 struct.pack('>I', ihdr_crc)
    
    raw_data = b''
    prev_row = b''
    
    for row in range(height):
        row_start = row * width * bytes_per_pixel
        row_end = min(row_start + width * bytes_per_pixel, len(pixels))
        row_data = bytes(pixels[row_start:row_end])
        
        _, _, filtered_row = find_best_filter(
            row_data, prev_row, lambda d: zlib.compress(d, 9)
        )
        raw_data += filtered_row
        prev_row = row_data
    
    compressed_data = zlib.compress(raw_data, 9)
    idat_crc = calculate_crc32(b'IDAT' + compressed_data)
    idat_chunk = struct.pack('>I', len(compressed_data)) + b'IDAT' + \
                 compressed_data + struct.pack('>I', idat_crc)
    
    iend_crc = calculate_crc32(b'IEND')
    iend_chunk = struct.pack('>I', 0) + b'IEND' + struct.pack('>I', iend_crc)
    
    png_data = png_signature + ihdr_chunk + idat_chunk + iend_chunk
    
    return png_data, (width, height)


# ============================================================================
# HAUPTFUNKTIONEN
# ============================================================================

def convert_audio_to_png(input_path: str, output_path: Optional[str] = None,
                         verbose: bool = False) -> bool:
    """
    Konvertiert eine Audiodatei (MP3/WAV) in ein PNG-Bild.
    
    Args:
        input_path: Pfad zur Eingabe-Audiodatei
        output_path: Pfad zur Ausgabe-PNG-Datei (optional, auto-generiert wenn None)
        verbose: Verbose Ausgabe aktivieren
        
    Returns:
        True bei Erfolg, False bei Fehler
    """
    print("=== Audio zu PNG Konverter ===")
    print(f"Eingabedatei: {input_path}")
    
    file_type, error = validate_audio_file(input_path)
    if error:
        print(error)
        return False
    
    assert file_type is not None
    print(f"Dateityp erkannt: {file_type.upper()}")
    print(f"Farbmodus: RGB (farbig)")
    
    file_size = os.path.getsize(input_path)
    print(f"Dateigröße: {file_size:,} Bytes ({file_size / 1024:.2f} KB)")
    
    try:
        with open(input_path, 'rb') as f:
            audio_data = f.read()
    except IOError as e:
        print(f"Fehler beim Lesen der Audiodatei: {e}")
        return False
    
    print(f"Daten gelesen: {len(audio_data):,} Bytes")
    
    if output_path is None:
        base_name = os.path.splitext(input_path)[0]
        output_path = f"{base_name}_color.png"
    
    print(f"Ausgabedatei: {output_path}")
    
    print("Konvertiere Binärdaten zu PNG...")
    png_data, dimensions = bytes_to_png_data(
        audio_data, file_type=file_type
    )
    width, height = dimensions
    
    print(f"Komprimierungsstrategie: zlib")
    print(f"Bilddimensionen: {width} x {height} Pixel")
    print(f"PNG-Größe: {len(png_data):,} Bytes")
    print(f"Kompressionsrate: {len(png_data) / file_size:.2%} der Originalgröße")
    
    try:
        with open(output_path, 'wb') as f:
            f.write(png_data)
        print(f"PNG-Datei erfolgreich gespeichert: {output_path}")
    except IOError as e:
        print(f"Fehler beim Schreiben der PNG-Datei: {e}")
        return False
    
    print("=== Konvertierung erfolgreich abgeschlossen ===")
    return True


def main():
    """Hauptfunktion für Kommandozeilen-Ausführung."""
    parser = argparse.ArgumentParser(
        description='Konvertiert Audiodateien (MP3/WAV) zu PNG-Bildern.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Beispiele:
  %(prog)s audio.mp3                    # Konvertiert MP3 zu PNG
  %(prog)s audio.wav output.png        # Konvertiert WAV zu PNG mit Ausgabename
'''
    )
    
    parser.add_argument('input', nargs='?', help='Eingabedatei (Audio)')
    parser.add_argument('output', nargs='?', help='Ausgabedatei (optional)')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Verbose Ausgabe')
    
    args = parser.parse_args()
    
    if not args.input:
        parser.print_help()
        return 1
    
    return (0 if convert_audio_to_png(
        args.input, args.output, args.verbose
    ) else 1)


if __name__ == '__main__':
    sys.exit(main())
