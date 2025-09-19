@echo off
title Update yt-dlp & ffmpeg
echo =========================================
echo   Update-Skript fuer yt-dlp und ffmpeg
echo =========================================
echo.

:: Ordner festlegen (da wo yt-dlp.exe und ffmpeg.exe liegen)
set "TOOLS_DIR=%~dp0"

:: yt-dlp updaten
echo [1/2] Lade neueste yt-dlp Version...
curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe -o "%TOOLS_DIR%yt-dlp.exe"
echo Fertig: yt-dlp aktualisiert.
echo.

:: ffmpeg updaten
echo [2/2] Lade neueste FFmpeg Build...
curl -L https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip -o "%TOOLS_DIR%ffmpeg-latest.zip"
echo Entpacke FFmpeg...
powershell -command "Expand-Archive -Force '%TOOLS_DIR%ffmpeg-latest.zip' '%TOOLS_DIR%ffmpeg-temp'"
copy /Y "%TOOLS_DIR%ffmpeg-temp\ffmpeg-*-essentials_build\bin\ffmpeg.exe" "%TOOLS_DIR%ffmpeg.exe"
copy /Y "%TOOLS_DIR%ffmpeg-temp\ffmpeg-*-essentials_build\bin\ffprobe.exe" "%TOOLS_DIR%ffprobe.exe"
rmdir /S /Q "%TOOLS_DIR%ffmpeg-temp"
del "%TOOLS_DIR%ffmpeg-latest.zip"
echo Fertig: FFmpeg aktualisiert.
echo.

echo =========================================
echo   Update abgeschlossen!
echo =========================================
pause
