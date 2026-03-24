import os
import sys
import shutil
import platform
import subprocess

def check_dependencies():
    print("Ensuring dependencies are installed...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller", "psutil", "PyQt6"])
    except subprocess.CalledProcessError:
        print("Failed to install dependencies. Please check your internet connection.")
        sys.exit(1)

def ensure_ffmpeg():
    os_name = platform.system().lower()
    bin_dir = "bin"
    
    if not os.path.exists(bin_dir):
        os.makedirs(bin_dir)
        
    ffmpeg_exe = "ffmpeg.exe" if os_name == "windows" else "ffmpeg"
    ffmpeg_local_path = os.path.join(bin_dir, ffmpeg_exe)
    
    if not os.path.exists(ffmpeg_local_path):
        print(f"FFmpeg not found in '{bin_dir}/'. Auto-searching in system PATH...")
        system_ffmpeg = shutil.which("ffmpeg")
        
        if system_ffmpeg:
            print(f"✅ Found system FFmpeg at: {system_ffmpeg}")
            print(f"Copying to local '{bin_dir}' folder...")
            try:
                shutil.copy2(system_ffmpeg, ffmpeg_local_path)
                print("✅ FFmpeg copied successfully!")
            except Exception as e:
                print(f"❌ Failed to copy FFmpeg: {e}")
                sys.exit(1)
        else:
            print("❌ ERROR: FFmpeg not found on your system!")
            if os_name == "darwin":
                print("💡 Hint: Run 'brew install ffmpeg' on your Mac, then run this script again.")
            else:
                print("💡 Hint: Please install FFmpeg and ensure it's in your system PATH.")
            sys.exit(1)
            
    return ffmpeg_local_path

def build_app():
    os_name = platform.system().lower()
    print(f"\n--- Starting Build Process for {os_name.upper()} ---")
    
    ffmpeg_path = ensure_ffmpeg()
    
    # PyInstaller arguments
    pyinstaller_args = [
        "pyinstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name=RTMPVideoEncoder",
        "--clean",
    ]
    
    icon_dir = "images"
    
    if os_name == "windows":
        icon_path = os.path.join(icon_dir, "app_icon.ico")
        if os.path.exists(icon_path):
            pyinstaller_args.append(f"--icon={icon_path}")
        else:
            print(f"⚠️ Warning: app_icon.ico not found in '{icon_dir}'. App will have default icon.")

        # FFmpeg bundling with ';' as separator on Windows
        pyinstaller_args.append(f"--add-binary={ffmpeg_path};bin")
        
    elif os_name == "darwin": # macOS
        # ম্যাকের জন্য .icns ব্যবহার করুন
        icon_path = os.path.join(icon_dir, "app_icon.icns")
        if os.path.exists(icon_path):
            pyinstaller_args.append(f"--icon={icon_path}")
        else:
            print(f"⚠️ Warning: app_icon.icns not found in '{icon_dir}'. App will have default icon.")

        # FFmpeg bundling with ':' as separator on Unix systems
        pyinstaller_args.append(f"--add-binary={ffmpeg_path}:bin")
        
    else: # Linux
        # লিনাক্সের জন্য আইকন ব্যবহারের নিয়ম ওএসের ওপর নির্ভর করে, কিন্তু ডিফল্ট অ্যাপ আইকন সেট করার জন্য এটুকু যথেষ্ট
        icon_path = os.path.join(icon_dir, "app_icon.ico")
        if os.path.exists(icon_path):
            pyinstaller_args.append(f"--icon={icon_path}")
        else:
            print(f"⚠️ Warning: app_icon.ico not found in '{icon_dir}'. App will have default icon.")

        # FFmpeg bundling with ':' as separator on Unix systems
        pyinstaller_args.append(f"--add-binary={ffmpeg_path}:bin")
        
    # Add main script
    pyinstaller_args.append("main.py")
    
    # Run PyInstaller
    print("\nRunning PyInstaller...")
    subprocess.check_call(pyinstaller_args)
    print("\n✅ Build Completed Successfully!")
    print("Check the 'dist/' folder for your standalone application.")

if __name__ == "__main__":
    check_dependencies()
    build_app()