import subprocess
import re
import os
import sys
import time
import psutil
from PyQt6.QtCore import QThread, pyqtSignal

def get_ffmpeg_path():
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    exe_name = "ffmpeg.exe" if os.name == 'nt' else "ffmpeg"
    ffmpeg_path = os.path.join(base_path, "bin", exe_name)
    if not os.path.exists(ffmpeg_path):
        return exe_name
    return ffmpeg_path

def get_ffprobe_path():
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    exe_name = "ffprobe.exe" if os.name == 'nt' else "ffprobe"
    ffprobe_path = os.path.join(base_path, "bin", exe_name)
    if not os.path.exists(ffprobe_path):
        return exe_name
    return ffprobe_path

def get_video_height(file_path):
    ffprobe_cmd = get_ffprobe_path()
    try:
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
        cmd = [
            ffprobe_cmd, "-v", "error", "-select_streams", "v:0", 
            "-show_entries", "stream=height", "-of", "default=noprint_wrappers=1:nokey=1", 
            file_path
        ]
        out = subprocess.check_output(cmd, startupinfo=startupinfo, universal_newlines=True).strip()
        if out and out.isdigit():
            return int(out)
    except Exception:
        pass
    return None

def get_video_framerate(file_path):
    ffprobe_cmd = get_ffprobe_path()
    try:
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
        cmd = [
            ffprobe_cmd, "-v", "error", "-select_streams", "v:0", 
            "-show_entries", "stream=r_frame_rate", "-of", "default=noprint_wrappers=1:nokey=1", 
            file_path
        ]
        out = subprocess.check_output(cmd, startupinfo=startupinfo, universal_newlines=True).strip()
        if out and '/' in out:
            num, den = out.split('/')
            return float(num) / float(den)
        elif out.isdigit():
            return float(out)
    except Exception:
        pass
    return None

def get_video_bitrate(file_path):
    ffprobe_cmd = get_ffprobe_path()
    try:
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
        cmd = [
            ffprobe_cmd, "-v", "error", "-select_streams", "v:0", 
            "-show_entries", "stream=bit_rate", "-of", "default=noprint_wrappers=1:nokey=1", 
            file_path
        ]
        out = subprocess.check_output(cmd, startupinfo=startupinfo, universal_newlines=True).strip()
        if out and out.isdigit():
            return int(out)
            
        cmd = [
            ffprobe_cmd, "-v", "error", 
            "-show_entries", "format=bit_rate", "-of", "default=noprint_wrappers=1:nokey=1", 
            file_path
        ]
        out = subprocess.check_output(cmd, startupinfo=startupinfo, universal_newlines=True).strip()
        if out and out.isdigit():
            return int(out)
    except Exception:
        pass
    return None

def get_available_hw_encoders():
    ffmpeg_cmd = get_ffmpeg_path()
    try:
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
        process = subprocess.Popen(
            [ffmpeg_cmd, "-encoders"], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            universal_newlines=True,
            startupinfo=startupinfo
        )
        stdout, _ = process.communicate()
        encoders = []
        if "h264_nvenc" in stdout:
            encoders.append("h264_nvenc")
        if "h264_qsv" in stdout:
            encoders.append("h264_qsv")
        if "h264_videotoolbox" in stdout:
            encoders.append("h264_videotoolbox")
        if "h264_amf" in stdout:
            encoders.append("h264_amf")
        return encoders
    except Exception:
        return []

