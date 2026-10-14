import os
import sys

print("Searching for pyinstaller or python environments across user directories...")

search_dirs = [
    os.path.expanduser("~\\AppData\\Local\\Programs\\Python"),
    os.path.expanduser("~\\AppData\\Roaming\\Python"),
    os.path.expanduser("~\\AppData\\Local\\pip"),
    os.path.expanduser("~\\.virtualenvs"),
    "C:\\Python313\\Lib\\site-packages",
    "C:\\Python312",
    "C:\\Python311",
    "C:\\Python310",
]

for d in search_dirs:
    if os.path.exists(d):
        print("Exists:", d)
        for root, dirs, files in os.walk(d):
            if "PyInstaller" in dirs or "pyinstaller.exe" in files:
                print("FOUND PyInstaller in:", root)
                break

# Check site-packages of current python
import site
print("Site packages dirs:", site.getsitepackages(), site.getusersitepackages())
