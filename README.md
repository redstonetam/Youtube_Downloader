````markdown
# YouTube Downloader (GUI)

A simple YouTube Downloader with a modern GUI built using **Python + ttkbootstrap**.  
It uses [yt-dlp](https://github.com/yt-dlp/yt-dlp) and [ffmpeg](https://ffmpeg.org/) to download and process videos.
Most of the code by chatgpt
---

## Features
- Download single videos or entire playlists
- Choose output format: **MP4, MP3, WAV, WEBM, MOV**
- Choose video quality: from 144p up to 4K (2160p)
- Extract audio directly as MP3 or WAV
- Auto remux or re-encode videos
- Proxy support
- Progress bar, ETA, and console log inside the GUI
- Customizable themes with `ttkbootstrap`

---

## Requirements

### 1. Python
- Python **3.8+** installed ([Download here](https://www.python.org/downloads/))

### 2. Python packages
Install dependencies with:
```bash
pip install -r requirements.txt
````

Or manually:

```bash
pip install ttkbootstrap
```

### 3. External tools

* [yt-dlp.exe](https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe)
* [ffmpeg.exe](https://www.gyan.dev/ffmpeg/builds/)

Place both files inside the `Necessary/` folder of this project.
The script will look for them automatically.

---

## How to Run

1. Clone or download this repository
2. Make sure `yt-dlp.exe` and `ffmpeg.exe` are in the `Necessary/` folder
3. Install dependencies (`pip install ttkbootstrap`)
4. Run the script:

   ```bash
   python YD.py
   ```
5. Enjoy downloading videos 🎬

---

## Notes

* Default downloads are saved into your **Downloads** folder.
* You can change the default folder and other settings in the **⚙️ Settings** menu.
* If `yt-dlp.exe` or `ffmpeg.exe` are missing, the program will show an error.

---

## License

This project is provided **as-is** for personal use.


