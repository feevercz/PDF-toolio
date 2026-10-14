# PDF-toolio

Lightweight desktop PDF compressor for Windows. Load a PDF, pick a compression level, save a smaller file.

Built with **Python**, **PyMuPDF**, and **CustomTkinter**.

## Features

- **Three compression levels** — evenly distributed on quality/size scale:
  - **Basic** — JPEG Q=95 at original resolution, near-lossless
  - **Large** — downsample to 200 DPI, JPEG Q=85
  - **Maximum** — downsample to 96 DPI, JPEG Q=50
- **Page 1 preview** — thumbnail rendered on load
- **Estimated reduction range** — content-aware % estimate before compression
- **Background processing** — non-blocking UI during compression
- **Windows installer** — Inno Setup package with optional desktop shortcut

## Quick Start

### Run from source

```bash
pip install -r requirements.txt
python main.py
```

### Build standalone installer

Requires [Inno Setup 6](https://jrsoftware.org/isinfo.php) installed.

```bash
python build_installer.py
```

Output: `dist/PDF-toolio-Setup.exe`

## Requirements

- Python 3.10+
- PyMuPDF >= 1.23.0
- Pillow >= 10.0.0
- customtkinter >= 5.2.0
- PyInstaller >= 6.0.0 (build only)

## Project Structure

```
main.py               Entry point
app_ui.py             CustomTkinter GUI (with standard Tkinter fallback)
pdf_engine.py         Compression engine — metadata, estimation, image re-encoding
build_installer.py    PyInstaller + Inno Setup build pipeline
generate_icon.py      Generates pdf_icon.ico programmatically
verify_compression.py Automated compression verification tests
```

## How It Works

The compression engine opens the PDF with PyMuPDF, extracts raster images, re-encodes them as JPEG at the target DPI and quality, replaces the image streams in-place, then saves with deflate compression and garbage collection. Text, vector graphics, and fonts remain untouched.

## Development

This project was built with AI-assisted development using [Claude Code](https://claude.com/claude-code) (Claude Opus).

## License

MIT
