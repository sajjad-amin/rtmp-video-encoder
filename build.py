import os
import sys
import shutil
import platform
import subprocess

def check_dependencies():
    print("Ensuring dependencies are installed...")
    deps = ["pyinstaller", "psutil", "PyQt6"]
    
    if platform.system().lower() == "darwin":
        deps.append("dmgbuild")
        
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + deps)
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
        print("\n📦 Packaging into DMG using native create-dmg...")
        
        # 1. Paths Setup
        app_path = os.path.abspath('dist/RTMPVideoEncoder.app')
        dmg_path = os.path.abspath('dist/RTMPVideoEncoder.dmg')
        bg_path_abs = os.path.abspath(os.path.join('images', 'dmg_background.png'))
        icon_path_abs = os.path.abspath(os.path.join('images', 'app_icon.icns'))

        # 2. Check if create-dmg is installed
        if not shutil.which("create-dmg"):
            print("❌ 'create-dmg' is not installed on your Mac.")
            print("💡 Please open terminal and run: brew install create-dmg")
            print("Then run this build script again.")
            return

        # 3. Create a Staging Directory (Required for create-dmg)
        staging_dir = os.path.abspath('dist/dmg_staging')
        if os.path.exists(staging_dir):
            shutil.rmtree(staging_dir)
        os.makedirs(staging_dir)

        # 4. Copy the .app into the staging directory (Preserving Symlinks)
        dest_app_path = os.path.join(staging_dir, 'RTMPVideoEncoder.app')
        shutil.copytree(app_path, dest_app_path, symlinks=True)

        # 4.1 Fix Code Signature for Apple Silicon (M-series Macs)
        print("🔐 Re-signing the app bundle to prevent crashes...")
        try:
            subprocess.check_call(["codesign", "--force", "--deep", "-s", "-", dest_app_path])
            print("✅ Code signing successful!")
        except subprocess.CalledProcessError as e:
            print(f"⚠️ Warning: Code signing failed: {e}")

        # 5. Remove existing DMG if it exists to avoid conflicts
        if os.path.exists(dmg_path):
            os.remove(dmg_path)

        # 6. Construct create-dmg command
        cmd = [
            "create-dmg",
            "--volname", "RTMP Video Encoder",
            "--window-pos", "200", "120",
            "--window-size", "640", "640",
            "--icon-size", "120",
            "--text-size", "14",
            "--icon", "RTMPVideoEncoder.app", "175", "324",
            "--hide-extension", "RTMPVideoEncoder.app",
            "--app-drop-link", "465", "324"
        ]

        # Add background if exists
        if os.path.exists(bg_path_abs):
            cmd.extend(["--background", bg_path_abs])
            print(f"✅ Found Background Image: {bg_path_abs}")
        else:
            print(f"⚠️ Warning: Background image not found at {bg_path_abs}")

        # Add volume icon if exists
        if os.path.exists(icon_path_abs):
            cmd.extend(["--volicon", icon_path_abs])
            print(f"✅ Found Volume Icon: {icon_path_abs}")

        cmd.extend([dmg_path, staging_dir])

        # 7. Execute create-dmg
        try:
            print("Running create-dmg (This might take a minute)...")
            subprocess.check_call(cmd)
            print(f"✅ DMG created successfully: {dmg_path}")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to create DMG: {e}")
        finally:
            # 8. Clean up staging directory
            if os.path.exists(staging_dir):
                shutil.rmtree(staging_dir)

if __name__ == "__main__":
    check_dependencies()
    build_app()