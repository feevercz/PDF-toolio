import os
import sys
import shutil

print("sys.executable:", sys.executable)
print("sys.prefix:", sys.prefix)
print("PATH environment:")
for p in os.environ.get("PATH", "").split(os.path.pathsep):
    print("  ", p)

pyinstaller_path = shutil.which("pyinstaller")
print("shutil.which('pyinstaller'):", pyinstaller_path)

# Look for venv directories in current directory or user home
for root in [".", os.path.expanduser("~")]:
    try:
        for item in os.listdir(root):
            if "venv" in item.lower() or "env" in item.lower() or "py" in item.lower():
                full = os.path.join(root, item)
                if os.path.isdir(full):
                    scripts_py = os.path.join(full, "Scripts", "python.exe")
                    if os.path.exists(scripts_py):
                        print("Found venv python at:", scripts_py)
    except Exception:
        pass
