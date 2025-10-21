import os
import sys
import json
import threading
import time
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as tb
from ttkbootstrap import ttk
from ttkbootstrap.constants import *

# ---------------- Resource & Settings ----------------
def resource_path(relative_path):
    """
    Gibt den Pfad zur Ressource zurück.
    Wenn das Script gebündelt ist (pyinstaller --onefile), benutzt es sys._MEIPASS.
    Bei normaler Ausführung referenziert es den lokalen Ordner und den "Necessary"-Unterordner.
    """
    try:
        base = sys._MEIPASS  # PyInstaller temp folder
    except Exception:
        base = os.path.abspath(os.path.dirname(__file__))
    # Settings & executables liegen im Necessary-Ordner
    return os.path.join(base, "Necessary", relative_path)

# SETTINGS_FILE liegt im Necessary-Ordner (wie gewünscht)
SETTINGS_FILE = resource_path("settings.json")
DEFAULT_SETTINGS = {
    "default_output": os.path.join(os.path.expanduser("~"), "Downloads"),
    "use_proxy": False,
    "proxy": "",
    "remux_mp4": True,
    "recode_mp4": False,
    "extract_audio": False,
    "theme": "cosmo",
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
        # Stelle sicher, dass Necessary-Ordner existiert (z. B. beim ersten Start)
        settings_dir = os.path.dirname(SETTINGS_FILE)
        os.makedirs(settings_dir, exist_ok=True)
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(s, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print("Error saving settings:", e)

settings = load_settings()

# ---------------- Globals ----------------
current_process = None
process_lock = threading.Lock()
stop_requested = False
paused = False
last_command = None
start_time = None
elapsed_updater_id = None
eta_text = ""

# ---------------- Helpers ----------------
def get_video_info(url, format_choice, quality_choice):
    # Optional helper - jetzt nicht automatisch aufgerufen
    yt_dlp_path = resource_path("yt-dlp.exe")
    if not os.path.exists(yt_dlp_path):
        return "yt-dlp.exe not found"

    if format_choice == "mp4":
        fmt = f"bestvideo[height<={quality_choice}]+bestaudio[ext=m4a]/best"
    elif format_choice in ("mp3", "wav"):
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
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=15
        )
        size_bytes = result.stdout.strip()
        if size_bytes.isdigit():
            size_mb = int(size_bytes) / (1024 * 1024)
            return f"Estimated size: {size_mb:.2f} MB"
        else:
            return "Size not available"
    except subprocess.TimeoutExpired:
        return "Unable to fetch size (timeout)"
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
    settings_win.geometry("520x500")
    settings_win.transient(root)

    ttk.Label(settings_win, text="Default output folder:").pack(anchor="w", padx=10, pady=(12,0))
    df_frame = ttk.Frame(settings_win)
    df_frame.pack(fill="x", padx=10)
    default_folder_entry = ttk.Entry(df_frame, width=50, textvariable=default_folder_var, state="readonly")
    default_folder_entry.pack(side="left", padx=(0,8))
    ttk.Button(df_frame, text="Change", bootstyle="info", command=choose_default_folder).pack(side="left")

    ttk.Separator(settings_win).pack(fill="x", pady=8, padx=10)

    proxy_frame = ttk.Frame(settings_win)
    proxy_frame.pack(fill="x", padx=10)
    ttk.Checkbutton(proxy_frame, text="Use proxy", variable=use_proxy_var, bootstyle="round-toggle").pack(anchor="w")
    ttk.Label(proxy_frame, text="Proxy (http://user:pass@host:port):").pack(anchor="w", pady=(6,0))
    ttk.Entry(proxy_frame, width=60, textvariable=proxy_var).pack(anchor="w", pady=(0,6))

    ttk.Separator(settings_win).pack(fill="x", pady=8, padx=10)

    ttk.Label(settings_win, text="Video options:").pack(anchor="w", padx=10)
    ttk.Checkbutton(settings_win, text="Auto remux to MP4 (fast, no re-encode)", variable=remux_var, bootstyle="round-toggle").pack(anchor="w", padx=20)
    ttk.Checkbutton(settings_win, text="If remux fails: re-encode to MP4 (slow)", variable=recode_var, bootstyle="round-toggle").pack(anchor="w", padx=20, pady=(4,0))

    ttk.Separator(settings_win).pack(fill="x", pady=8, padx=10)

    ttk.Checkbutton(settings_win, text="Extract audio when MP3/WAV", variable=extract_audio_var, bootstyle="round-toggle").pack(anchor="w", padx=10)

    ttk.Separator(settings_win).pack(fill="x", pady=8, padx=10)

    ttk.Label(settings_win, text="Theme:").pack(anchor="w", padx=10)
    theme_combo = ttk.Combobox(settings_win, values=["cosmo","flatly","darkly","cyborg","superhero","journal"], width=20)
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
        # apply theme
        try:
            root.style.theme_use(settings["theme"])
        except Exception:
            pass

    ttk.Button(settings_win, text="Save", bootstyle="primary", command=save_and_close).pack(side="right", padx=12, pady=12)
    ttk.Button(settings_win, text="Cancel", bootstyle="light", command=settings_win.destroy).pack(side="right", pady=12)

# ---------------- Process / Download handling ----------------
def update_progress_reader(process):
    global current_process, stop_requested, eta_text, elapsed_updater_id, start_time
    try:
        for line in process.stdout:
            if stop_requested:
                break
            line = line.rstrip()
            if not line:
                continue

            # show console output in UI
            root.after(0, lambda l=line: (status_box.insert(tk.END, l + "\n"), status_box.see(tk.END)))

            # progress %
            if "%" in line:
                parts = line.split()
                for p in parts:
                    if "%" in p:
                        try:
                            val = float(p.replace("%","").replace(",","").replace("%",""))
                            root.after(0, lambda v=val: progress_bar.configure(value=v))
                            root.after(0, lambda v=val: progress_label.configure(text=f"Progress: {v:.1f}%"))
                        except Exception:
                            pass

            # ETA
            if "ETA" in line:
                tokens = line.split()
                for i,tok in enumerate(tokens):
                    if tok == "ETA" and i+1 < len(tokens):
                        eta_text = tokens[i+1]
                        root.after(0, lambda: eta_label.configure(text=f"Remaining: {eta_text}"))

        # finished normally (if not paused)
        if not stop_requested and not paused:
            root.after(0, lambda: progress_bar.configure(value=100))
            root.after(0, lambda: progress_label.configure(text="Download finished ✅"))
            # Optional: kleine Info (kann entfernt werden, wenn gewünscht)
            try:
                root.after(0, lambda: messagebox.showinfo("Success", f"Download finished! Saved to: {output_var.get()}"))
            except Exception:
                pass

            # Stoppe Zeitmesser nach Abschluss
            if elapsed_updater_id:
                try:
                    root.after_cancel(elapsed_updater_id)
                except Exception:
                    pass
                elapsed_updater_id = None
            start_time = None
    finally:
        with process_lock:
            current_process = None
        root.after(0, lambda: pause_resume_button.configure(text="Start Download", bootstyle="success"))
        root.after(0, lambda: eta_label.configure(text="Remaining: --:--"))

def start_download_thread(command):
    global current_process
    try:
        # Unsichtbares Fenster (kein CMD beim Download)
        startupinfo = None
        creationflags = 0
        if os.name == "nt":
            try:
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            except Exception:
                startupinfo = None
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

        proc = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
            startupinfo=startupinfo,
            creationflags=creationflags
        )
        with process_lock:
            current_process = proc
        threading.Thread(target=update_progress_reader, args=(proc,), daemon=True).start()
    except Exception as e:
        messagebox.showerror("Error", f"Failed to start: {e}")

