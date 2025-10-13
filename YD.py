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

# ---------------- Resource & Settings ----------------
def resource_path(relative_path):
    """Locate resources inside 'Necessary' folder"""
    base = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base, "Necessary", relative_path)

SETTINGS_FILE = resource_path("settings.json")
DEFAULT_SETTINGS = {
    "default_output": os.path.join(os.path.expanduser("~"), "Downloads"),
    "use_proxy": False,
    "proxy": "",
    "remux_mp4": True,
    "recode_mp4": False,
    "extract_audio": False,
    "theme": "cosmo",  # default light
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
        print("Error saving settings:", e)

settings = load_settings()

# ---------------- Globals ----------------
current_process = None
process_lock = threading.Lock()
stop_requested = False
start_time = None
elapsed_updater_id = None
eta_text = ""

# ---------------- Helpers ----------------
def get_video_info(url, format_choice, quality_choice):
    """Ask yt-dlp for estimated filesize"""
    yt_dlp_path = resource_path("yt-dlp.exe")
    if not os.path.exists(yt_dlp_path):
        return "yt-dlp.exe not found"

    # format string
    if format_choice == "mp4":
        fmt = f"bestvideo[height<={quality_choice}]+bestaudio[ext=m4a]/best"
    elif format_choice == "mp3":
        fmt = "bestaudio"
    elif format_choice == "wav":
        fmt = "bestaudio"
    elif format_choice == "webm":
        fmt = f"bestvideo[height<={quality_choice}]+bestaudio[ext=webm]/best"
    elif format_choice == "mov":
        fmt = f"bestvideo[height<={quality_choice}]+bestaudio[ext=m4a]/best"
    else:
        fmt = "best"

    try:
        result = subprocess.run(
            [yt_dlp_path, "--no-warnings", "-f", fmt, "--print", "%(filesize_approx)s", url],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        size_bytes = result.stdout.strip()
        if size_bytes.isdigit():
            size_mb = int(size_bytes) / (1024 * 1024)
            return f"Estimated size: {size_mb:.2f} MB"
        else:
            return "Size not available"
    except Exception as e:
        return f"Error getting info: {e}"

# ---------------- GUI Functions ----------------
def choose_output_folder():
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
    settings_win = tb.Toplevel(root)
    settings_win.title("Settings")
    settings_win.geometry("520x400")
    settings_win.transient(root)

    # Default folder
    tb.Label(settings_win, text="Default output folder:").pack(anchor="w", padx=10, pady=(12,0))
    df_frame = tb.Frame(settings_win)
    df_frame.pack(fill="x", padx=10)
    default_folder_entry = tb.Entry(df_frame, width=50, textvariable=default_folder_var, state="readonly")
    default_folder_entry.pack(side="left", padx=(0,8))
    tb.Button(df_frame, text="Change", bootstyle="info", command=choose_default_folder).pack(side="left")

    tb.Separator(settings_win).pack(fill="x", pady=8, padx=10)

    # Proxy
    proxy_frame = tb.Frame(settings_win)
    proxy_frame.pack(fill="x", padx=10)
    tb.Checkbutton(proxy_frame, text="Use proxy", variable=use_proxy_var, bootstyle="round-toggle").pack(anchor="w")
    tb.Label(proxy_frame, text="Proxy (http://user:pass@host:port):").pack(anchor="w", pady=(6,0))
    tb.Entry(proxy_frame, width=60, textvariable=proxy_var).pack(anchor="w", pady=(0,6))

    tb.Separator(settings_win).pack(fill="x", pady=8, padx=10)

    # Video settings
    tb.Label(settings_win, text="Video options:").pack(anchor="w", padx=10)
    tb.Checkbutton(settings_win, text="Auto remux to MP4 (fast, no re-encode)", variable=remux_var, bootstyle="round-toggle").pack(anchor="w", padx=20)
    tb.Checkbutton(settings_win, text="If remux fails: re-encode to MP4 (slow)", variable=recode_var, bootstyle="round-toggle").pack(anchor="w", padx=20, pady=(4,0))

    tb.Separator(settings_win).pack(fill="x", pady=8, padx=10)

    # Audio
    tb.Checkbutton(settings_win, text="Extract audio when MP3/WAV", variable=extract_audio_var, bootstyle="round-toggle").pack(anchor="w", padx=10)

    tb.Separator(settings_win).pack(fill="x", pady=8, padx=10)

    # Theme
    tb.Label(settings_win, text="Theme:").pack(anchor="w", padx=10)
    theme_combo = tb.Combobox(settings_win, values=["cosmo","flatly","darkly","cyborg","superhero","journal"], width=20)
    theme_combo.set(settings.get("theme", "cosmo"))
    theme_combo.pack(anchor="w", padx=20, pady=(0,8))

    def save_and_close():
        settings["default_output"] = default_folder_var.get()
        settings["use_proxy"] = bool(use_proxy_var.get())
        settings["proxy"] = proxy_var.get().strip()
        settings["remux_mp4"] = bool(remux_var.get())
        settings["recode_mp4"] = bool(recode_var.get())
        settings["extract_audio"] = bool(extract_audio_var.get())
        settings["theme"] = theme_combo.get()
        save_settings(settings)
        settings_win.destroy()
        root.style.theme_use(settings["theme"])

    tb.Button(settings_win, text="Save", bootstyle="primary", command=save_and_close).pack(side="right", padx=12, pady=12)
    tb.Button(settings_win, text="Cancel", bootstyle="light", command=settings_win.destroy).pack(side="right", pady=12)

def update_progress_reader(process):
    global current_process, stop_requested, eta_text
    try:
        for line in process.stdout:
            if stop_requested:
                break
            line = line.strip()
            if line:
                # Progress %
                if "%" in line:
                    parts = line.split()
                    for p in parts:
                        if "%" in p:
                            try:
                                val = float(p.replace("%","").replace(",",".")) 
                                root.after(0, lambda v=val: progress_bar.configure(value=v))
                                root.after(0, lambda v=val: progress_label.configure(text=f"Progress: {v:.1f}%"))
                            except:
                                pass
                # ETA
                if "ETA" in line:
                    for i,p in enumerate(line.split()):
                        if p == "ETA" and i+1 < len(line.split()):
                            eta_text = line.split()[i+1]
                            root.after(0, lambda: eta_label.configure(text=f"Remaining: {eta_text}"))
                # Console output
                root.after(0, lambda l=line: (status_box.insert(tk.END, l + "\n"), status_box.see(tk.END)))

        if not stop_requested:
            root.after(0, lambda: progress_bar.configure(value=100))
            root.after(0, lambda: progress_label.configure(text="Download finished ✅"))
            root.after(0, lambda: messagebox.showinfo("Success", f"Download finished! Saved to: {output_var.get()}"))
    finally:
        with process_lock:
            current_process = None
        root.after(0, lambda: download_toggle_button.configure(text="Start Download", bootstyle="success"))
        root.after(0, lambda: eta_label.configure(text="Remaining: --:--"))

def start_download_thread(command):
    global current_process
    try:
        proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, bufsize=1, universal_newlines=True)
        with process_lock:
            current_process = proc
        threading.Thread(target=update_progress_reader, args=(proc,), daemon=True).start()
    except Exception as e:
        messagebox.showerror("Error", f"Failed to start: {e}")

def stop_current_process():
    global current_process, stop_requested
    stop_requested = True
    with process_lock:
        proc = current_process
    if proc:
        try:
            proc.terminate()
            time.sleep(0.5)
            if proc.poll() is None:
                proc.kill()
        except:
            pass
    with process_lock:
        current_process = None

def download_toggle():
    global start_time, elapsed_updater_id, stop_requested
    with process_lock:
        running = current_process is not None
    if running:
        stop_requested = True
        stop_current_process()
        progress_label.configure(text="Cancelled")
        download_toggle_button.configure(text="Start Download", bootstyle="success")
        if elapsed_updater_id:
            root.after_cancel(elapsed_updater_id)
        return

    # Start new
    url = url_entry.get().strip()
    if not url:
        messagebox.showerror("Error", "Please enter a valid YouTube URL or playlist.")
        return

    # Get estimated size first
    info_text = get_video_info(url, format_var.get(), quality_var.get())
    messagebox.showinfo("Video Info", info_text)

    outdir = output_var.get() or settings["default_output"]
    os.makedirs(outdir, exist_ok=True)

    yt_dlp_path = resource_path("yt-dlp.exe")
    ffmpeg_path = resource_path("ffmpeg.exe")
    if not os.path.exists(yt_dlp_path) or not os.path.exists(ffmpeg_path):
        messagebox.showerror("Error", "yt-dlp.exe or ffmpeg.exe not found in 'Necessary' folder.")
        return

    command = [yt_dlp_path, "--ffmpeg-location", ffmpeg_path,
               "-o", os.path.join(outdir, "%(title)s.%(ext)s"), "--progress"]

    if use_proxy_var.get():
        proxy_value = proxy_var.get().strip()
        if proxy_value:
            command.extend(["--proxy", proxy_value])

    if format_var.get() == "mp4":
        if remux_var.get():
            command.extend(["-f", f"bestvideo[height<={quality_var.get()}]+bestaudio[ext=m4a]/best", "--remux-video", "mp4"])
        elif recode_var.get():
            command.extend(["-f", f"bestvideo[height<={quality_var.get()}]+bestaudio[ext=m4a]/best", "--recode-video", "mp4"])
        else:
            command.extend(["-f", f"bestvideo[height<={quality_var.get()}]+bestaudio[ext=m4a]/best"])
    elif format_var.get() == "mp3":
        command.extend(["-f","bestaudio","--extract-audio","--audio-format","mp3"])
    elif format_var.get() == "wav":
        command.extend(["-f","bestaudio","--extract-audio","--audio-format","wav"])
    elif format_var.get() == "webm":
        command.extend(["-f", f"bestvideo[height<={quality_var.get()}]+bestaudio[ext=webm]/best"])
    elif format_var.get() == "mov":
        command.extend(["-f", f"bestvideo[height<={quality_var.get()}]+bestaudio[ext=m4a]/best","--recode-video","mov"])

    command.append(url)

    progress_bar.configure(value=0)
    progress_label.configure(text="Starting...")
    status_box.delete(1.0, tk.END)
    download_toggle_button.configure(text="Stop (cancel)", bootstyle="danger-outline")
    stop_requested = False

    # start elapsed updater
    start_time = time.time()
    def update_elapsed():
        global elapsed_updater_id
        if start_time and not stop_requested:
            elapsed = int(time.time() - start_time)
            mins, secs = divmod(elapsed, 60)
            hours, mins = divmod(mins, 60)
            elapsed_label.configure(text=f"Elapsed: {hours:02d}:{mins:02d}:{secs:02d}")
            elapsed_updater_id = root.after(500, update_elapsed)
        else:
            elapsed_label.configure(text="Elapsed: 00:00:00")
    update_elapsed()

    threading.Thread(target=start_download_thread, args=(command,), daemon=True).start()

# ---------------- GUI ----------------
root = tb.Window(themename=settings.get("theme", "cosmo"))
root.title("YouTube Downloader")
root.geometry("550x610")

top_frame = tb.Frame(root)
top_frame.pack(fill="x", pady=(8, 0), padx=10)
tb.Label(top_frame, text="YouTube Downloader", font=("TkDefaultFont", 14, "bold")).pack(side="left")
tb.Button(top_frame, text="⚙️ Settings", bootstyle="light", command=open_settings).pack(side="right")

tb.Label(root, text="YouTube URL or Playlist URL:").pack(pady=(12, 4))
url_entry = tb.Entry(root, width=60)
url_entry.pack()

tb.Label(root, text="Format:").pack(pady=(10, 4))
format_var = tk.StringVar(value="mp4")
tb.Combobox(root, textvariable=format_var, values=["mp4", "mp3", "wav", "webm", "mov"], width=20).pack()

tb.Label(root, text="Quality:").pack(pady=(10, 4))
quality_var = tk.StringVar(value="1080")
tb.Combobox(root, textvariable=quality_var, values=["144", "240", "360", "480", "720", "1080", "1440", "2160"], width=20).pack()

tb.Label(root, text="Output folder:").pack(pady=(10, 4))
output_var = tk.StringVar(value=settings.get("default_output", DEFAULT_SETTINGS["default_output"]))
tb.Entry(root, width=60, textvariable=output_var, state="readonly").pack()
tb.Button(root, text="Choose folder", bootstyle="info", command=choose_output_folder).pack(pady=(6, 8))

download_toggle_button = tb.Button(root, text="Start Download", bootstyle="success", width=20, command=download_toggle)
download_toggle_button.pack(pady=(6, 6))

progress_label = tb.Label(root, text="No download yet")
progress_label.pack(pady=(6, 4))
progress_bar = tb.Progressbar(root, length=460, mode="determinate", bootstyle="success-striped")
progress_bar.pack()

elapsed_label = tb.Label(root, text="Elapsed: 00:00:00")
elapsed_label.pack(pady=(6, 2))
eta_label = tb.Label(root, text="Remaining: --:--")
eta_label.pack(pady=(0, 6))

status_box = tk.Text(root, height=12, width=70)
status_box.pack(pady=10)

# Settings variables
default_folder_var = tk.StringVar(value=settings["default_output"])
use_proxy_var = tk.IntVar(value=1 if settings["use_proxy"] else 0)
proxy_var = tk.StringVar(value=settings["proxy"])
remux_var = tk.IntVar(value=1 if settings["remux_mp4"] else 0)
recode_var = tk.IntVar(value=1 if settings["recode_mp4"] else 0)
extract_audio_var = tk.IntVar(value=1 if settings["extract_audio"] else 0)

def on_close():
    stop_current_process()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_close)
root.mainloop()