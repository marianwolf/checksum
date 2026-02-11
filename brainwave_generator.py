#!/usr/bin/env python3
"""
Brainwave Audio Generator

Erstellt binaurale Beats und Wellenformen für:
- Delta (0.5-4 Hz): Tiefschlaf, Regeneration
- Theta (4-8 Hz): Meditation, kreative Zustände
- Alpha (8-12 Hz): Entspannter Wachzustand, fokussierte Aufmerksamkeit

Die Ausgabe erfolgt als MP3-Datei mit einer Mischung aller drei Wellentypen.
"""

import numpy as np
import argparse
import os
import sys
import struct

# Versuche ffmpeg für MP3-Export zu importieren, falls verfügbar
try:
    import ffmpeg
    FFMPEG_AVAILABLE = True
except ImportError:
    FFMPEG_AVAILABLE = False


def generate_sine_wave(frequency: float, duration: float, 
                       sample_rate: int = 44100, 
                       amplitude: float = 0.5) -> np.ndarray:
    """
    Generiert eine Sinuswelle mit der angegebenen Frequenz.
    
    Args:
        frequency: Frequenz in Hz
        duration: Dauer in Sekunden
        sample_rate: Abtastrate in Hz (Standard: 44100)
        amplitude: Amplitude zwischen 0 und 1 (Standard: 0.5)
    
    Returns:
        numpy Array mit den Audiodaten
    """
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    wave = amplitude * np.sin(2 * np.pi * frequency * t)
    return wave


def generate_binaural_beat(base_frequency: float, beat_frequency: float,
                           duration: float, sample_rate: int = 44100,
                           amplitude: float = 0.3) -> np.ndarray:
    """
    Generiert einen binauralen Beat mit zwei leicht unterschiedlichen Frequenzen
    für das linke und rechte Ohr.
    
    Args:
        base_frequency: Basis-Frequenz in Hz
        beat_frequency: Beat-Frequenz in Hz (Differenz zwischen beiden Ohren)
        duration: Dauer in Sekunden
        sample_rate: Abtastrate in Hz
        amplitude: Amplitude pro Kanal
    
    Returns:
        Stereo-Audiodaten als numpy Array (shape: [samples, 2])
    """
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    
    # Linker Kanal: Basis-Frequenz
    left_channel = amplitude * np.sin(2 * np.pi * base_frequency * t)
    
    # Rechter Kanal: Basis-Frequenz + Beat-Frequenz
    right_channel = amplitude * np.sin(2 * np.pi * (base_frequency + beat_frequency) * t)
    
    # Kombiniere zu Stereo
    stereo = np.column_stack((left_channel, right_channel))
    return stereo


def generate_brainwave_mix(duration: float = 300, sample_rate: int = 44100,
                           delta_amp: float = 0.2, theta_amp: float = 0.3,
                           alpha_amp: float = 0.3) -> np.ndarray:
    """
    Generiert eine Mischung aus Delta, Theta und Alpha Wellen.
    
    Args:
        duration: Dauer in Sekunden (Standard: 5 Minuten = 300s)
        sample_rate: Abtastrate in Hz
        delta_amp: Delta-Wellen Amplitude (0.5-4 Hz)
        theta_amp: Theta-Wellen Amplitude (4-8 Hz)
        alpha_amp: Alpha-Wellen Amplitude (8-12 Hz)
    
    Returns:
        Stereo-Audiodaten als numpy Array
    """
    num_samples = int(sample_rate * duration)
    t = np.linspace(0, duration, num_samples, endpoint=False)
    
    # Delta-Wellen (0.5-4 Hz) - Mischung aus mehreren Frequenzen
    delta_frequencies = [0.5, 1.0, 2.0, 3.0]
    delta_wave = np.zeros(num_samples)
    for freq in delta_frequencies:
        delta_wave += np.sin(2 * np.pi * freq * t)
    delta_wave = (delta_amp / len(delta_frequencies)) * delta_wave
    
    # Theta-Wellen (4-8 Hz)
    theta_frequencies = [4.0, 5.0, 6.0, 7.0]
    theta_wave = np.zeros(num_samples)
    for freq in theta_frequencies:
        theta_wave += np.sin(2 * np.pi * freq * t)
    theta_wave = (theta_amp / len(theta_frequencies)) * theta_wave
    
    # Alpha-Wellen (8-12 Hz)
    alpha_frequencies = [8.0, 9.0, 10.0, 11.0]
    alpha_wave = np.zeros(num_samples)
    for freq in alpha_frequencies:
        alpha_wave += np.sin(2 * np.pi * freq * t)
    alpha_wave = (alpha_amp / len(alpha_frequencies)) * alpha_wave
    
    # Kombiniere alle Wellen
    combined = delta_wave + theta_wave + alpha_wave
    
    # Normalisiere auf [-1, 1]
    combined = combined / np.max(np.abs(combined))
    
    # Erstelle Stereo-Signal (gleiches Signal für beide Ohren)
    stereo = np.column_stack((combined, combined))
    
    return stereo


