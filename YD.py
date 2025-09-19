import os
import sys
import subprocess
import threading
import time
import json
import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as tb
from ttkbootstrap.constants import *

# ---------------- Ressourcen für PyInstaller ----------------
def resource_path(relative_path):
    """Pfad zu eingebetteten Dateien im PyInstaller-Bundle oder normalem Ordner"""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# ---------------- Settings (persistiert) ----------------
SETTINGS_FILE = resource_path("settings.json")
DEFAULT_SETTINGS = {
    "default_output": os.path.join(os.path.expanduser("~"), "Downloads"),
    "use_proxy": False,
    "proxy": "",
    "remux_mp4": True,
    "recode_mp4": False,
    "extract_audio": False
}

def load_settings():
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {**DEFAULT_SETTINGS, **data}
    except Exception:
        pass
    return DEFAULT_SETTINGS.copy()

def save_settings(s):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(s, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print("Fehler beim Speichern der Einstellungen:", e)

settings = load_settings()

# ---------------- Globals für Download-Management ----------------
current_process = None
process_lock = threading.Lock()
stop_requested = False
start_time = None
elapsed_updater_id = None

# ---------------- GUI-Funktionen ----------------
def choose_folder_for_main():
    folder = filedialog.askdirectory(initialdir=settings.get("default_output", DEFAULT_SETTINGS["default_output"]))
    if folder:
        output_var.set(folder)

def choose_default_folder():
    folder = filedialog.askdirectory(initialdir=settings.get("default_output", DEFAULT_SETTINGS["default_output"]))
    if folder:
        settings["default_output"] = folder
        save_settings(settings)
        default_folder_var.set(folder)

def open_settings():
    # kleines Einstellungsfenster (modal)
    settings_win = tb.Toplevel(root)
    settings_win.title("Einstellungen")
    settings_win.geometry("520x320")
    settings_win.transient(root)

    # Default Ordner
    tb.Label(settings_win, text="Standard-Speicherordner:").pack(anchor="w", padx=10, pady=(12,0))
    df_frame = tb.Frame(settings_win)
    df_frame.pack(fill="x", padx=10)
    default_folder_entry = tb.Entry(df_frame, width=50, textvariable=default_folder_var, state="readonly")
    default_folder_entry.pack(side="left", padx=(0,8))
    tb.Button(df_frame, text="Ändern", bootstyle="info", command=choose_default_folder).pack(side="left")

    # Proxy
    tb.Separator(settings_win).pack(fill="x", pady=8, padx=10)
    proxy_frame = tb.Frame(settings_win)
    proxy_frame.pack(fill="x", padx=10)
    use_proxy_chk = tb.Checkbutton(proxy_frame, text="Proxy verwenden", variable=use_proxy_var, bootstyle="round-toggle")
    use_proxy_chk.pack(anchor="w")
    tb.Label(proxy_frame, text="Proxy (z. B. http://user:pass@host:port):").pack(anchor="w", pady=(6,0))
    proxy_entry_settings = tb.Entry(proxy_frame, width=60, textvariable=proxy_var)
    proxy_entry_settings.pack(anchor="w", pady=(0,6))

    # Remux / Recode Optionen
    tb.Separator(settings_win).pack(fill="x", pady=8, padx=10)
    tb.Label(settings_win, text="Video Ausgabe-Einstellungen:").pack(anchor="w", padx=10)
    remux_frame = tb.Frame(settings_win)
    remux_frame.pack(fill="x", padx=10)
    tb.Checkbutton(remux_frame, text="Auto remux nach MP4 (schnell, kein Rekodieren)", variable=remux_var, bootstyle="round-toggle").pack(anchor="w")
    tb.Checkbutton(remux_frame, text="Falls remux nicht möglich: recode nach MP4 (dauert länger)", variable=recode_var, bootstyle="round-toggle").pack(anchor="w", pady=(4,0))

    # Extract audio
    tb.Separator(settings_win).pack(fill="x", pady=8, padx=10)
    tb.Checkbutton(settings_win, text="Beim Audio-Format: Audio extrahieren (mp3/wav)", variable=extract_audio_var, bootstyle="round-toggle").pack(anchor="w", padx=10)

    # Save + Close
    def save_and_close():
        settings["default_output"] = default_folder_var.get()
        settings["use_proxy"] = bool(use_proxy_var.get())
        settings["proxy"] = proxy_var.get().strip()
        settings["remux_mp4"] = bool(remux_var.get())
        settings["recode_mp4"] = bool(recode_var.get())
        settings["extract_audio"] = bool(extract_audio_var.get())
        save_settings(settings)
        settings_win.destroy()

    tb.Button(settings_win, text="Speichern", bootstyle="primary", command=save_and_close).pack(side="right", padx=12, pady=12)
    tb.Button(settings_win, text="Abbrechen", bootstyle="light", command=settings_win.destroy).pack(side="right", pady=12)

def update_progress_reader(process):
    """Liest stdout des Subprozesses und schreibt in Statusbox; respektiert stop_requested"""
    global current_process, stop_requested
    try:
        for line in process.stdout:
            if stop_requested:
                break
            line = line.strip()
            if line:
                # Fortschritt aus Zeile extrahieren
                if "%" in line:
                    parts = line.split()
                    for p in parts:
                        if "%" in p:
                            try:
                                progress_value = float(p.replace("%", "").replace(",", "."))
                                root.after(0, lambda v=progress_value: progress_bar.configure(value=v))
                                root.after(0, lambda v=progress_value: progress_label.configure(text=f"Fortschritt: {v:.1f}%"))
                            except:
                                pass
                # Zeile in Textbox einfügen
                root.after(0, lambda l=line: (status_box.insert(tk.END, l + "\n"), status_box.see(tk.END)))
        # falls beendet ohne Stop
        if not stop_requested:
            root.after(0, lambda: progress_bar.configure(value=100))
            root.after(0, lambda: progress_label.configure(text="Download abgeschlossen ✅"))
            root.after(0, lambda: messagebox.showinfo("Erfolg", f"Download abgeschlossen! Dateien gespeichert in: {output_var.get()}"))
    except Exception as e:
        root.after(0, lambda: messagebox.showerror("Fehler", f"Update-Thread Fehler: {e}"))
    finally:
        with process_lock:
            current_process = None
        # Reset toggle state (Button auf "Start" setzen)
        root.after(0, lambda: download_toggle_button.configure(text="Download starten", bootstyle="success"))

def start_download_thread(command):
    global current_process, stop_requested
    stop_requested = False
    try:
        # Start subprocess
        proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True)
        with process_lock:
            current_process = proc
        threading.Thread(target=update_progress_reader, args=(proc,), daemon=True).start()
    except Exception as e:
        root.after(0, lambda: messagebox.showerror("Fehler", f"Fehler beim Starten des Downloads: {e}"))
        with process_lock:
            current_process = None
        root.after(0, lambda: download_toggle_button.configure(text="Download starten", bootstyle="success"))