class ConverterThread(QThread):
    progress_updated = pyqtSignal(int, int, str, str)
    conversion_finished = pyqtSignal(int, bool, str)
    encoder_detected = pyqtSignal(int, str)

    def __init__(self, row, source_path, dest_path, encoder_selection, resolution_selection, framerate_selection, parent=None):
        super().__init__(parent)
        self.row = row
        self.source_path = source_path
        self.dest_path = dest_path
        self.encoder_selection = encoder_selection
        self.resolution_selection = resolution_selection
        self.framerate_selection = framerate_selection
        self.process = None
        self._is_cancelled = False
        self._is_paused = False

    def toggle_pause(self):
        if not self.process:
            return self._is_paused
            
        try:
            p = psutil.Process(self.process.pid)
            if self._is_paused:
                p.resume()
                self._is_paused = False
            else:
                p.suspend()
                self._is_paused = True
        except Exception as e:
            print(f"Failed to toggle pause: {e}")
            
        return self._is_paused

    def run(self):
        ffmpeg_exe = get_ffmpeg_path()
        selected_encoder = self.encoder_selection

        self.progress_updated.emit(self.row, 0, "00:00:00", "00:00:00")

        if selected_encoder == "Auto-Detect (Best Available)":
            available = get_available_hw_encoders()
            if "h264_nvenc" in available:
                selected_encoder = "NVIDIA NVENC (h264_nvenc)"
            elif "h264_videotoolbox" in available:
                selected_encoder = "Apple VideoToolbox (h264_videotoolbox)"
            elif "h264_qsv" in available:
                selected_encoder = "Intel QSV (h264_qsv)"
            elif "h264_amf" in available:
                selected_encoder = "AMD AMF (h264_amf)"
            else:
                selected_encoder = "CPU (libx264)"
        
        self.encoder_detected.emit(self.row, selected_encoder)

        # --- Resolution Logic ---
        target_height = None
        if self.resolution_selection != "Auto (Same as Source)":
            match = re.search(r'(\d+)p', self.resolution_selection)
            if match:
                target_height = int(match.group(1))

        source_height = get_video_height(self.source_path)
        vf_params = []
        bitrate_scale_factor = 1.0
        
        if target_height:
            if source_height:
                if source_height > target_height:
                    vf_params = ["-vf", f"scale=-2:{target_height}"]
                    bitrate_scale_factor = (target_height / source_height)
            else:
                vf_params = ["-vf", f"scale=-2:{target_height}"]

        # --- Constant Framing Parameter (CFR) ---
        r_params = []
        
        if self.framerate_selection.strip().lower() == "default":
            source_fps = get_video_framerate(self.source_path)
            
            # Safe standard broadcast framerates suitable natively for RTMP (allow slight floating point parsing inaccuracies)
            safe_framerates = [23.976, 23.98, 24, 25, 29.97, 30, 50, 59.94, 60]
            final_fps = 30
            
            if source_fps:
                # Check if it aligns with a standard safe constant framerate within 0.1 variance
                is_safe = any(abs(source_fps - s) < 0.1 for s in safe_framerates)
                
                # If parsed VFR exists natively over bound limitations securely enforce fallback to 30.
                if source_fps > 60.0 or not is_safe:
                    final_fps = 30
                else:
                    # Target safe rounding execution
                    final_fps = round(source_fps, 3)
                    
            r_params = ["-r", str(final_fps), "-fps_mode", "cfr"]
            
        else:
            # Explicit standard manual choice extraction
            match = re.search(r'([\d\.]+)', self.framerate_selection)
            if match:
                r_params = ["-r", match.group(1), "-fps_mode", "cfr"]

        # --- Encoder and Bitrate Generation ---
        if selected_encoder != "CPU (libx264)":
            bitrate_bps = get_video_bitrate(self.source_path)
            
            if bitrate_bps is None:
                bitrate_bps = 3000000 
            
            bitrate_bps = int(bitrate_bps * bitrate_scale_factor)
            bitrate_bps = max(bitrate_bps, 300000)
            
            kbps = int(bitrate_bps / 1000)
            target_bitrate = f"{kbps}k"
            max_bitrate = f"{int(kbps * 1.25)}k"
            bufsize = f"{int(kbps * 2)}k"
            v_params = ["-b:v", target_bitrate, "-maxrate", max_bitrate, "-bufsize", bufsize]
            
            if selected_encoder == "Apple VideoToolbox (h264_videotoolbox)":
                v_codec = "h264_videotoolbox"
            elif selected_encoder == "NVIDIA NVENC (h264_nvenc)":
                v_codec = "h264_nvenc"
                v_params = ["-preset", "fast"] + v_params
            elif selected_encoder == "Intel QSV (h264_qsv)":
                v_codec = "h264_qsv"
                v_params = ["-preset", "fast"] + v_params
            elif selected_encoder == "AMD AMF (h264_amf)":
                v_codec = "h264_amf"
                v_params = ["-quality", "speed"] + v_params
        else: 
            v_codec = "libx264"
            v_params = ["-preset", "fast", "-crf", "23"]

        cmd = [
            ffmpeg_exe,
            "-y",
            "-i", self.source_path,
            *vf_params,
            "-c:v", v_codec,
            *v_params,
            *r_params,
            "-c:a", "aac",
            "-movflags", "+faststart",
            self.dest_path
        ]
        
        try:
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            self.process = subprocess.Popen(
                cmd,
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                startupinfo=startupinfo
            )
        except FileNotFoundError:
            self.conversion_finished.emit(self.row, False, f"FFmpeg Executable not found locally! Expected mapping: {ffmpeg_exe}")
            return
        except Exception as e:
            self.conversion_finished.emit(self.row, False, f"Failed to start native FFmpeg hook: {str(e)}")
            return

        duration_regex = re.compile(r"Duration: (\d{2}):(\d{2}):(\d{2}\.\d+)")
        time_regex = re.compile(r"time=(\d{2}):(\d{2}):(\d{2}\.\d+)")
        
        total_duration_secs = 0.0
        buffer = bytearray()
        
        start_time = time.time()
        paused_duration = 0.0
        pause_start_time = None

        while True:
            if self._is_cancelled:
                self.process.terminate()
                self.process.wait()
                self.conversion_finished.emit(self.row, False, "Conversion cancelled by user.")
                return

            if self._is_paused:
                if pause_start_time is None:
                    pause_start_time = time.time()
                time.sleep(0.5)
                continue
            else:
                if pause_start_time is not None:
                    paused_duration += (time.time() - pause_start_time)
                    pause_start_time = None

            char = self.process.stderr.read(1)
            if not char:
                if self.process.poll() is not None:
                    break
                else:
                    continue
                
            buffer.extend(char)
            
            if char == b'\r' or char == b'\n':
                line = buffer.decode('utf-8', errors='ignore').strip()
                buffer.clear()
                
                if not line:
                    continue

                duration_match = duration_regex.search(line)
                if duration_match:
                    h, m, s = duration_match.groups()
                    total_duration_secs = int(h) * 3600 + int(m) * 60 + float(s)

                time_match = time_regex.search(line)
                if time_match and total_duration_secs > 0:
                    h, m, s = time_match.groups()
                    current_secs = int(h) * 3600 + int(m) * 60 + float(s)
                    progress = int((current_secs / total_duration_secs) * 100)
                    progress = max(0, min(100, progress))
                    
                    elapsed_secs = int(time.time() - start_time - paused_duration)
                    
                    if progress > 0 and progress <= 100:
                        total_estimated_secs = elapsed_secs / (progress / 100.0)
                        remaining_secs = int(max(0, total_estimated_secs - elapsed_secs))
                    else:
                        remaining_secs = 0
                    
                    elapsed_str = f"{int(elapsed_secs // 3600):02d}:{int((elapsed_secs % 3600) // 60):02d}:{int(elapsed_secs % 60):02d}"
                    est_str = f"{int(remaining_secs // 3600):02d}:{int((remaining_secs % 3600) // 60):02d}:{int(remaining_secs % 60):02d}"
                    
                    self.progress_updated.emit(self.row, progress, elapsed_str, est_str)

        self.process.wait()
        if self._is_cancelled:
            return
            
        if self.process.returncode == 0:
            self.progress_updated.emit(self.row, 100, "00:00:00", "00:00:00")
            self.conversion_finished.emit(self.row, True, "Completed Successfully.")
        else:
            self.conversion_finished.emit(self.row, False, f"FFmpeg error (code {self.process.returncode}).")

    def cancel(self):
        self._is_cancelled = True
        if self._is_paused:
            try:
                psutil.Process(self.process.pid).resume()
                self._is_paused = False
            except Exception:
                pass