def save_wav(audio_data: np.ndarray, filepath: str, sample_rate: int = 44100) -> None:
    """
    Speichert Audiodaten als WAV-Datei.
    
    Args:
        audio_data: numpy Array mit Audiodaten
        filepath: Ausgabedateipfad
        sample_rate: Abtastrate in Hz
    """
    # Konvertiere zu 16-bit PCM
    audio_int16 = np.int16(audio_data * 32767)
    
    # WAV-Header schreiben
    num_channels = audio_data.shape[1] if len(audio_data.shape) > 1 else 1
    bytes_per_sample = 2
    sub_chunk2_size = len(audio_int16) * num_channels * bytes_per_sample
    chunk_size = 36 + sub_chunk2_size
    
    with open(filepath, 'wb') as wav_file:
        # RIFF Header
        wav_file.write(b'RIFF')
        wav_file.write(struct.pack('<I', chunk_size))
        wav_file.write(b'WAVE')
        
        # fmt Chunk
        wav_file.write(b'fmt ')
        wav_file.write(struct.pack('<I', 16))  # Subchunk1 size
        wav_file.write(struct.pack('<H', 1))   # Audio format (PCM)
        wav_file.write(struct.pack('<H', num_channels))
        wav_file.write(struct.pack('<I', sample_rate))
        wav_file.write(struct.pack('<I', sample_rate * num_channels * bytes_per_sample))
        wav_file.write(struct.pack('<H', num_channels * bytes_per_sample))
        wav_file.write(struct.pack('<H', 16))  # Bits per sample
        
        # data Chunk
        wav_file.write(b'data')
        wav_file.write(struct.pack('<I', sub_chunk2_size))
        
        # Audio-Daten schreiben
        wav_file.write(audio_int16.tobytes())


def convert_wav_to_mp3(wav_path: str, mp3_path: str, bitrate: str = '192k') -> bool:
    """
    Konvertiert eine WAV-Datei zu MP3.
    
    Args:
        wav_path: Pfad zur WAV-Datei
        mp3_path: Pfad zur MP3-Ausgabe
        bitrate: MP3-Bitrate (Standard: 192k)
    
    Returns:
        True wenn erfolgreich, False sonst
    """
    if FFMPEG_AVAILABLE:
        try:
            (ffmpeg
             .input(wav_path)
             .output(mp3_path, audio_bitrate=bitrate, ar=44100)
             .overwrite_output()
             .run(quiet=True))
            return True
        except Exception as e:
            print(f"FFmpeg Fehler: {e}", file=sys.stderr)
            return False
    else:
        # Fallback: Versuche subprocess zu verwenden
        import subprocess
        try:
            subprocess.run([
                'ffmpeg', '-i', wav_path, 
                '-b:a', bitrate, 
                '-ar', '44100',
                '-y', mp3_path
            ], check=True, capture_output=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"FFmpeg nicht verfügbar: {e}", file=sys.stderr)
            return False


def main():
    """Hauptfunktion für die Kommandozeile."""
    parser = argparse.ArgumentParser(
        description='Generiert Brainwave-Audio (Delta/Theta/Alpha) als MP3-Datei',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiel:
  python brainwave_generator.py -d 600 -o brainwaves.mp3
  python brainwave_generator.py --duration 300 --delta 0.3 --theta 0.4 --alpha 0.3
        """
    )
    
    parser.add_argument('-o', '--output', type=str, default='brainwaves.mp3',
                        help='Ausgabe-MP3-Datei (Standard: brainwaves.mp3)')
    parser.add_argument('-d', '--duration', type=int, default=300,
                        help='Dauer in Sekunden (Standard: 300 = 5 Minuten)')
    parser.add_argument('--delta', type=float, default=0.2,
                        help='Delta-Wellen Amplitude 0-1 (Standard: 0.2)')
    parser.add_argument('--theta', type=float, default=0.3,
                        help='Theta-Wellen Amplitude 0-1 (Standard: 0.3)')
    parser.add_argument('--alpha', type=float, default=0.3,
                        help='Alpha-Wellen Amplitude 0-1 (Standard: 0.3)')
    parser.add_argument('--sample-rate', type=int, default=44100,
                        help='Abtastrate in Hz (Standard: 44100)')
    parser.add_argument('--bitrate', type=str, default='192k',
                        help='MP3-Bitrate (Standard: 192k)')
    parser.add_argument('-q', '--quiet', action='store_true',
                        help='Keine Fortschrittsanzeige')
    
    args = parser.parse_args()
    
    # Ausgabe-Dateiname
    output_dir = os.path.dirname(args.output) or '.'
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    wav_path = args.output.replace('.mp3', '.wav')
    
    if not args.quiet:
        print(f"Generiere Brainwave-Audio...")
        print(f"  Dauer: {args.duration} Sekunden ({args.duration // 60} Min)")
        print(f"  Delta (0.5-4 Hz): {args.delta}")
        print(f"  Theta (4-8 Hz): {args.theta}")
        print(f"  Alpha (8-12 Hz): {args.alpha}")
    
    # Generiere Brainwave-Mischung
    audio_data = generate_brainwave_mix(
        duration=args.duration,
        sample_rate=args.sample_rate,
        delta_amp=args.delta,
        theta_amp=args.theta,
        alpha_amp=args.alpha
    )
    
    # Speichere temporär als WAV
    if not args.quiet:
        print(f"Speichere temporäre WAV-Datei...")
    save_wav(audio_data, wav_path, args.sample_rate)
    
    # Konvertiere zu MP3
    if args.output.endswith('.mp3'):
        if not args.quiet:
            print(f"Konvertiere zu MP3...")
        success = convert_wav_to_mp3(wav_path, args.output, args.bitrate)
        
        if success:
            # Lösche temporäre WAV-Datei
            os.remove(wav_path)
            if not args.quiet:
                print(f"fertig: {args.output}")
        else:
            print(f"WARNUNG: MP3-Konvertierung fehlgeschlagen, behalte WAV-Datei: {wav_path}")
    else:
        # Wenn keine MP3-Erweiterung, behalte WAV
        os.rename(wav_path, args.output)
        if not args.quiet:
            print(f"fertig: {args.output}")


if __name__ == '__main__':
    main()
