import os
import sys
import subprocess
from PIL import Image, ImageDraw, ImageFont

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(base_dir, 'pdf_icon.ico')
    
    # 1. Create a simple PDF icon using Pillow
    print("Vytvářím ikonu...")
    img = Image.new('RGB', (256, 256), color=(220, 53, 69)) # Red background like PDF
    d = ImageDraw.Draw(img)
    
    try:
        # Try to use a nice font if available
        font = ImageFont.truetype("arialbd.ttf", 90)
        d.text((45, 80), "PDF", fill=(255, 255, 255), font=font)
    except IOError:
        # Fallback to default font
        font = ImageFont.load_default()
        d.text((100, 120), "PDF", fill=(255, 255, 255), font=font)
        
    img.save(icon_path, format='ICO', sizes=[(256, 256), (64, 64), (32, 32)])
    print(f"Ikona uložena jako: {icon_path}")
    
    # 2. Create the shortcut on Desktop using PowerShell
    print("Vytvářím zástupce na ploše...")
    desktop = os.path.join(os.environ['USERPROFILE'], 'Desktop')
    shortcut_path = os.path.join(desktop, 'PDF-toolio.lnk')
    
    # Use pythonw.exe so no console window pops up when running the app
    python_exe = sys.executable
    pythonw_exe = python_exe.replace('python.exe', 'pythonw.exe')
    if not os.path.exists(pythonw_exe):
        pythonw_exe = python_exe # Fallback if pythonw is not found
        
    main_script = os.path.join(base_dir, 'main.py')
    
    ps_script = f"""
    $WshShell = New-Object -comObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut('{shortcut_path}')
    $Shortcut.TargetPath = '{pythonw_exe}'
    $Shortcut.Arguments = '"{main_script}"'
    $Shortcut.WorkingDirectory = '{base_dir}'
    $Shortcut.IconLocation = '{icon_path}'
    $Shortcut.Save()
    """
    
    result = subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, text=True)
    
    if result.returncode == 0:
        print("Hotovo! Zástupce 'PDF-toolio' byl vytvořen na vaší ploše.")
    else:
        print(f"Došlo k chybě při vytváření zástupce:\n{result.stderr}")

if __name__ == "__main__":
    main()