def stop_current_process(kill=False):
    global current_process, stop_requested
    stop_requested = True
    with process_lock:
        proc = current_process
    if proc:
        try:
            proc.terminate()
            time.sleep(0.5)
            if proc.poll() is None and kill:
                proc.kill()
        except Exception:
            pass
    with process_lock:
        current_process = None

# ---------------- Pause / Resume / Cancel logic ----------------
def pause_or_resume():
    """
    Button state machine:
    - "Start Download": start anew
    - "Pause": terminate running process but keep last_command for resume
    - "Resume": start process again using last_command (if available)
    """
    global paused, stop_requested, last_command, start_time, elapsed_updater_id

    state = pause_resume_button.cget("text")

    # If currently running -> Pause
    if state == "Pause":
        if current_process:
            stop_requested = True
            # do not destroy last_command; we intend to resume
            stop_current_process(kill=False)
            paused = True
            pause_resume_button.configure(text="Resume", bootstyle="warning")
            progress_label.configure(text="Paused")
            # stop elapsed timer but keep elapsed value
            if elapsed_updater_id:
                try:
                    root.after_cancel(elapsed_updater_id)
                except Exception:
                    pass
            return

    # If currently paused -> Resume
    if state == "Resume":
        if last_command:
            stop_requested = False
            paused = False
            pause_resume_button.configure(text="Pause", bootstyle="danger-outline")
            progress_label.configure(text="Resuming...")
            # restart elapsed timer
            if start_time is None:
                start_time = time.time()
            def update_elapsed():
                global elapsed_updater_id
                if start_time and not stop_requested and not paused:
                    elapsed = int(time.time() - start_time)
                    mins, secs = divmod(elapsed, 60)
                    hours, mins = divmod(mins, 60)
                    elapsed_label.configure(text=f"Elapsed: {hours:02d}:{mins:02d}:{secs:02d}")
                    elapsed_updater_id = root.after(500, update_elapsed)
                else:
                    # don't reset to 00:00:00 here; keep last shown value
                    pass
            update_elapsed()
            threading.Thread(target=start_download_thread, args=(last_command,), daemon=True).start()
        else:
            messagebox.showwarning("Resume", "No previous download command to resume.")
        return

    # If starting from idle -> Start Download
    if state in ("Start Download", "Start"):
        url = url_entry.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a valid YouTube URL or playlist.")
            return

        # check executables
        yt_dlp_path = resource_path("yt-dlp.exe")
        ffmpeg_path = resource_path("ffmpeg.exe")
        if not os.path.exists(yt_dlp_path) or not os.path.exists(ffmpeg_path):
            messagebox.showerror("Error", "yt-dlp.exe or ffmpeg.exe not found in 'Necessary' folder.")
            return

        # --- Entfernt: keine Video-Info-Abfrage / kein Popup mehr ---

        outdir = output_var.get() or settings["default_output"]
        os.makedirs(outdir, exist_ok=True)

        command = build_command(url, outdir)

        # record last_command for resume
        last_command = command.copy()

        # reset UI and start
        progress_bar.configure(value=0, maximum=100, mode="determinate")
        progress_label.configure(text="Starting...")
        status_box.delete(1.0, tk.END)
        pause_resume_button.configure(text="Pause", bootstyle="danger-outline")
        cancel_button.configure(state="normal")
        start_time = time.time()
        stop_requested = False
        paused = False

        # start elapsed updater
        def update_elapsed():
            global elapsed_updater_id
            if start_time and not stop_requested and not paused:
                elapsed = int(time.time() - start_time)
                mins, secs = divmod(elapsed, 60)
                hours, mins = divmod(mins, 60)
                elapsed_label.configure(text=f"Elapsed: {hours:02d}:{mins:02d}:{secs:02d}")
                elapsed_updater_id = root.after(500, update_elapsed)
            else:
                # keep last shown time when paused/stopped
                pass
        update_elapsed()

        threading.Thread(target=start_download_thread, args=(command,), daemon=True).start()
        return

