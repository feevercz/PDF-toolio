"""
build_installer.py
Automates icon generation, PyInstaller single-folder packaging, and Windows installer compilation (dist/PDF-toolio-Setup.exe).
Supports Inno Setup (ISCC.exe) if available, or native PyInstaller setup builder fallback.
"""

import os
import sys
import shutil
import zipfile
import subprocess
import generate_icon


def ensure_icon():
    icon_path = "pdf_icon.ico"
    if not os.path.exists(icon_path):
        print("pdf_icon.ico missing. Generating icon...")
        generate_icon.generate_icon(icon_path)
    else:
        print("pdf_icon.ico exists.")


def build_pyinstaller_app():
    print("Building standalone application via PyInstaller...")
    spec_path = "PDF-toolio.spec"
    if not os.path.exists(spec_path):
        raise FileNotFoundError(f"{spec_path} does not exist.")

    cmd = [sys.executable, "-m", "PyInstaller", "--clean", "-y", spec_path]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print("PyInstaller stdout:\n", res.stdout)
        print("PyInstaller stderr:\n", res.stderr)
        raise RuntimeError(f"PyInstaller failed with returncode {res.returncode}")

    app_dir = os.path.join("dist", "PDF-toolio")
    exe_path = os.path.join(app_dir, "PDF-toolio.exe")
    if not os.path.exists(exe_path):
        raise FileNotFoundError(f"Expected built executable at {exe_path}")

    print(f"PyInstaller build successful: {exe_path}")
    return app_dir


def find_iscc():
    iscc = shutil.which("iscc") or shutil.which("ISCC")
    if iscc and os.path.exists(iscc):
        return iscc
    common_paths = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
        r"C:\Program Files\Inno Setup 5\ISCC.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"),
    ]
    for path in common_paths:
        if os.path.exists(path):
            return path
    return None


def build_inno_installer(iscc_path):
    print(f"Building installer via Inno Setup ({iscc_path})...")
    iss_content = """[Setup]
AppName=PDF-toolio
AppVersion=1.0.0
AppPublisher=PDF-toolio Team
DefaultDirName={autopf}\\PDF-toolio
DefaultGroupName=PDF-toolio
OutputDir=dist
OutputBaseFilename=PDF-toolio-Setup
SetupIconFile=pdf_icon.ico
UninstallDisplayIcon={app}\\_internal\\pdf_icon.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
DisableDirPage=no

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "dist\\PDF-toolio\\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\\PDF-toolio"; Filename: "{app}\\PDF-toolio.exe"; IconFilename: "{app}\\_internal\\pdf_icon.ico"
Name: "{group}\\Uninstall PDF-toolio"; Filename: "{uninstallexe}"
Name: "{userdesktop}\\PDF-toolio"; Filename: "{app}\\PDF-toolio.exe"; IconFilename: "{app}\\_internal\\pdf_icon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\\PDF-toolio.exe"; Description: "{cm:LaunchProgram,PDF-toolio}"; Flags: nowait postinstall skipifsilent
"""
    iss_path = "PDF-toolio.iss"
    with open(iss_path, "w", encoding="utf-8") as f:
        f.write(iss_content)

    res = subprocess.run([iscc_path, iss_path], capture_output=True, text=True)
    if res.returncode != 0:
        print("ISCC stdout:\n", res.stdout)
        print("ISCC stderr:\n", res.stderr)
        raise RuntimeError(f"ISCC compilation failed with returncode {res.returncode}")

    setup_exe = os.path.join("dist", "PDF-toolio-Setup.exe")
    if not os.path.exists(setup_exe):
        raise FileNotFoundError(f"Expected installer at {setup_exe}")

    print(f"Inno Setup build successful: {setup_exe}")
    return setup_exe


def build_native_installer(app_dir):
    raise RuntimeError("Inno Setup (ISCC.exe) nebyl nalezen. Instalátor vyžaduje Inno Setup pro zajištění bezpečné odinstalace.")


def main():
    print("=== Starting PDF-toolio Build Pipeline ===")
    ensure_icon()
    app_dir = build_pyinstaller_app()

    iscc_path = find_iscc()
    if iscc_path:
        build_inno_installer(iscc_path)
    else:
        build_native_installer(app_dir)

    print("=== PDF-toolio Build Completed Successfully ===")


if __name__ == "__main__":
    main()
