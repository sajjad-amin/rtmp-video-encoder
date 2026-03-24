# RTMP Video Encoder

A cross-platform, high-performance desktop application built with Python and PyQt6. Designed specifically to re-encode corrupted videos for seamless IPTV / RTMP streaming. It utilizes robust FFmpeg backend processes with advanced hardware acceleration and file-size intelligence.

## Core Features
- **Batch Processing Queue**: Add multiple video files, set specific global or local destinations, and let the sequential orchestrator handle conversions in the background without freezing the UI.
- **Hardware Acceleration**: Auto-detects and leverages powerful system GPUs (NVIDIA NVENC, Apple VideoToolbox, Intel QSV, AMD AMF) for maximum encoding speed, or gracefully falls back to CPU (libx264).
- **Anti-Bloat Bitrate Intelligence**: Automatically extracts your original source video's exact bitrate via an invisible `ffprobe` subprocess. It pushes equivalent parameters to the hardware encoders, preserving visual quality without needlessly inflating the output file boundaries.
- **Native Pause / Resume**: Safely suspends the active FFmpeg process at the OS-level using `psutil`, ensuring 0% system resource usage while functionally paused.
- **Cross-Platform Bundling**: Includes an advanced `build.py` script to natively compile macOS `.dmg` installers or Windows `.exe` binaries using PyInstaller and dmgbuild.

## Installation / Setup (Development)
1. Clone the repository and install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Place a valid `ffmpeg` and `ffprobe` executable into a local `bin/` folder at the root directory.
3. Run the application:
   ```bash
   python main.py
   ```

## Compiling to Standalone Deployments
The application ships with a customized `build.py` file which acts as a deployment wrapper. 
1. Ensure your machine has internet access to grab Pyinstaller & dependencies.
2. Ensure you have FFmpeg configured globally or residing cleanly in the `bin/` folder.
3. Run the build compiler:
   ```bash
   python build.py
   ```
The script will cleanly output an autonomous application (and `.dmg` volume on macOS) securely tucked in the `dist/` directory!
