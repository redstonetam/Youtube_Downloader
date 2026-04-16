import os
import sys
import json
import threading
import time
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk    
import ttkbootstrap as tb
from ttkbootstrap.constants import *


# ---------------- Resource & Settings ----------------
def resource_path(relative_path):
    """
    Return path to a bundled resource.
    If script is bundled by pyinstaller (--onefile) use sys._MEIPASS.
    Otherwise use the local folder and the 'Necessary' subfolder.
    """
    try:
        base = sys._MEIPASS
    except Exception:
        base = os.path.abspath(os.path.dirname(__file__))
    # executables & settings live in the Necessary folder
    return os.path.join(base, "Necessary", relative_path)

# SETTINGS_FILE lives in the Necessary folder
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
    """
    Load settings from SETTINGS_FILE if present.
    Merge with DEFAULT_SETTINGS so new keys get defaults.
    Returns a dict (copy on failure).
    """
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {**DEFAULT_SETTINGS, **data}
    except Exception:
        pass
    return DEFAULT_SETTINGS.copy()

def save_settings(s):
    """
    Save provided settings dict to SETTINGS_FILE.
    Ensures the Necessary folder exists before writing.
    """
    try:
        # Ensure Necessary folder exists (e.g. first run)
        settings_dir = os.path.dirname(SETTINGS_FILE)
        os.makedirs(settings_dir, exist_ok=True)
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(s, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print("Error saving settings:", e)

settings = load_settings()

# ---------------- Globals ----------------
# current_process: subprocess running the download
# process_lock: protect access to current_process
# stop_requested: signal to stop current process (used for pause/cancel)
# paused: whether UI is in paused state (resume will restart last_command)
# last_command: saved command list to allow resume
# start_time, elapsed_updater_id: track elapsed time updater scheduled with root.after
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
    """
    Optional helper: return an estimated filesize using yt-dlp --print.
    Not automatically called in the UI; used for quick size estimation only.
    """
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
    # Open folder picker and update the output_var if the user selects one
    folder = filedialog.askdirectory(initialdir=settings.get("default_output", DEFAULT_SETTINGS["default_output"]))
    if folder:
        output_var.set(folder)

def choose_default_folder():
    # Change the default download folder in persistent settings
    folder = filedialog.askdirectory(initialdir=settings.get("default_output", DEFAULT_SETTINGS["default_output"]))
    if folder:
        settings["default_output"] = folder
        save_settings(settings)
        default_folder_var.set(folder)

def open_settings():
    # Build settings window (modal-like) that allows the user to change persistent options
    settings_win = tb.Toplevel(root)
    settings_win.title("Settings")
    settings_win.geometry("580x650")
    settings_win.transient(root)

    # Create main frame with padding
    main_settings_frame = ttk.Frame(settings_win, padding=16)
    main_settings_frame.pack(fill="both", expand=True)

    # ===== Output Folder Section =====
    folder_section = ttk.LabelFrame(main_settings_frame, text="Save Location", padding=12)
    folder_section.pack(fill="x", pady=(0, 12))

    ttk.Label(folder_section, text="Default output folder:", font=("TkDefaultFont", 9)).pack(anchor="w", pady=(0, 4))
    df_frame = ttk.Frame(folder_section)
    df_frame.pack(fill="x")
    default_folder_entry = ttk.Entry(df_frame, width=50, textvariable=default_folder_var, state="readonly")
    default_folder_entry.pack(side="left", padx=(0, 8), fill="x", expand=True)
    ttk.Button(df_frame, text="Change", bootstyle="info", command=choose_default_folder).pack(side="left")

    # ===== Proxy Section =====
    proxy_section = ttk.LabelFrame(main_settings_frame, text="Network (Optional)", padding=12)
    proxy_section.pack(fill="x", pady=(0, 12))

    proxy_check = ttk.Checkbutton(proxy_section, text="Use proxy", variable=use_proxy_var, bootstyle="round-toggle")
    proxy_check.pack(anchor="w", pady=(0, 8))
    
    ttk.Label(proxy_section, text="Proxy (http://user:pass@host:port):", font=("TkDefaultFont", 9)).pack(anchor="w", pady=(0, 4))
    ttk.Entry(proxy_section, width=60, textvariable=proxy_var).pack(anchor="w", fill="x")

    # ===== Video Options Section =====
    video_section = ttk.LabelFrame(main_settings_frame, text="Video Conversion", padding=12)
    video_section.pack(fill="x", pady=(0, 12))

    ttk.Checkbutton(video_section, text="Auto remux to MP4 (fast, no re-encode)", variable=remux_var, bootstyle="round-toggle").pack(anchor="w", pady=(0, 6))
    ttk.Checkbutton(video_section, text="If remux fails: re-encode to MP4 (slower)", variable=recode_var, bootstyle="round-toggle").pack(anchor="w")

    # ===== Audio Extract Section =====
    audio_section = ttk.LabelFrame(main_settings_frame, text="Audio Extraction", padding=12)
    audio_section.pack(fill="x", pady=(0, 12))

    ttk.Checkbutton(audio_section, text="Extract audio when downloading MP3/WAV", variable=extract_audio_var, bootstyle="round-toggle").pack(anchor="w")

    # ===== Theme Section =====
    theme_section = ttk.LabelFrame(main_settings_frame, text="Appearance", padding=12)
    theme_section.pack(fill="x", pady=(0, 20))

    ttk.Label(theme_section, text="Theme:", font=("TkDefaultFont", 9)).pack(anchor="w", pady=(0, 4))
    theme_combo = ttk.Combobox(theme_section, values=["cosmo", "flatly", "darkly", "cyborg", "superhero", "journal"], width=25, state="readonly")
    theme_combo.set(settings.get("theme", "cosmo"))
    theme_combo.pack(anchor="w", fill="x")

    # ===== Buttons =====
    button_frame = ttk.Frame(main_settings_frame)
    button_frame.pack(fill="x", pady=(12, 0))

    def save_and_close():
        # Persist settings and apply chosen theme if possible
        settings["default_output"] = default_folder_var.get()
        settings["use_proxy"] = bool(use_proxy_var.get())
        settings["proxy"] = proxy_var.get().strip()
        settings["remux_mp4"] = bool(remux_var.get())
        settings["recode_mp4"] = bool(recode_var.get())
        settings["extract_audio"] = bool(extract_audio_var.get())
        settings["theme"] = theme_combo.get()
        save_settings(settings)
        settings_win.destroy()
        # apply theme (best-effort)
        try:
            root.style.theme_use(settings["theme"])
        except Exception:
            pass

    ttk.Button(button_frame, text="✓ Save", bootstyle="success", command=save_and_close, width=15).pack(side="right", padx=(8, 0))
    ttk.Button(button_frame, text="✕ Cancel", bootstyle="light", command=settings_win.destroy, width=15).pack(side="right")

# ---------------- Process / Download handling ----------------
def update_progress_reader(process):
    """
    Read stdout lines from the running process and update the UI.
    Extract percentage and ETA tokens when available and reflect them.
    When the process finishes normally (not paused/stopped) mark progress as complete.
    """
    global current_process, stop_requested, eta_text, elapsed_updater_id, start_time
    try:
        for line in process.stdout:
            if stop_requested:
                break
            line = line.rstrip()
            if not line:
                continue

            # show console output in UI (thread-safe via root.after)
            root.after(0, lambda l=line: (status_box.insert(tk.END, l + "\n"), status_box.see(tk.END)))

            # attempt to find a percentage token in the line
            if "%" in line:
                parts = line.split()
                for p in parts:
                    if "%" in p:
                        try:
                            val = float(p.replace("%","").replace(",","").replace("%",""))
                            root.after(0, lambda v=val: progress_bar.configure(value=v))
                            root.after(0, lambda v=val: progress_label.configure(text=f"⬇ Downloading... {v:.1f}%"))
                        except Exception:
                            pass

            # parse simple 'ETA' token patterns and show remaining time
            if "ETA" in line:
                tokens = line.split()
                for i,tok in enumerate(tokens):
                    if tok == "ETA" and i+1 < len(tokens):
                        eta_text = tokens[i+1]
                        root.after(0, lambda: eta_label.configure(text=f"⏳ Remaining: {eta_text}"))

        # finished normally (if not paused/stopped) -> finalize UI
        if not stop_requested and not paused:
            root.after(0, lambda: progress_bar.configure(value=100))
            root.after(0, lambda: progress_label.configure(text="✓ Download finished"))
            # show a small info dialog (best-effort)
            try:
                root.after(0, lambda: messagebox.showinfo("Success", f"✓ Download finished!\n\nSaved to:\n{output_var.get()}"))
            except Exception:
                pass

            # Stop elapsed timer after completion
            if elapsed_updater_id:
                try:
                    root.after_cancel(elapsed_updater_id)
                except Exception:
                    pass
                elapsed_updater_id = None
            start_time = None
    finally:
        # Ensure process reference is cleared and buttons updated
        with process_lock:
            current_process = None
        root.after(0, lambda: pause_resume_button.configure(text="▶ Start Download", bootstyle="success"))
        root.after(0, lambda: eta_label.configure(text="⏳ Remaining: --:--"))

def start_download_thread(command):
    """
    Start the yt-dlp subprocess with given command and spawn a reader thread.
    On Windows the console window is suppressed (CREATE_NO_WINDOW) to avoid flashing a console.
    """
    global current_process
    try:
        # Invisible window / no cmd shown during download (Windows-specific)
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
        # reader thread will parse progress and update GUI
        threading.Thread(target=update_progress_reader, args=(proc,), daemon=True).start()
    except Exception as e:
        messagebox.showerror("Error", f"Failed to start: {e}")

def stop_current_process(kill=False):
    """
    Terminate the running subprocess. If kill=True and terminate doesn't stop it, force kill.
    This does not clear last_command so a paused download can be resumed.
    """
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
    - "Start Download": start a new download
    - "Pause": stop the running process but keep last_command for resume
    - "Resume": start a new subprocess using the saved last_command
    """
    global paused, stop_requested, last_command, start_time, elapsed_updater_id

    state = pause_resume_button.cget("text")

    # If currently running -> Pause
    if state == "Pause" or state == "⏸ Pause":
        if current_process:
            stop_requested = True
            # keep last_command to allow resuming later
            stop_current_process(kill=False)
            paused = True
            pause_resume_button.configure(text="▶ Resume", bootstyle="warning")
            progress_label.configure(text="⏸ Paused")
            # stop elapsed timer but keep displayed elapsed value
            if elapsed_updater_id:
                try:
                    root.after_cancel(elapsed_updater_id)
                except Exception:
                    pass
            return

    # If currently paused -> Resume
    if state == "Resume" or state == "▶ Resume":
        if last_command:
            stop_requested = False
            paused = False
            pause_resume_button.configure(text="⏸ Pause", bootstyle="danger-outline")
            progress_label.configure(text="⬇ Resuming...")
            # restart elapsed timer (preserve previous elapsed if any)
            if start_time is None:
                start_time = time.time()
            def update_elapsed():
                global elapsed_updater_id
                if start_time and not stop_requested and not paused:
                    elapsed = int(time.time() - start_time)
                    mins, secs = divmod(elapsed, 60)
                    hours, mins = divmod(mins, 60)
                    elapsed_label.configure(text=f"⏱ Elapsed: {hours:02d}:{mins:02d}:{secs:02d}")
                    elapsed_updater_id = root.after(500, update_elapsed)
                else:
                    # keep last shown elapsed time when paused/stopped
                    pass
            update_elapsed()
            # start download using previous command (fresh subprocess)
            threading.Thread(target=start_download_thread, args=(last_command,), daemon=True).start()
        else:
            messagebox.showwarning("Resume", "No previous download command to resume.")
        return

    # If starting from idle -> Start Download
    if state in ("Start Download", "Start", "▶ Start Download"):
        url = url_entry.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a valid YouTube URL or playlist.")
            return

        # check required executables are present in the Necessary folder
        yt_dlp_path = resource_path("yt-dlp.exe")
        ffmpeg_path = resource_path("ffmpeg.exe")
        if not os.path.exists(yt_dlp_path) or not os.path.exists(ffmpeg_path):
            messagebox.showerror("Error", "yt-dlp.exe or ffmpeg.exe not found in 'Necessary' folder.")
            return

        # Note: Removed interactive video info prompt to simplify flow

        outdir = output_var.get() or settings["default_output"]
        os.makedirs(outdir, exist_ok=True)

        command = build_command(url, outdir)

        # Save last_command so user can resume after a pause
        last_command = command.copy()

        # reset UI and start
        progress_bar.configure(value=0, maximum=100, mode="determinate")
        progress_label.configure(text="⬇ Downloading...")
        status_box.delete(1.0, tk.END)
        pause_resume_button.configure(text="⏸ Pause", bootstyle="danger-outline")
        cancel_button.configure(state="normal")
        start_time = time.time()
        stop_requested = False
        paused = False

        # start elapsed updater (updates elapsed_label)
        def update_elapsed():
            global elapsed_updater_id
            if start_time and not stop_requested and not paused:
                elapsed = int(time.time() - start_time)
                mins, secs = divmod(elapsed, 60)
                hours, mins = divmod(mins, 60)
                elapsed_label.configure(text=f"Elapsed: {hours:02d}:{mins:02d}:{secs:02d}")
                elapsed_updater_id = root.after(500, update_elapsed)
            else:
                # keep last shown value when paused/stopped
                pass
        update_elapsed()

        threading.Thread(target=start_download_thread, args=(command,), daemon=True).start()
        return

def cancel_download():
    """
    Cancel the current download: force-kill the process and clear last_command.
    After cancel the user cannot resume the cancelled download.
    """
    global paused, last_command, stop_requested, start_time, elapsed_updater_id
    if current_process:
        stop_requested = True
        stop_current_process(kill=True)
    paused = False
    last_command = None
    pause_resume_button.configure(text="▶ Start Download", bootstyle="success")
    cancel_button.configure(state="disabled")
    progress_label.configure(text="✕ Cancelled")
    try:
        if elapsed_updater_id:
            root.after_cancel(elapsed_updater_id)
    except Exception:
        pass
    elapsed_updater_id = None
    start_time = None

# ---------------- Command builder ----------------
def build_command(url, outdir):
    """
    Build yt-dlp command based on UI options.
    Includes ffmpeg location, output template, proxy and format choices.
    """
    yt_dlp_path = resource_path("yt-dlp.exe")
    ffmpeg_path = resource_path("ffmpeg.exe")
    cmd = [yt_dlp_path, "--ffmpeg-location", ffmpeg_path, "-o", os.path.join(outdir, "%(title)s.%(ext)s"), "--progress"]

    if use_proxy_var.get():
        proxy_value = proxy_var.get().strip()
        if proxy_value:
            cmd.extend(["--proxy", proxy_value])

    fmt = format_var.get()
    q = quality_var.get()

    # Build format selection and post-processing options
    if fmt == "mp4":
        if remux_var.get():
            # Fast: remux to mp4 without re-encoding when possible
            cmd.extend(["-f", f"bestvideo[height<={q}]+bestaudio[ext=m4a]/best", "--remux-video", "mp4"])
        elif recode_var.get():
            # Slow: re-encode to mp4
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

    # Add subtitle options if selected
    subtitles_choice = subtitles_var.get()
    if subtitles_choice != "none":
        if subtitles_choice == "auto-all":
            # Auto-generate subtitles in all available languages
            cmd.extend(["--write-auto-sub", "--sub-format", "srt"])
        elif subtitles_choice.startswith("lang-"):
            # Extract language code (format: "lang-en", "lang-es", etc.)
            lang_code = subtitles_choice.split("-", 1)[1]
            cmd.extend(["--write-sub", "--write-auto-sub", "--sub-lang", lang_code, "--sub-format", "srt"])
        else:
            # Default: English subtitles
            cmd.extend(["--write-sub", "--write-auto-sub", "--sub-lang", "en", "--sub-format", "srt"])

    cmd.append(url)
    return cmd

# ---------------- GUI ----------------
root = tb.Window(themename=settings.get("theme", "cosmo"))
root.title("YouTube Downloader")
root.geometry("700x900")

# ===== Header Section =====
header_frame = ttk.Frame(root)
header_frame.pack(fill="x", padx=16, pady=(16, 0))

title_label = ttk.Label(header_frame, text="YouTube Downloader", font=("Helvetica", 20, "bold"))
title_label.pack(side="left", anchor="w")

settings_btn = ttk.Button(header_frame, text="⚙ Settings", bootstyle="light", command=open_settings)
settings_btn.pack(side="right")

ttk.Separator(root, orient="horizontal").pack(fill="x", pady=12, padx=0)

# ===== Main Content Frame (Scrollable area) =====
main_frame = ttk.Frame(root)
main_frame.pack(fill="both", expand=True, padx=16, pady=0)

# ===== URL Input Section =====
url_section = ttk.LabelFrame(main_frame, text="Source", padding=12)
url_section.pack(fill="x", pady=(0, 12))

ttk.Label(url_section, text="YouTube URL or Playlist:", font=("TkDefaultFont", 9)).pack(anchor="w", pady=(0, 4))
url_entry = ttk.Entry(url_section, width=70)
url_entry.pack(fill="x")
ttk.Label(url_section, text="Paste your video or playlist link", font=("TkDefaultFont", 8, "italic")).pack(anchor="w", pady=(2, 0))

# ===== Download Options Section =====
options_section = ttk.LabelFrame(main_frame, text="Download Options", padding=12)
options_section.pack(fill="x", pady=(0, 12))

# Format and Quality row
format_quality_frame = ttk.Frame(options_section)
format_quality_frame.pack(fill="x", pady=(0, 10))

# Format column
format_col = ttk.Frame(format_quality_frame)
format_col.pack(side="left", expand=True, padx=(0, 8))
ttk.Label(format_col, text="Format:", font=("TkDefaultFont", 9)).pack(anchor="w", pady=(0, 4))
format_var = tk.StringVar(value="mp4")
format_combo = ttk.Combobox(format_col, textvariable=format_var, values=["mp4", "mp3", "wav", "webm", "mov"], width=15, state="readonly")
format_combo.pack(fill="x")

# Quality column
quality_col = ttk.Frame(format_quality_frame)
quality_col.pack(side="left", expand=True, padx=(8, 0))
ttk.Label(quality_col, text="Quality:", font=("TkDefaultFont", 9)).pack(anchor="w", pady=(0, 4))
quality_var = tk.StringVar(value="1080")
quality_combo = ttk.Combobox(quality_col, textvariable=quality_var, values=["144", "240", "360", "480", "720", "1080", "1440", "2160"], width=15, state="readonly")
quality_combo.pack(fill="x")

# Subtitles row
ttk.Label(options_section, text="Subtitles:", font=("TkDefaultFont", 9)).pack(anchor="w", pady=(6, 4))
subtitles_var = tk.StringVar(value="none")
subtitles_options = [
    "none",
    "auto-all",
    "lang-en (English)",
    "lang-es (Spanish)",
    "lang-fr (French)",
    "lang-de (German)",
    "lang-it (Italian)",
    "lang-pt (Portuguese)",
    "lang-ru (Russian)",
    "lang-ja (Japanese)",
    "lang-ko (Korean)",
    "lang-zh (Chinese)",
    "lang-ar (Arabic)",
    "lang-hi (Hindi)",
    "lang-pl (Polish)",
    "lang-tr (Turkish)",
    "lang-vi (Vietnamese)",
    "lang-th (Thai)",
]
subtitles_combo = ttk.Combobox(options_section, textvariable=subtitles_var, values=subtitles_options, width=25, state="readonly")
subtitles_combo.pack(fill="x")
ttk.Label(options_section, text="'auto-all' downloads auto-generated subs in all available languages", font=("TkDefaultFont", 8, "italic")).pack(anchor="w", pady=(2, 0))

# ===== Output Folder Section =====
output_section = ttk.LabelFrame(main_frame, text="Save Location", padding=12)
output_section.pack(fill="x", pady=(0, 12))

output_var = tk.StringVar(value=settings.get("default_output", DEFAULT_SETTINGS["default_output"]))
ttk.Label(output_section, text="Destination folder:", font=("TkDefaultFont", 9)).pack(anchor="w", pady=(0, 4))
output_entry_frame = ttk.Frame(output_section)
output_entry_frame.pack(fill="x", pady=(0, 8))
ttk.Entry(output_entry_frame, width=60, textvariable=output_var, state="readonly").pack(side="left", fill="x", expand=True, padx=(0, 8))
ttk.Button(output_entry_frame, text="Browse", bootstyle="info", width=12, command=choose_output_folder).pack(side="left")

# ===== Control Buttons Section =====
button_section = ttk.Frame(main_frame)
button_section.pack(fill="x", pady=(6, 12))

pause_resume_button = ttk.Button(button_section, text="▶ Start Download", bootstyle="success", width=25, command=pause_or_resume)
pause_resume_button.pack(side="left", padx=(0, 8), fill="x", expand=True)

cancel_button = ttk.Button(button_section, text="✕ Cancel", bootstyle="danger", width=15, command=cancel_download, state="disabled")
cancel_button.pack(side="left", fill="x")

# ===== Progress Section =====
progress_section = ttk.LabelFrame(main_frame, text="Progress", padding=12)
progress_section.pack(fill="x", pady=(0, 12))

progress_label = ttk.Label(progress_section, text="Ready", font=("TkDefaultFont", 10, "bold"))
progress_label.pack(anchor="w", pady=(0, 6))

progress_bar = ttk.Progressbar(progress_section, length=600, mode="determinate", bootstyle="success-striped")
progress_bar.pack(fill="x", pady=(0, 8))

# Time info row
time_frame = ttk.Frame(progress_section)
time_frame.pack(fill="x")

elapsed_label = ttk.Label(time_frame, text="⏱ Elapsed: 00:00:00", font=("TkDefaultFont", 9))
elapsed_label.pack(side="left", padx=(0, 16))

eta_label = ttk.Label(time_frame, text="⏳ Remaining: --:--", font=("TkDefaultFont", 9))
eta_label.pack(side="left")

# ===== Status Output Section =====
output_section_label = ttk.LabelFrame(main_frame, text="Download Log", padding=8)
output_section_label.pack(fill="both", expand=True, pady=(0, 12))

status_frame = ttk.Frame(output_section_label)
status_frame.pack(fill="both", expand=True)

scrollbar = ttk.Scrollbar(status_frame)
scrollbar.pack(side="right", fill="y")

status_box = tk.Text(status_frame, height=12, width=85, yscrollcommand=scrollbar.set, font=("Courier", 8))
status_box.pack(side="left", fill="both", expand=True)
scrollbar.config(command=status_box.yview)

# Settings variables (bound to UI controls)
default_folder_var = tk.StringVar(value=settings["default_output"])
use_proxy_var = tk.IntVar(value=1 if settings["use_proxy"] else 0)
proxy_var = tk.StringVar(value=settings["proxy"])
remux_var = tk.IntVar(value=1 if settings["remux_mp4"] else 0)
recode_var = tk.IntVar(value=1 if settings["recode_mp4"] else 0)
extract_audio_var = tk.IntVar(value=1 if settings["extract_audio"] else 0)

def on_close():
    # Ensure any running process is stopped before closing the UI
    cancel_download()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_close)
root.mainloop()
