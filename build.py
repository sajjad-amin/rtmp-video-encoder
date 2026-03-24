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
        os.environ["MACOSX_DEPLOYMENT_TARGET"] = "11.0"
        icon_path = os.path.join(icon_dir, "app_icon.icns")
        if os.path.exists(icon_path):
            pyinstaller_args.append(f"--icon={icon_path}")
        else:
            print(f"⚠️ Warning: app_icon.icns not found in '{icon_dir}'. App will have default icon.")

        # FFmpeg bundling with ':' as separator on Unix systems
        pyinstaller_args.append(f"--add-binary={ffmpeg_path}:bin")
        
    else: # Linux
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

    # Cleanup the .spec file
    spec_file = "RTMPVideoEncoder.spec"
    if os.path.exists(spec_file):
        os.remove(spec_file)
        print(f"Removed {spec_file}")

    print("\n✅ Build Completed Successfully!")
    print("Check the 'dist/' folder for your standalone application.")

    # MacOS DMG creation
    if os_name == "darwin":
        print("\n📦 Packaging into DMG...")
        app_path = os.path.abspath('dist/RTMPVideoEncoder.app')
        dmg_path = os.path.abspath('dist/RTMPVideoEncoder.dmg')
        # Dynamically creating the dmgbuild settings file based on your provided configuration
        settings_code = f"""
import os

format = 'UDBZ'
size = None
files = [r'{app_path}']
symlinks = {{'Applications': '/Applications'}}

# Use icons if available
if os.path.exists('images/app_icon.icns'):
    badge_icon = os.path.abspath('images/app_icon.icns')
    icon = os.path.abspath('images/app_icon.icns')

# Use your generated background image if available, else fallback to builtin arrow
if os.path.exists('images/dmg_background.png'):
    background = os.path.abspath('images/dmg_background.png')
else:
    background = 'builtin-arrow'

# Window and View settings
window_rect = ((100, 100), (640, 640))
default_view = 'icon-view'
show_status_bar = False
show_tab_view = False
show_toolbar = False
show_pathbar = False
show_sidebar = False

# Positioning your App and Applications folder
icon_locations = {{
    'RTMPVideoEncoder.app': (175, 324),
    'Applications': (465, 324)
}}

text_size = 14
icon_size = 120
"""
        with open("dmg_settings.py", "w") as f:
            f.write(settings_code)
        
        # Run dmgbuild
        try:
            subprocess.check_call(["dmgbuild", "-s", "dmg_settings.py", "RTMP Video Encoder", dmg_path])
            print(f"✅ DMG created successfully: {dmg_path}")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to create DMG: {e}")
        finally:
            # Cleanup
            if os.path.exists("dmg_settings.py"):
                os.remove("dmg_settings.py")

if __name__ == "__main__":
    check_dependencies()
    build_app()