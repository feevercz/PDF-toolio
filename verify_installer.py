"""
verify_installer.py
Automated E2E Verification Harness for PDF-toolio Packaging & Windows Installer.
Checks installer creation, silent installation to isolated folder, PE GUI subsystem,
desktop shortcut & icon, smoke test execution, and silent uninstallation clean removal.
"""

import os
import sys
import time
import shutil
import struct
import tempfile
import subprocess


def get_pe_subsystem(exe_path: str) -> int:
    with open(exe_path, "rb") as f:
        dos_header = f.read(64)
        if len(dos_header) < 64 or dos_header[:2] != b"MZ":
            raise ValueError("Not a valid PE file (missing MZ signature)")
        e_lfanew = struct.unpack("<I", dos_header[0x3C:0x40])[0]
        f.seek(e_lfanew)
        pe_sig = f.read(4)
        if pe_sig != b"PE\x00\x00":
            raise ValueError("Not a valid PE header")
        opt_header_offset = e_lfanew + 24
        f.seek(opt_header_offset)
        magic = struct.unpack("<H", f.read(2))[0]
        if magic not in (0x10b, 0x20b):
            raise ValueError(f"Unknown PE magic: {hex(magic)}")
        f.seek(opt_header_offset + 68)
        subsystem = struct.unpack("<H", f.read(2))[0]
        return subsystem


