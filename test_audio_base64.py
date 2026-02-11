#!/usr/bin/env python3
"""
Unit-Tests für audio_base64.py

Testet verschiedene Szenarien:
- PNG-Signatur-Validierung
- CRC32-Berechnung
- IHDR-Parsing
- Bytes-pro-Pixel-Berechnung
- PNG-Filter
- Komprimierung
- PNG-Erstellung
"""

import os
import sys
import struct
import zlib
import unittest

# Importiere die zu testenden Funktionen
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from audio_base64 import (
    # Konstanten
    PNG_SIGNATURE,
    COMPRESSION_NONE,
    COMPRESSION_ZLIB,
    FILTER_NONE,
    FILTER_SUB,
    FILTER_UP,
    FILTER_AVERAGE,
    FILTER_PAETH,
    
    # Hilfsfunktionen
    validate_png_signature,
    calculate_crc32,
    parse_ihdr_chunk,
    get_bytes_per_pixel,
    
    # PNG-Filter
    apply_png_filter,
    find_best_filter,
    
    # Komprimierung
    compress_data,
    
    # Hauptfunktionen
    bytes_to_png_data,
)


class TestPngSignatureValidation(unittest.TestCase):
    """Tests für PNG-Signatur-Validierung."""
    
    def test_valid_signature(self):
        """Testet, ob eine gültige PNG-Signatur akzeptiert wird."""
        valid_png = PNG_SIGNATURE + b'IHDR' + b'\x00' * 100
        self.assertTrue(validate_png_signature(valid_png))
    
    def test_invalid_signature(self):
        """Testet, ob eine ungültige PNG-Signatur abgelehnt wird."""
        invalid_png = b'NOTPNG' + b'\x00' * 100
        self.assertFalse(validate_png_signature(invalid_png))
    
    def test_empty_data(self):
        """Testet, ob leere Daten abgelehnt werden."""
        self.assertFalse(validate_png_signature(b''))
    
    def test_short_data(self):
        """Testet, ob kurze Daten abgelehnt werden."""
        self.assertFalse(validate_png_signature(b'PNG'))


class TestCrc32Calculation(unittest.TestCase):
    """Tests für CRC32-Berechnung."""
    
    def test_empty_data(self):
        """Testet CRC32 für leere Daten."""
        self.assertEqual(calculate_crc32(b''), 0)
    
    def test_known_value(self):
        """Testet CRC32 für bekannte Daten."""
        data = b'hello world'
        expected = zlib.crc32(data) & 0xFFFFFFFF
        self.assertEqual(calculate_crc32(data), expected)
    
    def test_consistency(self):
        """Testet Konsistenz der CRC32-Berechnung."""
        data = b'test data ' * 100
        self.assertEqual(calculate_crc32(data), calculate_crc32(data))


class TestIhdrParsing(unittest.TestCase):
    """Tests für IHDR-Chunk-Parsing."""
    
    def test_valid_ihdr(self):
        """Testet Parsing eines gültigen IHDR-Chunks."""
        width = 1024
        height = 768
        bit_depth = 8
        color_type = 2  # RGB
        compression = 0
        filter_method = 0
        interlace = 0
        
        ihdr_data = struct.pack('>IIBBBBB', width, height, bit_depth,
                                  color_type, compression, filter_method, interlace)
        
        result = parse_ihdr_chunk(ihdr_data)
        
        self.assertEqual(result['width'], width)
        self.assertEqual(result['height'], height)
        self.assertEqual(result['bit_depth'], bit_depth)
        self.assertEqual(result['color_type'], color_type)
    
    def test_invalid_ihdr_short(self):
        """Testet, ob zu kurze IHDR-Daten einen Fehler auslösen."""
        with self.assertRaises(ValueError):
            parse_ihdr_chunk(b'short')
    
    def test_invalid_width(self):
        """Testet, ob eine Breite von 0 einen Fehler auslöst."""
        ihdr_data = struct.pack('>IIBBBBB', 0, 768, 8, 2, 0, 0, 0)
        with self.assertRaises(ValueError):
            parse_ihdr_chunk(ihdr_data)
    
    def test_invalid_bit_depth(self):
        """Testet, ob eine nicht-unterstützte Bit-Tiefe einen Fehler auslöst."""
        ihdr_data = struct.pack('>IIBBBBB', 1024, 768, 16, 2, 0, 0, 0)
        with self.assertRaises(ValueError):
            parse_ihdr_chunk(ihdr_data)


class TestBytesPerPixel(unittest.TestCase):
    """Tests für Bytes-pro-Pixel-Berechnung."""
    
    def test_rgb(self):
        """Testet RGB (3 Bytes/Pixel)."""
        self.assertEqual(get_bytes_per_pixel(2), 3)
    
    def test_rgba(self):
        """Testet RGBA (4 Bytes/Pixel)."""
        self.assertEqual(get_bytes_per_pixel(6), 4)
    
    def test_unknown(self):
        """Testet unbekannten Farbtyp (Standard 3)."""
        self.assertEqual(get_bytes_per_pixel(99), 3)