def stop_current_process():
    global current_process, stop_requested
    stop_requested = True
    with process_lock:
        proc = current_process
    if proc:
        try:
            proc.terminate()
            # Warte kurz, dann kill falls nötig
            time.sleep(0.5)
            if proc.poll() is None:
                proc.kill()
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
    with process_lock:
        current_process = None

def download_toggle():
    global start_time, elapsed_updater_id, stop_requested
    with process_lock:
        running = current_process is not None

    if running:
        # Stop requested
        stop_requested = True
        stop_current_process()
        progress_label.configure(text="Abgebrochen")
        download_toggle_button.configure(text="Download starten", bootstyle="success")
        if elapsed_updater_id:
            root.after_cancel(elapsed_updater_id)
    else:
        # Start new download
        youtube_url = url_entry.get().strip()
        if not youtube_url:
            messagebox.showerror("Fehler", "Bitte eine gültige YouTube-URL oder Playlist-URL eingeben.")
            return

        # Einstellungen sammeln
        format_choice = format_var.get()
        output_folder = output_var.get() or settings.get("default_output", DEFAULT_SETTINGS["default_output"])
        os.makedirs(output_folder, exist_ok=True)

        # Pfade zu eingebetteten Exes
        yt_dlp_path = resource_path("yt-dlp.exe")
        ffmpeg_path = resource_path("ffmpeg.exe")

        if not os.path.exists(yt_dlp_path):
            messagebox.showerror("Fehler", "yt-dlp.exe wurde nicht gefunden!")
            return

        if not os.path.exists(ffmpeg_path):
            messagebox.showerror("Fehler", "ffmpeg.exe wurde nicht gefunden!")
            return

        # build command
        command = [yt_dlp_path, "--ffmpeg-location", ffmpeg_path, "-o", os.path.join(output_folder, "%(title)s.%(ext)s"), "--progress"]
        # Proxy
        if use_proxy_var.get():
            proxy_value = proxy_var.get().strip()
            if proxy_value:
                command.extend(["--proxy", proxy_value])
        # Format-Optionen
        if format_choice == "mp4":
            if remux_var.get():
                command.extend(["-f", f"bestvideo[height<={quality_var.get()}]+bestaudio[ext=m4a]/best", "--remux-video", "mp4"])
            elif recode_var.get():
                command.extend(["-f", f"bestvideo[height<={quality_var.get()}]+bestaudio[ext=m4a]/best", "--recode-video", "mp4"])
            else:
                command.extend(["-f", f"bestvideo[height<={quality_var.get()}]+bestaudio[ext=m4a]/best"])
        elif format_choice == "mp3":
            command.extend(["-f", "bestaudio", "--extract-audio", "--audio-format", "mp3"])
        elif format_choice == "wav":
            command.extend(["-f", "bestaudio", "--extract-audio", "--audio-format", "wav"])
        elif format_choice == "webm":
            command.extend(["-f", f"bestvideo[height<={quality_var.get()}]+bestaudio[ext=webm]/best"])
        elif format_choice == "mov":
            command.extend(["-f", f"bestvideo[height<={quality_var.get()}]+bestaudio[ext=m4a]/best", "--recode-video", "mov"])
        else:
            messagebox.showerror("Fehler", "Ungültiges Format ausgewählt.")
            return

        # *** WICHTIG: URL anfügen (sonst ruft yt-dlp nichts zum Herunterladen auf) ***
        command.append(youtube_url)
        # Wenn du Playlists automatisch bestätigen willst, statt append kannst du:
        # command.extend(["--yes-playlist", youtube_url])

        # (Optional) Debug: zeige den kompletten Befehl in der Status-Box
        # status_box.insert(tk.END, "Command: " + " ".join(command) + "\n")

        # UI vorbereiten
        progress_bar.configure(value=0)
        progress_label.configure(text="Starte Download...")
        status_box.delete(1.0, tk.END)
        download_toggle_button.configure(text="Stopp (abbrechen)", bootstyle="danger-outline")
        stop_requested = False

        # start time for elapsed
        start_time = time.time()
        def update_elapsed():
            global elapsed_updater_id
            if start_time and (not stop_requested):
                elapsed = int(time.time() - start_time)
                mins, secs = divmod(elapsed, 60)
                hours, mins = divmod(mins, 60)
                elapsed_label.configure(text=f"Verstrichene Zeit: {hours:02d}:{mins:02d}:{secs:02d}")
                elapsed_updater_id = root.after(500, update_elapsed)
            else:
                elapsed_label.configure(text="Verstrichene Zeit: 00:00:00")
        update_elapsed()

        # Starten
        threading.Thread(target=start_download_thread, args=(command,), daemon=True).start()

