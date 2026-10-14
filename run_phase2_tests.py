"""
run_phase2_tests.py
Empirical Verification & Stress Test Suite for Phase 2 Implementation.
"""

import os
import sys
import struct
import subprocess

def test_1_icon_generation_and_binary_inspection():
    print("\n--- TEST 1: ICO Generation & Binary Inspection ---")
    import generate_icon
    icon_path = "pdf_icon.ico"
    generate_icon.generate_icon(icon_path)
    
    if not os.path.exists(icon_path):
        raise RuntimeError(f"{icon_path} was not created!")
        
    with open(icon_path, "rb") as f:
        data = f.read()
        
    magic = data[:4]
    print(f"ICO Header Magic Bytes: {magic.hex()} (Expected: 00000100)")
    if magic != b"\x00\x00\x01\x00":
        raise ValueError(f"Invalid ICO header magic: {magic.hex()}")
        
    num_images = struct.unpack("<H", data[4:6])[0]
    print(f"Number of embedded images: {num_images}")
    
    frames = []
    # Directory entries start at offset 6, 16 bytes per entry
    for i in range(num_images):
        offset = 6 + i * 16
        width = data[offset]
        height = data[offset + 1]
        w_eff = 256 if width == 0 else width
        h_eff = 256 if height == 0 else height
        bpp = struct.unpack("<H", data[offset + 6:offset + 8])[0]
        size = struct.unpack("<I", data[offset + 8:offset + 12])[0]
        img_offset = struct.unpack("<I", data[offset + 12:offset + 16])[0]
        frames.append((w_eff, h_eff, bpp, size, img_offset))
        print(f" Frame {i+1}: {w_eff}x{h_eff}, bpp={bpp}, size={size} bytes, offset={img_offset}")
        
    expected_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    found_sizes = [(f[0], f[1]) for f in frames]
    print(f"Found frames: {found_sizes}")
    for sz in expected_sizes:
        if sz not in found_sizes:
            raise ValueError(f"Expected frame size {sz} missing from ICO!")
            
    print("TEST 1 PASSED: ICO header magic bytes and stored size frames verified successfully.")

def test_2_build_installer():
    print("\n--- TEST 2: Build Installer Verification ---")
    res = subprocess.run([sys.executable, "build_installer.py"], capture_output=True, text=True)
    print("build_installer stdout:\n", res.stdout)
    if res.returncode != 0:
        print("build_installer stderr:\n", res.stderr)
        raise RuntimeError(f"build_installer.py failed with returncode {res.returncode}")
        
    setup_exe = os.path.join("dist", "PDF-toolio-Setup.exe")
    if not os.path.exists(setup_exe):
        raise FileNotFoundError(f"{setup_exe} was not created!")
        
    size_bytes = os.path.getsize(setup_exe)
    print(f"Installer artifact: {setup_exe} ({size_bytes} bytes)")
    if size_bytes < 100 * 1024:
        raise ValueError(f"Installer size ({size_bytes} bytes) below 100KB threshold!")
        
    print("TEST 2 PASSED: Installer build and setup EXE verified successfully.")

def test_3_pe_subsystem_header():
    print("\n--- TEST 3: PE Subsystem Header Stress Test ---")
    exe_path = os.path.join("dist", "PDF-toolio", "PDF-toolio.exe")
    if not os.path.exists(exe_path):
        raise FileNotFoundError(f"{exe_path} missing!")
        
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
        
    print(f"PE Header Subsystem value for {exe_path}: {subsystem}")
    if subsystem != 2:
        raise ValueError(f"Expected PE subsystem == 2 (IMAGE_SUBSYSTEM_WINDOWS_GUI), got {subsystem}")
    print("TEST 3 PASSED: GUI subsystem == 2 verified (no command console window).")

def test_4_verify_installer_e2e():
    print("\n--- TEST 4: E2E Installer Verification Suite ---")
    res = subprocess.run([sys.executable, "verify_installer.py"], capture_output=True, text=True)
    print("verify_installer stdout:\n", res.stdout)
    if res.returncode != 0:
        print("verify_installer stderr:\n", res.stderr)
        raise RuntimeError(f"verify_installer.py failed with returncode {res.returncode}")
    print("TEST 4 PASSED: All 6 E2E verification checks passed.")

if __name__ == "__main__":
    print("=== STARTING PHASE 2 EMPIRICAL CHALLENGE SUITE ===")
    test_1_icon_generation_and_binary_inspection()
    test_2_build_installer()
    test_3_pe_subsystem_header()
    test_4_verify_installer_e2e()
    print("\n=== ALL PHASE 2 EMPIRICAL TESTS PASSED SUCCESSFULLY ===")