def cancel_download():
    """
    Cancel: kill process and clear last_command (so Resume won't work).
    """
    global paused, last_command, stop_requested, start_time, elapsed_updater_id
    if current_process:
        stop_requested = True
        stop_current_process(kill=True)
    paused = False
    last_command = None
    pause_resume_button.configure(text="Start Download", bootstyle="success")
    cancel_button.configure(state="disabled")
    progress_label.configure(text="Cancelled")
    try:
        if elapsed_updater_id:
            root.after_cancel(elapsed_updater_id)
    except Exception:
        pass
    elapsed_updater_id = None
    start_time = None

# ---------------- Command builder ----------------
def build_command(url, outdir):
    yt_dlp_path = resource_path("yt-dlp.exe")
    ffmpeg_path = resource_path("ffmpeg.exe")
    cmd = [yt_dlp_path, "--ffmpeg-location", ffmpeg_path, "-o", os.path.join(outdir, "%(title)s.%(ext)s"), "--progress"]

    if use_proxy_var.get():
        proxy_value = proxy_var.get().strip()
        if proxy_value:
            cmd.extend(["--proxy", proxy_value])

    fmt = format_var.get()
    q = quality_var.get()

    if fmt == "mp4":
        if remux_var.get():
            cmd.extend(["-f", f"bestvideo[height<={q}]+bestaudio[ext=m4a]/best", "--remux-video", "mp4"])
        elif recode_var.get():
            cmd.extend(["-f", f"bestvideo[height<={q}]+bestaudio[ext=m4a]/best", "--recode-video", "mp4"])
        else:
            cmd.extend(["-f", f"bestvideo[height<={q}]+bestaudio[ext=m4a]/best"])
    elif fmt == "mp3":
        cmd.extend(["-f", "bestaudio", "--extract-audio", "--audio-format", "mp3"])
    elif fmt == "wav":
        cmd.extend(["-f", "bestaudio", "--extract-audio", "--audio-format", "wav"])
    elif fmt == "webm":
        cmd.extend(["-f", f"bestvideo[height<={q}]+bestaudio[ext=webm]/best"])
    elif fmt == "mov":
        cmd.extend(["-f", f"bestvideo[height<={q}]+bestaudio[ext=m4a]/best", "--recode-video", "mov"])

    cmd.append(url)
    return cmd

