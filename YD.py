import os
import subprocess

script_dir = os.path.dirname(os.path.abspath(__file__))
# Windows-Download-Ordner holen
output_folder = os.path.join(os.path.expanduser("~"), "Downloads")
os.makedirs(output_folder, exist_ok=True)

def main():
    print("YouTube Downloader")
    print("===================")

    # Frage nach der YouTube-URL
    youtube_url = input("Gib die YouTube-URL ein: ").strip()
    if not youtube_url:
        print("Ungültige URL! Bitte starte das Skript erneut.")
        return

    # Pfad zur yt-dlp.exe (vollständiger Pfad erforderlich)
    yt_dlp_path = os.path.join(script_dir, "yt-dlp.exe")

    # Prüfe, ob yt-dlp.exe existiert
    if not os.path.exists(yt_dlp_path):
        print(f"Fehler: yt-dlp.exe wurde unter {yt_dlp_path} nicht gefunden.")
        return

    # Proxy-Einstellung (freiwillig)
    proxy = input("Gib die Proxy-Adresse ein (Drücke Enter, um keinen Proxy zu nutzen): ").strip()

    # Frage nach dem gewünschten Format mit Standardwert MP4
    format_choice = input("Möchtest du MP4 (Video) oder MP3 (Audio) herunterladen? (Drücke Enter für MP4): ").strip().lower()
    if not format_choice:
        format_choice = "mp4"

    # Zielordner für den Download
    command = [
        yt_dlp_path, "--ffmpeg-location", "ffmpeg.exe",
        "-o", os.path.join(output_folder, "%(title)s.%(ext)s")
    ]


    # Pfad zu ffmpeg (vollständiger Pfad erforderlich)
    ffmpeg_path = os.path.join(script_dir, "ffmpeg-7.1-essentials_build", "bin", "ffmpeg.exe")
    if not os.path.exists(ffmpeg_path):
        print(f"Fehler: FFmpeg wurde unter {ffmpeg_path} nicht gefunden.")
        return

    # yt-dlp-Befehl erstellen
    command = [yt_dlp_path, "--ffmpeg-location", ffmpeg_path, "-o", os.path.join(output_folder, "%(title)s.%(ext)s")]

    # Falls ein Proxy eingegeben wurde, hinzufügen
    if proxy:
        command.extend(["--proxy", proxy])

    # Format festlegen (MP4 oder MP3)
    if format_choice == "mp4":
         # Qualitätseinstellung vom Benutzer
        quality = input("Gib die gewünschte Videoqualität ein (z. B. 720, 1080, 1440). Drücke Enter für 1080p: ").strip()

        # Standardwert setzen (1080p), falls keine Eingabe
        if not quality.isdigit():
            quality = "1080"

           # Hier wurde die Zeile angepasst, um AAC anstelle von Opus zu erzwingen
        video_format = f"bestvideo[height<={quality}]+bestaudio[ext=m4a]/best"

        command.extend([
            "-f", video_format, "--merge-output-format", "mp4",
            "--throttled-rate", "1M",
            "--http-chunk-size", "10M",
            "--force-ipv4",
            "--geo-bypass"
        ])



    elif format_choice == "mp3":
        command.extend(["-f", "bestaudio", "--extract-audio", "--audio-format", "mp3"])
    else:
        print("Ungültige Auswahl! Bitte starte das Skript neu und wähle mp4 oder mp3.")
        return

    # URL hinzufügen
    command.append(youtube_url)

    # Download ausführen
    try:
        print("\nStarte Download...")
        subprocess.run(command, check=True)
        print("\nDownload abgeschlossen! Die Datei wurde gespeichert in:", output_folder)
    except FileNotFoundError:
        print("Fehler: yt-dlp.exe oder FFmpeg wurde nicht gefunden.")
    except subprocess.CalledProcessError as e:
        print(f"Ein Fehler ist beim Download aufgetreten: {e}")
    except Exception as e:
        print(f"Ein unerwarteter Fehler ist aufgetreten: {e}")

if __name__ == "__main__":
    main()