class TestPngFilter(unittest.TestCase):
    """Tests für PNG-Filter."""
    
    def test_filter_none(self):
        """Testet Filter None."""
        row = b'\x01\x02\x03\x04'
        prev = b''
        filtered = apply_png_filter(row, prev, FILTER_NONE)
        self.assertEqual(filtered[0], FILTER_NONE)
        self.assertEqual(filtered[1:], row)
    
    def test_filter_sub(self):
        """Testet Filter Sub."""
        row = b'\x10\x20\x30\x40'
        prev = b''
        filtered = apply_png_filter(row, prev, FILTER_SUB)
        self.assertEqual(filtered[0], FILTER_SUB)
        # Erster Wert bleibt, zweite Differenz zum vorherigen
        self.assertEqual(filtered[1], 0x10)
        self.assertEqual(filtered[2], (0x20 - 0x10) & 0xFF)
    
    def test_filter_up(self):
        """Testet Filter Up."""
        row = b'\x10\x20\x30\x40'
        prev = b'\x05\x05\x05\x05'
        filtered = apply_png_filter(row, prev, FILTER_UP)
        self.assertEqual(filtered[0], FILTER_UP)
        self.assertEqual(filtered[1], (0x10 - 0x05) & 0xFF)


class TestFindBestFilter(unittest.TestCase):
    """Tests für optimale Filterauswahl."""
    
    def test_returns_valid_filter(self):
        """Testet, ob ein gültiger Filter zurückgegeben wird."""
        row = b'\x01\x02\x03\x04' * 10
        prev = b''
        filter_type, size, filtered = find_best_filter(
            row, prev, lambda d: zlib.compress(d, 9)
        )
        self.assertIn(filter_type, range(5))
        self.assertIsInstance(filtered, bytes)
    
    def test_finds_compressed_version(self):
        """Testet, ob eine komprimierte Version gefunden wird."""
        row = b'\x00' * 100  # Viele Nullen komprimieren gut
        prev = b''
        filter_type, size, filtered = find_best_filter(
            row, prev, lambda d: zlib.compress(d, 9)
        )
        self.assertIsNotNone(filtered)
        self.assertGreater(len(filtered), 0)


class TestCompression(unittest.TestCase):
    """Tests für Komprimierung."""
    
    def test_compress_zlib(self):
        """Testet zlib-Komprimierung."""
        original = b'Test data for compression ' * 100
        
        compressed, ctype = compress_data(
            original, COMPRESSION_ZLIB, 'wav'
        )
        
        self.assertEqual(ctype, COMPRESSION_ZLIB)
        decompressed = zlib.decompress(compressed)
        self.assertEqual(original, decompressed)
    
    def test_compression_none(self):
        """Testet, dass keine Komprimierung die Daten unverändert lässt."""
        data = b'Test data ' * 100
        compressed, ctype = compress_data(data, COMPRESSION_NONE, 'mp3')
        
        self.assertEqual(ctype, COMPRESSION_NONE)
        self.assertEqual(compressed, data)


class TestBytesToPngData(unittest.TestCase):
    """Tests für die PNG-Erstellung."""
    
    def test_empty_data(self):
        """Testet PNG-Erstellung für leere Daten."""
        png_data, dims = bytes_to_png_data(b'')
        self.assertIsInstance(png_data, bytes)
        self.assertTrue(validate_png_signature(png_data))
    
    def test_small_data(self):
        """Testet PNG-Erstellung für kleine Daten."""
        data = b'Small test data'
        png_data, dims = bytes_to_png_data(data)
        
        self.assertTrue(validate_png_signature(png_data))
        self.assertIsInstance(dims, tuple)
        self.assertEqual(len(dims), 2)
    
    def test_valid_png_structure(self):
        """Testet, ob gültige PNG-Struktur erstellt wird."""
        data = b'Test data'
        png_data, dims = bytes_to_png_data(data)
        
        # Prüfe PNG-Signatur
        self.assertTrue(validate_png_signature(png_data))
        
        # Prüfe IHDR-Chunk existiert
        ihdr_pos = png_data.find(b'IHDR')
        self.assertNotEqual(ihdr_pos, -1)
        
        # Prüfe IDAT-Chunk existiert
        idat_pos = png_data.find(b'IDAT')
        self.assertNotEqual(idat_pos, -1)
        
        # Prüfe IEND-Chunk existiert
        iend_pos = png_data.find(b'IEND')
        self.assertNotEqual(iend_pos, -1)
    
    def test_png_with_wav_data(self):
        """Testet PNG-Erstellung mit WAV-Daten."""
        data = b'WAV audio data ' * 50
        png_data, dims = bytes_to_png_data(data, file_type='wav')
        
        self.assertTrue(validate_png_signature(png_data))
        self.assertIsInstance(dims, tuple)
        self.assertEqual(len(dims), 2)


if __name__ == '__main__':
    unittest.main()