# ---------------- GUI ----------------
root = tb.Window(themename=settings.get("theme", "cosmo"))
root.title("YouTube Downloader")
root.geometry("640x720")

top_frame = ttk.Frame(root)
top_frame.pack(fill="x", pady=(8, 0), padx=10)
ttk.Label(top_frame, text="YouTube Downloader", font=("TkDefaultFont", 14, "bold")).pack(side="left")
ttk.Button(top_frame, text="⚙️ Settings", bootstyle="light", command=open_settings).pack(side="right")

ttk.Label(root, text="YouTube URL or Playlist URL:").pack(pady=(12, 4))
url_entry = ttk.Entry(root, width=70)
url_entry.pack()

ttk.Label(root, text="Format:").pack(pady=(10, 4))
format_var = tk.StringVar(value="mp4")
ttk.Combobox(root, textvariable=format_var, values=["mp4", "mp3", "wav", "webm", "mov"], width=20).pack()

ttk.Label(root, text="Quality:").pack(pady=(10, 4))
quality_var = tk.StringVar(value="1080")
ttk.Combobox(root, textvariable=quality_var, values=["144", "240", "360", "480", "720", "1080", "1440", "2160"], width=20).pack()

ttk.Label(root, text="Output folder:").pack(pady=(10, 4))
output_var = tk.StringVar(value=settings.get("default_output", DEFAULT_SETTINGS["default_output"]))
ttk.Entry(root, width=60, textvariable=output_var, state="readonly").pack()
ttk.Button(root, text="Choose folder", bootstyle="info", command=choose_output_folder).pack(pady=(6, 8))

# Pause/Resume + Cancel buttons
button_frame = ttk.Frame(root)
button_frame.pack(pady=(6,6))
pause_resume_button = ttk.Button(button_frame, text="Start Download", bootstyle="success", width=18, command=pause_or_resume)
pause_resume_button.pack(side="left", padx=(0,8))
cancel_button = ttk.Button(button_frame, text="Cancel", bootstyle="danger", width=12, command=cancel_download, state="disabled")
cancel_button.pack(side="left")

progress_label = ttk.Label(root, text="No download yet")
progress_label.pack(pady=(6, 4))
progress_bar = ttk.Progressbar(root, length=560, mode="determinate", bootstyle="success-striped")
progress_bar.pack()

elapsed_label = ttk.Label(root, text="Elapsed: 00:00:00")
elapsed_label.pack(pady=(6, 2))
eta_label = ttk.Label(root, text="Remaining: --:--")
eta_label.pack(pady=(0, 6))

status_box = tk.Text(root, height=18, width=85)
status_box.pack(pady=10)

# Settings variables
default_folder_var = tk.StringVar(value=settings["default_output"])
use_proxy_var = tk.IntVar(value=1 if settings["use_proxy"] else 0)
proxy_var = tk.StringVar(value=settings["proxy"])
remux_var = tk.IntVar(value=1 if settings["remux_mp4"] else 0)
recode_var = tk.IntVar(value=1 if settings["recode_mp4"] else 0)
extract_audio_var = tk.IntVar(value=1 if settings["extract_audio"] else 0)

def on_close():
    # ensure we stop process cleanly
    cancel_download()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_close)
root.mainloop()