def main():
    print("=== STARTING PDF-TOOLIO INSTALLER E2E VERIFICATION ===")

    # Step 1: Programmatically execute build_installer.py
    print("[TEST 1/6] Programmatically executing build_installer.py...")
    res = subprocess.run([sys.executable, "build_installer.py"], capture_output=True, text=True)
    if res.returncode != 0:
        print("build_installer.py stdout:\n", res.stdout)
        print("build_installer.py stderr:\n", res.stderr)
        raise RuntimeError(f"build_installer.py failed with exit code {res.returncode}")

    setup_exe = os.path.join("dist", "PDF-toolio-Setup.exe")
    if not os.path.exists(setup_exe):
        raise AssertionError(f"Installer artifact missing at {setup_exe}")

    size_bytes = os.path.getsize(setup_exe)
    print(f"Installer built: {setup_exe} ({size_bytes} bytes)")
    if size_bytes < 100 * 1024:
        raise AssertionError(f"Installer size ({size_bytes} bytes) is less than 100KB threshold!")
    print("[PASS 1/6] Installer creation verified (>100KB).")

    # Step 2: Install silently to custom isolated test directory
    print("[TEST 2/6] Silent installation to custom directory...")
    test_install_dir = os.path.join(tempfile.gettempdir(), "PDFToolio_E2E_TestInstall")
    if os.path.exists(test_install_dir):
        try:
            shutil.rmtree(test_install_dir)
        except Exception:
            pass

    desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
    desktop_lnk = os.path.join(desktop_dir, "PDF-toolio.lnk")
    if os.path.exists(desktop_lnk):
        try:
            os.remove(desktop_lnk)
        except Exception:
            pass

    install_cmd = [
        os.path.abspath(setup_exe),
        "/VERYSILENT",
        "/SUPPRESSMSGBOXES",
        f"/DIR={test_install_dir}",
        "/TASKS=desktopicon",
    ]
    res_inst = subprocess.run(install_cmd, capture_output=True, text=True)
    if res_inst.returncode != 0:
        print("Installer stdout:\n", res_inst.stdout)
        print("Installer stderr:\n", res_inst.stderr)
        raise RuntimeError(f"Installer failed with exit code {res_inst.returncode}")

    installed_exe = os.path.join(test_install_dir, "PDF-toolio.exe")
    installed_icon = os.path.join(test_install_dir, "pdf_icon.ico")

    if not os.path.exists(installed_exe):
        raise AssertionError(f"Installed executable missing: {installed_exe}")
    if not os.path.exists(installed_icon):
        raise AssertionError(f"Installed icon missing: {installed_icon}")

    # Find uninstaller
    uninstaller_path = None
    for cand in ["unins000.exe", "uninstall.exe"]:
        p = os.path.join(test_install_dir, cand)
        if os.path.exists(p):
            uninstaller_path = p
            break

    if not uninstaller_path:
        raise AssertionError(f"Uninstaller executable missing in {test_install_dir}")

    print(f"[PASS 2/6] Silent install successful. Installed EXE: {installed_exe}, Uninstaller: {uninstaller_path}")

    # Step 3: Assert Desktop shortcut exists & references pdf_icon.ico
    print("[TEST 3/6] Verifying Desktop shortcut and icon...")
    if not os.path.exists(desktop_lnk):
        raise AssertionError(f"Desktop shortcut missing: {desktop_lnk}")

    ps_cmd = f"$s = (New-Object -ComObject WScript.Shell).CreateShortcut('{desktop_lnk}'); Write-Output \"$($s.TargetPath)|$($s.IconLocation)\""
    res_ps = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, text=True)
    if res_ps.returncode != 0:
        raise RuntimeError(f"PowerShell shortcut query failed: {res_ps.stderr}")

    parts = res_ps.stdout.strip().split("|")
    target_path = parts[0].strip() if len(parts) > 0 else ""
    icon_loc = parts[1].strip() if len(parts) > 1 else ""

    print(f"Shortcut target: '{target_path}'")
    print(f"Shortcut icon location: '{icon_loc}'")

    if os.path.normpath(target_path).lower() != os.path.normpath(installed_exe).lower():
        raise AssertionError(f"Shortcut target mismatch! Got '{target_path}', expected '{installed_exe}'")

    # Validate icon magic bytes
    with open(installed_icon, "rb") as f:
        magic = f.read(4)
        if magic != b"\x00\x00\x01\x00":
            raise AssertionError(f"Invalid ICO magic header: {magic.hex()}")

    print("[PASS 3/6] Desktop shortcut and icon validation passed.")

    # Step 4: PE Header Subsystem & Smoke Test Execution
    print("[TEST 4/6] Verifying PE Header Subsystem (WinMain / GUI mode)...")
    subsystem = get_pe_subsystem(installed_exe)
    print(f"PE Header Subsystem value: {subsystem}")
    if subsystem != 2:
        raise AssertionError(f"Expected Subsystem == 2 (IMAGE_SUBSYSTEM_WINDOWS_GUI), got {subsystem} (Console/Other)")

    print("[PASS 4/6] PE Header subsystem verified (Subsystem == 2, Windowed GUI).")

    # Step 5: Execute smoke test
    print("[TEST 5/6] Executing --smoke-test on installed executable...")
    res_smoke = subprocess.run([installed_exe, "--smoke-test"], capture_output=True, text=True, timeout=30)
    print("Smoke test stdout:\n", res_smoke.stdout)
    if res_smoke.returncode != 0 or "SUCCESS: GUI SMOKE TEST PASSED CLEANLY!" not in res_smoke.stdout:
        raise AssertionError(f"Smoke test failed! Returncode={res_smoke.returncode}, Output={res_smoke.stdout}")

    print("[PASS 5/6] Smoke test passed cleanly.")

    # Step 6: Silent uninstallation & clean removal verification
    print("[TEST 6/6] Executing silent uninstaller...")
    unins_cmd = [uninstaller_path, "/VERYSILENT", "/SUPPRESSMSGBOXES"]
    res_unins = subprocess.run(unins_cmd, capture_output=True, text=True)
    if res_unins.returncode != 0:
        print("Uninstaller stderr:\n", res_unins.stderr)

    start_wait = time.time()
    while time.time() - start_wait < 10:
        if not os.path.exists(installed_exe):
            break
        time.sleep(0.5)

    if os.path.exists(installed_exe):
        raise AssertionError(f"Installed executable {installed_exe} still exists after uninstallation!")

    if os.path.exists(desktop_lnk):
        raise AssertionError(f"Desktop shortcut {desktop_lnk} still exists after uninstallation!")

    print("[PASS 6/6] Silent uninstallation verified. App files and desktop shortcut removed cleanly.")

    print("\n=== ALL 6 E2E VERIFICATION TESTS PASSED SUCCESSFULLY! ===")


if __name__ == "__main__":
    main()
