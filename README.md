# Audio zu PNG konvertieren
python3 audio_base64.py audio.mp3 output.png
python3 audio_base64.py audio.wav

# PNG zurück zu Audio konvertieren (--reverse)
python3 audio_base64.py --reverse audio.png
python3 audio_base64.py -r audio.png audio_reconstructed.mp3