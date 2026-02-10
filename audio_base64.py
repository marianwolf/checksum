import base64
import os

pfad = "/home/marian/Schreibtisch/test/kirbus.mp3"
def pfad_zu_base64(pfad: str) -> str:
    """
    Wandelt einen Dateipfad in Base64 um.
    
    Args:
        pfad: Der Pfad zur Datei
        
    Returns:
        Base64-kodierter String
    """
    try:
        with open(pfad, 'rb') as datei:
            daten = datei.read()
        return base64.b64encode(daten).decode('utf-8')
    except FileNotFoundError:
        raise ValueError(f"Datei nicht gefunden: {pfad}")
    except Exception as e:
        raise ValueError(f"Fehler beim Lesen der Datei: {e}")


def base64_zu_datei(base64_string: str, ausgabe_pfad: str, format_name: str | None = None) -> str:
    """
    Dekodiert Base64-String und speichert als Datei.
    
    Args:
        base64_string: Der Base64-kodierte String
        ausgabe_pfad: Pfad, wo die dekodierte Datei gespeichert werden soll
        format_name: Optionaler Dateiformat-Hinweis (wird für Endung verwendet)
        
    Returns:
        Pfad zur erstellten Datei
    """
    try:
        daten = base64.b64decode(base64_string)
        
        endung = ''
        if format_name:
            if not format_name.startswith('.'):
                format_name = '.' + format_name
            endung = format_name
        
        if not endung and '.' in ausgabe_pfad:
            pass
        elif endung:
            if '.' in ausgabe_pfad:
                ausgabe_pfad = ausgabe_pfad.rsplit('.', 1)[0] + endung
            else:
                ausgabe_pfad = ausgabe_pfad + endung
        
        with open(ausgabe_pfad, 'wb') as datei:
            datei.write(daten)
        
        return ausgabe_pfad
    except Exception as e:
        raise ValueError(f"Fehler beim Dekodieren: {e}")


def konsolen_modus():
    print("=" * 50)
    print("Base64 Pfad Encoder/Decoder")
    print("=" * 50)
    print()
    
    while True:
        print("Optionen:")
        print("  1. Pfad in Base64 kodieren")
        print("  2. Base64 in Datei dekodieren")
        print("  3. Beenden")
        print()
        
        auswahl = input("Bitte wählen (1-3): ").strip()
        
        if auswahl == '1':
            print("\n--- Pfad zu Base64 ---")
            pfad = input("Pfad zur Datei eingeben: ").strip('"\'')
            
            try:
                base64_ergebnis = pfad_zu_base64(pfad)
                print(f"\nBase64-kodiertes Ergebnis:")
                print("-" * 50)
                print(base64_ergebnis)
                print("-" * 50)
                
                speichern = input("\nIn Datei speichern? (j/n): ").lower()
                if speichern == 'j':
                    ausgabe = input("Ausgabepfad für Base64-Datei: ").strip('"\'')
                    with open(ausgabe, 'w') as f:
                        f.write(base64_ergebnis)
                    print(f"Base64 in {ausgabe} gespeichert.")
                    
            except ValueError as e:
                print(f"Fehler: {e}")
                
        elif auswahl == '2':
            print("\n--- Base64 zu Datei ---")
            
            quelle = input("Base64-Quelle (1 = Datei, 2 = direkteingabe): ").strip()
            
            if quelle == '1':
                base64_pfad = input("Pfad zur Base64-Datei: ").strip('"\'')
                try:
                    with open(base64_pfad, 'r') as f:
                        base64_string = f.read().strip()
                except Exception as e:
                    print(f"Fehler beim Lesen: {e}")
                    continue
            else:
                base64_string = input("Base64-String eingeben: ").strip()
            
            ausgabe_pfad = input("Ausgabepfad für dekodierte Datei: ").strip('"\'')
            format_name = input("Dateiformat-Endung (z.B. .png, .mp3, leer lassen für auto): ").strip()
            
            try:
                ergebnis = base64_zu_datei(base64_string, ausgabe_pfad, format_name if format_name else None)
                print(f"\nDatei erfolgreich dekodiert: {ergebnis}")
                print(f"Dateigröße: {os.path.getsize(ergebnis)} Bytes")
            except ValueError as e:
                print(f"Fehler: {e}")
                
        elif auswahl == '3':
            print("Programm beendet.")
            break
        else:
            print("Ungültige Auswahl. Bitte 1, 2 oder 3 eingeben.")
        
        print()


if __name__ == "__main__":
    konsolen_modus()
