import os
import sys
import subprocess
import threading
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

# ---------------- Funktionen ----------------
def choose_folder():
    folder = filedialog.askdirectory()
    if folder:
        output_var.set(folder)

def update_progress(process):
    for line in process.stdout:
        line = line.strip()
        if "%" in line:
            parts = line.split()
            for p in parts:
                if "%" in p:
                    try:
                        progress_value = float(p.replace("%", "").replace(",", "."))
                        progress_bar["value"] = progress_value
                        progress_label.config(text=f"Fortschritt: {progress_value:.1f}%")
                        root.update_idletasks()
                    except:
                        pass
        status_box.insert(tk.END, line + "\n")
        status_box.see(tk.END)

    progress_bar["value"] = 100
    progress_label.config(text="Download abgeschlossen ✅")
    messagebox.showinfo("Erfolg", f"Download abgeschlossen! Dateien gespeichert in: {output_var.get()}")

def download_video():
    youtube_url = url_entry.get().strip()
    if not youtube_url:
        messagebox.showerror("Fehler", "Bitte eine gültige YouTube-URL eingeben.")
        return
    
    format_choice = format_var.get()
    proxy = proxy_entry.get().strip()
    quality = quality_var.get()
    output_folder = output_var.get()
    if not output_folder:
        output_folder = os.path.join(os.path.expanduser("~"), "Downloads")
    os.makedirs(output_folder, exist_ok=True)
    
    yt_dlp_path = resource_path("yt-dlp.exe")
    ffmpeg_path = resource_path("ffmpeg.exe")
    
    if not os.path.exists(yt_dlp_path):
        messagebox.showerror("Fehler", "yt-dlp.exe wurde nicht gefunden!")
        return
    
    if not os.path.exists(ffmpeg_path):
        messagebox.showerror("Fehler", "ffmpeg.exe wurde nicht gefunden!")
        return
    
    command = [yt_dlp_path, "--ffmpeg-location", ffmpeg_path,
               "-o", os.path.join(output_folder, "%(title)s.%(ext)s"), "--progress"]
    
    if proxy:
        command.extend(["--proxy", proxy])
    
    format_options = {
        "mp4": f"bestvideo[height<={quality}]+bestaudio[ext=m4a]/best --remux-video mp4",
        "mp3": "bestaudio --extract-audio --audio-format mp3",
        "wav": "bestaudio --extract-audio --audio-format wav",
        "webm": f"bestvideo[height<={quality}]+bestaudio[ext=webm]/best",
        "mov": f"bestvideo[height<={quality}]+bestaudio[ext=m4a]/best --recode-video mov"
    }
    
    if format_choice in format_options:
        command.extend(["-f", format_options[format_choice]])
    else:
        messagebox.showerror("Fehler", "Ungültiges Format ausgewählt.")
        return
    
    command.extend(["--yes-playlist", youtube_url])
    
    try:
        progress_bar["value"] = 0
        progress_label.config(text="Starte Download...")
        status_box.delete(1.0, tk.END)

        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   text=True, bufsize=1, universal_newlines=True)
        threading.Thread(target=update_progress, args=(process,), daemon=True).start()
    except Exception as e:
        messagebox.showerror("Fehler", f"Ein Fehler ist aufgetreten: {e}")


# ---------------- GUI -----------------
root = tb.Window(themename="cosmo")
root.title("YouTube Downloader")
root.geometry("550x610")   # <--- Höhe angepasst

# URL
tb.Label(root, text="YouTube-URL oder Playlist-URL:").pack(pady=5)
url_entry = tb.Entry(root, width=50)
url_entry.pack()

# Format
tb.Label(root, text="Format wählen:").pack(pady=5)
format_var = tk.StringVar(value="mp4")
format_dropdown = tb.Combobox(root, textvariable=format_var,
                              values=["mp4", "mp3", "wav", "webm", "mov"], width=20)
format_dropdown.pack()

# Qualität
tb.Label(root, text="Qualität wählen:").pack(pady=5)
quality_var = tk.StringVar(value="1080")
quality_dropdown = tb.Combobox(root, textvariable=quality_var,
                               values=["144", "240", "360", "480", "720", "1080", "1440", "2160"], width=20)
quality_dropdown.pack()

# Zielordner
tb.Label(root, text="Speicherort:").pack(pady=5)
output_var = tk.StringVar(value=os.path.join(os.path.expanduser("~"), "Downloads"))
output_entry = tb.Entry(root, width=50, textvariable=output_var, state="readonly")
output_entry.pack()
tb.Button(root, text="Ordner auswählen", bootstyle="info", command=choose_folder).pack(pady=5)

# Proxy
tb.Label(root, text="Proxy (optional):").pack(pady=5)
proxy_entry = tb.Entry(root, width=50)
proxy_entry.pack()

# Button
tb.Button(root, text="Download starten", bootstyle="success",
          command=lambda: threading.Thread(target=download_video).start()).pack(pady=10)

# Fortschritt
progress_label = tb.Label(root, text="Noch kein Download gestartet")
progress_label.pack(pady=5)
progress_bar = tb.Progressbar(root, length=400, mode="determinate", bootstyle="success-striped")
progress_bar.pack(pady=5)

# Status-Box
status_box = tk.Text(root, height=12, width=60)   # etwas größer für mehr Infos
status_box.pack(pady=10)

root.mainloop()