# ---------------- GUI -----------------
root = tb.Window(themename="cosmo")
root.title("YouTube Downloader")
root.geometry("550x610")   # Höhe wie gewünscht

# obere Leiste: Zahnrad (Einstellungen)
top_frame = tb.Frame(root)
top_frame.pack(fill="x", pady=(8,0), padx=10)
tb.Label(top_frame, text="YouTube Downloader", font=("TkDefaultFont", 14, "bold")).pack(side="left")
tb.Button(top_frame, text="⚙️ Einstellungen", bootstyle="light", command=open_settings).pack(side="right")

# URL
tb.Label(root, text="YouTube-URL oder Playlist-URL:").pack(pady=(12,4))
url_entry = tb.Entry(root, width=60)
url_entry.pack()

# Format
tb.Label(root, text="Format wählen:").pack(pady=(10,4))
format_var = tk.StringVar(value="mp4")
format_dropdown = tb.Combobox(root, textvariable=format_var, values=["mp4", "mp3", "wav", "webm", "mov"], width=20)
format_dropdown.pack()

# Qualität
tb.Label(root, text="Qualität wählen:").pack(pady=(10,4))
quality_var = tk.StringVar(value="1080")
quality_dropdown = tb.Combobox(root, textvariable=quality_var, values=["144", "240", "360", "480", "720", "1080", "1440", "2160"], width=20)
quality_dropdown.pack()

