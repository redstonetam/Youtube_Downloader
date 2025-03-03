import os
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

def choose_folder():
    folder = filedialog.askdirectory()
    if folder:
        output_var.set(folder)

def update_progress(process):
    for line in process.stdout:
        if "ETA" in line or "%" in line:
            status_label.config(text=line.strip())
    status_label.config(text="Download abgeschlossen!")
    messagebox.showinfo("Erfolg", f"Download abgeschlossen! Dateien gespeichert in: {output_var.get()}")

def download_video():
    youtube_url = url_entry.get().strip()
    if not youtube_url:
        messagebox.showerror("Fehler", "Bitte eine gültige YouTube-URL oder Playlist-URL eingeben.")
        return
    
    format_choice = format_var.get()
    proxy = proxy_entry.get().strip()
    quality = quality_var.get()
    output_folder = output_var.get()
    if not output_folder:
        output_folder = os.path.join(os.path.expanduser("~"), "Downloads")
    os.makedirs(output_folder, exist_ok=True)
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    yt_dlp_path = os.path.join(script_dir, "yt-dlp.exe")
    ffmpeg_path = os.path.join(script_dir, "ffmpeg-7.1-essentials_build", "bin", "ffmpeg.exe")
    
    if not os.path.exists(yt_dlp_path):
        messagebox.showerror("Fehler", "yt-dlp.exe wurde nicht gefunden!")
        return
    
    if not os.path.exists(ffmpeg_path):
        messagebox.showerror("Fehler", "FFmpeg wurde nicht gefunden!")
        return
    
    command = [yt_dlp_path, "--ffmpeg-location", ffmpeg_path, "-o", os.path.join(output_folder, "%(title)s.%(ext)s"), "--progress"]
    
    if proxy:
        command.extend(["--proxy", proxy])
    
    format_options = {
        "mp4": f"bestvideo[height<={quality}]+bestaudio[ext=m4a]/best",
        "mp3": "bestaudio --extract-audio --audio-format mp3",
        "wav": "bestaudio --extract-audio --audio-format wav",
        "flac": "bestaudio --extract-audio --audio-format flac",
        "webm": f"bestvideo[height<={quality}]+bestaudio[ext=webm]/best",
        "mov": f"bestvideo[height<={quality}]+bestaudio[ext=m4a]/best --recode-video mov"
    }
    
    if format_choice in format_options:
        command.extend(["-f", format_options[format_choice]])
        if format_choice == "mov":
            command.append("--recode-video"); command.append("mov")
    else:
        messagebox.showerror("Fehler", "Ungültiges Format ausgewählt.")
        return
    
    command.extend(["--yes-playlist", youtube_url])
    
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True)
        threading.Thread(target=update_progress, args=(process,), daemon=True).start()
    except Exception as e:
        messagebox.showerror("Fehler", f"Ein Fehler ist aufgetreten: {e}")

# GUI erstellen
root = tk.Tk()
root.title("YouTube Downloader")
root.geometry("400x400")

# URL-Eingabe
url_label = tk.Label(root, text="YouTube-URL oder Playlist-URL:")
url_label.pack()
url_entry = tk.Entry(root, width=50)
url_entry.pack()

# Format-Auswahl
format_label = tk.Label(root, text="Format wählen:")
format_label.pack()
format_var = tk.StringVar(value="mp4")
format_dropdown = ttk.Combobox(root, textvariable=format_var, values=["mp4", "mp3", "wav", "flac", "webm", "mov"])
format_dropdown.pack()

# Qualität-Auswahl
quality_label = tk.Label(root, text="Qualität wählen:")
quality_label.pack()
quality_var = tk.StringVar(value="1080")
quality_dropdown = ttk.Combobox(root, textvariable=quality_var, values=["144", "240", "360", "480", "720", "1080", "1440", "2160"])
quality_dropdown.pack()

# Zielordner-Auswahl
output_label = tk.Label(root, text="Speicherort wählen:")
output_label.pack()
output_var = tk.StringVar(value=os.path.join(os.path.expanduser("~"), "Downloads"))
output_entry = tk.Entry(root, width=50, textvariable=output_var, state="readonly")
output_entry.pack()
choose_folder_button = tk.Button(root, text="Ordner auswählen", command=choose_folder)
choose_folder_button.pack()

# Proxy-Eingabe
proxy_label = tk.Label(root, text="Proxy (optional):")
proxy_label.pack()
proxy_entry = tk.Entry(root, width=50)
proxy_entry.pack()

# Download-Button
download_button = tk.Button(root, text="Download starten", command=download_video)
download_button.pack()

# Status-Anzeige
status_label = tk.Label(root, text="")
status_label.pack()

root.mainloop()