# Zielordner (Hauptansicht)
tb.Label(root, text="Speicherort:").pack(pady=(10,4))
output_var = tk.StringVar(value=settings.get("default_output", DEFAULT_SETTINGS["default_output"]))
output_entry = tb.Entry(root, width=60, textvariable=output_var, state="readonly")
output_entry.pack()
tb.Button(root, text="Ordner auswählen", bootstyle="info", command=choose_folder_for_main).pack(pady=(6,8))

# Download Toggle Button (über Progressbar)
download_toggle_button = tb.Button(root, text="Download starten", bootstyle="success", width=20, command=download_toggle)
download_toggle_button.pack(pady=(6,6))

# Fortschritt
progress_label = tb.Label(root, text="Noch kein Download gestartet")
progress_label.pack(pady=(6,4))
progress_bar = tb.Progressbar(root, length=460, mode="determinate", bootstyle="success-striped")
progress_bar.pack()

# Elapsed time unter der Fortschrittsleiste
elapsed_label = tb.Label(root, text="Verstrichene Zeit: 00:00:00")
elapsed_label.pack(pady=(6,4))

# Status-Box
status_box = tk.Text(root, height=12, width=70)
status_box.pack(pady=10)

# ---------------- Settings vars (GUI und persistent) ----------------
default_folder_var = tk.StringVar(value=settings.get("default_output", DEFAULT_SETTINGS["default_output"]))
use_proxy_var = tk.IntVar(value=1 if settings.get("use_proxy") else 0)
proxy_var = tk.StringVar(value=settings.get("proxy", ""))
remux_var = tk.IntVar(value=1 if settings.get("remux_mp4") else 0)
recode_var = tk.IntVar(value=1 if settings.get("recode_mp4") else 0)
extract_audio_var = tk.IntVar(value=1 if settings.get("extract_audio") else 0)

# Diese GUI-Variablen werden im Einstellungsdialog gebunden:
# (proxy_var, default_folder_var etc. sind bereits definiert)
# Aber wir wollen auch Änderungen sofort sichtbar machen: binde proxy->proxy_entry in main wäre optional.

# Wenn Fenster geschlossen wird, speichere Einstellungen
def on_close():
    # speichere aktuelle Einstellungen (zum Beispiel falls man sie im Einstellungsfenster geändert hat)
    settings["default_output"] = default_folder_var.get()
    settings["use_proxy"] = bool(use_proxy_var.get())
    settings["proxy"] = proxy_var.get().strip()
    settings["remux_mp4"] = bool(remux_var.get())
    settings["recode_mp4"] = bool(recode_var.get())
    settings["extract_audio"] = bool(extract_audio_var.get())
    save_settings(settings)
    # stoppe Prozess falls noch laufend
    stop_current_process()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_close)

# ---------------- Start GUI -----------------
root.mainloop()
