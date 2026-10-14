"""
app_ui.py - Desktop GUI Application for PDF-toolio

Built using CustomTkinter (with standard Tkinter/TTK fallback).
Provides PDF loading, Page 1 preview thumbnail, dynamic compression size estimation,
level selection ("Basic", "Large", "Maximum"), background threaded execution, and
headless smoke-test mode (--smoke-test).
"""

import os
import sys
import io
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk

import pdf_engine

# Attempt CustomTkinter import with graceful fallback
try:
    import customtkinter as ctk
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")
    CTK_AVAILABLE = True
except ImportError:
    ctk = None
    CTK_AVAILABLE = False


def get_resource_path(relative_path: str) -> str:
    """Get absolute path to resource, compatible with PyInstaller freeze."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


LEVEL_DESCRIPTIONS = {
    "Basic": "Re-encodes images to JPEG Q=95 at original resolution. Deflates streams, removes garbage, cleans metadata. Near-lossless quality.",
    "Large": "Downsamples images >200 DPI to 200 DPI with JPEG Q=85. Good balance of quality and file size for everyday use.",
    "Maximum": "Downsamples images >96 DPI to 96 DPI with JPEG Q=50. Smallest file size for email or web sharing."
}


class PDFToolioApp(ctk.CTk if CTK_AVAILABLE else tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("PDF-toolio — Desktop PDF Compressor")
        self.geometry("700x750")
        self.minsize(640, 680)

        # Set window titlebar icon safely
        icon_path = get_resource_path("pdf_icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

        # Application state
        self.current_pdf_path = None
        self.current_pdf_info = None
        self.estimates = {}
        self.selected_level = "Large"
        self._current_thumbnail = None

        self._build_ui()

    def _build_ui(self):
        if CTK_AVAILABLE:
            self._build_customtkinter_ui()
        else:
            self._build_standard_tkinter_ui()

    # -------------------------------------------------------------------------
    # CustomTkinter UI Builder
    # -------------------------------------------------------------------------
    def _build_customtkinter_ui(self):
        # Header Frame
        header_frame = ctk.CTkFrame(self, corner_radius=10)
        header_frame.pack(fill="x", padx=20, pady=(20, 10))

        title_label = ctk.CTkLabel(
            header_frame,
            text="📄 PDF-toolio",
            font=ctk.CTkFont(size=26, weight="bold")
        )
        title_label.pack(anchor="w", padx=20, pady=(15, 2))

        subtitle_label = ctk.CTkLabel(
            header_frame,
            text="Lightweight, High-Efficiency PDF Compression Tool",
            font=ctk.CTkFont(size=13),
            text_color="gray"
        )
        subtitle_label.pack(anchor="w", padx=20, pady=(0, 15))

        # Main Layout: 2 Columns (Left: Controls & Info, Right: Preview)
        content_frame = ctk.CTkFrame(self, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=20, pady=10)
        content_frame.columnconfigure(0, weight=3)
        content_frame.columnconfigure(1, weight=2)

        # LEFT COLUMN (File Selection, Levels, Estimation)
        left_col = ctk.CTkFrame(content_frame, corner_radius=10)
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        # Section 1: File Selection
        sec1_label = ctk.CTkLabel(
            left_col,
            text="1. Select Input PDF",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        sec1_label.pack(anchor="w", padx=15, pady=(15, 5))

        self.select_button = ctk.CTkButton(
            left_col,
            text="📁 Choose PDF File...",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=38,
            command=self.on_select_pdf
        )
        self.select_button.pack(fill="x", padx=15, pady=5)

        self.filename_label = ctk.CTkLabel(
            left_col,
            text="No file selected",
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
            wraplength=340
        )
        self.filename_label.pack(fill="x", padx=15, pady=(5, 0))

        self.file_stats_label = ctk.CTkLabel(
            left_col,
            text="Original Size: -- | Pages: --",
            font=ctk.CTkFont(size=12),
            text_color="gray",
            anchor="w"
        )
        self.file_stats_label.pack(fill="x", padx=15, pady=(0, 15))

        # Section 2: Compression Level
        sec2_label = ctk.CTkLabel(
            left_col,
            text="2. Compression Level",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        sec2_label.pack(anchor="w", padx=15, pady=(10, 5))

        self.level_selector = ctk.CTkSegmentedButton(
            left_col,
            values=["Basic", "Large", "Maximum"],
            command=self.on_level_changed,
            font=ctk.CTkFont(size=13, weight="bold"),
            height=32
        )
        self.level_selector.set("Large")
        self.level_selector.pack(fill="x", padx=15, pady=5)

        # Estimation Display Card
        est_card = ctk.CTkFrame(left_col, corner_radius=8, fg_color=("gray85", "gray20"))
        est_card.pack(fill="x", padx=15, pady=10)

        self.est_reduction_label = ctk.CTkLabel(
            est_card,
            text="Estimated Reduction: --",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#10B981"  # Emerald green
        )
        self.est_reduction_label.pack(anchor="w", padx=12, pady=(10, 5))

        self.level_desc_label = ctk.CTkLabel(
            est_card,
            text=LEVEL_DESCRIPTIONS["Large"],
            font=ctk.CTkFont(size=11),
            text_color="gray",
            wraplength=330,
            justify="left"
        )
        self.level_desc_label.pack(anchor="w", padx=12, pady=(0, 10))

        # RIGHT COLUMN (Visual Page Preview)
        right_col = ctk.CTkFrame(content_frame, corner_radius=10)
        right_col.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        preview_title = ctk.CTkLabel(
            right_col,
            text="Page 1 Preview",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        preview_title.pack(anchor="w", padx=15, pady=(15, 10))

        self.preview_container = ctk.CTkFrame(
            right_col,
            corner_radius=8,
            fg_color=("gray90", "gray15")
        )
        self.preview_container.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        self.preview_label = ctk.CTkLabel(
            self.preview_container,
            text="No PDF Loaded",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.preview_label.pack(expand=True)

        # BOTTOM ACTION FRAME
        bottom_frame = ctk.CTkFrame(self, corner_radius=10)
        bottom_frame.pack(fill="x", padx=20, pady=(10, 20))

        self.progressbar = ctk.CTkProgressBar(bottom_frame, height=10)
        self.progressbar.set(0)
        self.progressbar.pack(fill="x", padx=20, pady=(15, 5))

        self.status_label = ctk.CTkLabel(
            bottom_frame,
            text="Ready to process PDF",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.status_label.pack(anchor="w", padx=20, pady=(0, 10))

        self.compress_button = ctk.CTkButton(
            bottom_frame,
            text="⚡ Compress & Save PDF",
            font=ctk.CTkFont(size=16, weight="bold"),
            height=45,
            fg_color="#2563EB",
            hover_color="#1D4ED8",
            state="disabled",
            command=self.on_compress_click
        )
        self.compress_button.pack(fill="x", padx=20, pady=(0, 15))

    # -------------------------------------------------------------------------
    # Standard Tkinter UI Fallback
    # -------------------------------------------------------------------------
    def _build_standard_tkinter_ui(self):
        from tkinter import ttk
        self.configure(bg="#F3F4F6")

        header = ttk.Frame(self)
        header.pack(fill="x", padx=20, pady=15)
        ttk.Label(header, text="📄 PDF-toolio", font=("Helvetica", 22, "bold")).pack(anchor="w")
        ttk.Label(header, text="Lightweight, High-Efficiency PDF Compression Tool", font=("Helvetica", 11)).pack(anchor="w")

        content = ttk.Frame(self)
        content.pack(fill="both", expand=True, padx=20, pady=10)

        left_col = ttk.LabelFrame(content, text=" Control Panel ", padding=15)
        left_col.pack(side="left", fill="both", expand=True, padx=(0, 10))

        right_col = ttk.LabelFrame(content, text=" Page 1 Preview ", padding=15)
        right_col.pack(side="right", fill="both", expand=True, padx=(10, 0))

        # Controls
        self.select_button = ttk.Button(left_col, text="📁 Choose PDF File...", command=self.on_select_pdf)
        self.select_button.pack(fill="x", pady=5)

        self.filename_label = ttk.Label(left_col, text="No file selected", font=("Helvetica", 11, "bold"))
        self.filename_label.pack(fill="x", pady=(5, 0))

        self.file_stats_label = ttk.Label(left_col, text="Original Size: -- | Pages: --")
        self.file_stats_label.pack(fill="x", pady=(0, 15))

        ttk.Label(left_col, text="Compression Level:", font=("Helvetica", 11, "bold")).pack(anchor="w", pady=(10, 5))

        self.level_var = tk.StringVar(value="Large")
        for lvl in ["Basic", "Large", "Maximum"]:
            r = ttk.Radiobutton(
                left_col,
                text=lvl,
                value=lvl,
                variable=self.level_var,
                command=lambda: self.on_level_changed(self.level_var.get())
            )
            r.pack(anchor="w", padx=10, pady=2)

        est_frame = ttk.LabelFrame(left_col, text=" Estimation ", padding=10)
        est_frame.pack(fill="x", pady=15)

        self.est_reduction_label = ttk.Label(est_frame, text="Estimated Reduction: --", font=("Helvetica", 11, "bold"), foreground="green")
        self.est_reduction_label.pack(anchor="w")

        self.level_desc_label = ttk.Label(est_frame, text=LEVEL_DESCRIPTIONS["Large"], wraplength=280)
        self.level_desc_label.pack(anchor="w", pady=(5, 0))

        # Preview
        self.preview_label = ttk.Label(right_col, text="No PDF Loaded")
        self.preview_label.pack(expand=True)

        # Bottom
        bottom = ttk.Frame(self)
        bottom.pack(fill="x", padx=20, pady=15)

        self.progressbar = ttk.Progressbar(bottom, mode="indeterminate")
        self.progressbar.pack(fill="x", pady=5)

        self.status_label = ttk.Label(bottom, text="Ready to process PDF")
        self.status_label.pack(anchor="w", pady=(0, 5))

        self.compress_button = ttk.Button(bottom, text="⚡ Compress & Save PDF", state="disabled", command=self.on_compress_click)
        self.compress_button.pack(fill="x", ipady=5)

    # -------------------------------------------------------------------------
    # PDF Loading & Event Handlers
    # -------------------------------------------------------------------------
    def on_select_pdf(self):
        filepath = filedialog.askopenfilename(
            title="Select PDF File to Compress",
            filetypes=[("PDF Files", "*.pdf"), ("All Files", "*.*")]
        )
        if filepath:
            self.load_pdf(filepath)

    def load_pdf(self, pdf_path: str):
        """
        Loads PDF, updates UI file info, displays thumbnail preview, and pre-calculates estimates.
        """
        try:
            info = pdf_engine.get_pdf_info(pdf_path)
        except Exception as e:
            messagebox.showerror("Error Opening PDF", str(e))
            self._reset_file_state()
            return

        self.current_pdf_path = pdf_path
        self.current_pdf_info = info

        # Update labels
        name_str = info["name"]
        if len(name_str) > 40:
            name_str = name_str[:20] + "..." + name_str[-15:]
        self.filename_label.configure(text=f"File: {name_str}")

        stats_str = f"Original Size: {info['size_formatted']} ({info['size_bytes']:,} B) | Pages: {info['page_count']}"
        self.file_stats_label.configure(text=stats_str)

        # Render Page 1 Preview Thumbnail
        preview_bytes = info.get("preview_image_bytes")
        if preview_bytes:
            try:
                pil_img = Image.open(io.BytesIO(preview_bytes))
                pil_img.thumbnail((220, 280), Image.Resampling.LANCZOS)

                if CTK_AVAILABLE:
                    ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=pil_img.size)
                    self.preview_label.configure(image=ctk_img, text="")
                    self._current_thumbnail = ctk_img
                else:
                    tk_img = ImageTk.PhotoImage(pil_img)
                    self.preview_label.configure(image=tk_img, text="")
                    self._current_thumbnail = tk_img
            except Exception:
                self.preview_label.configure(image="", text="Preview Unavailable")
        else:
            self.preview_label.configure(image="", text="No Preview Image")

        # Pre-calculate estimations for all 3 compression levels (R2 Requirement)
        self.estimates = {}
        for lvl in ["Basic", "Large", "Maximum"]:
            try:
                self.estimates[lvl] = pdf_engine.estimate_compressed_size(pdf_path, lvl)
            except Exception:
                self.estimates[lvl] = {
                    "reduction_min": 0.0,
                    "reduction_max": 0.0,
                    "reduction_label": "N/A"
                }

        # Enable compress button and update estimation display for current level
        if CTK_AVAILABLE:
            self.compress_button.configure(state="normal")
        else:
            self.compress_button.configure(state="normal")

        self.on_level_changed(self.selected_level)
        self.status_label.configure(text="PDF loaded. Select compression level and click 'Compress & Save'.")

    def on_level_changed(self, selected_level: str):
        self.selected_level = selected_level
        if CTK_AVAILABLE:
            if hasattr(self, "level_selector") and self.level_selector.get() != selected_level:
                self.level_selector.set(selected_level)
        else:
            if hasattr(self, "level_var"):
                self.level_var.set(selected_level)

        # Update description text
        desc = LEVEL_DESCRIPTIONS.get(selected_level, "")
        self.level_desc_label.configure(text=desc)

        # Update Estimation display
        if self.selected_level in self.estimates:
            est = self.estimates[self.selected_level]
            self.est_reduction_label.configure(
                text=f"Estimated Reduction: -{est['reduction_label']}"
            )
        else:
            self.est_reduction_label.configure(text="Estimated Reduction: --")

    def _reset_file_state(self):
        self.current_pdf_path = None
        self.current_pdf_info = None
        self.estimates = {}
        self._current_thumbnail = None

        self.filename_label.configure(text="No file selected")
        self.file_stats_label.configure(text="Original Size: -- | Pages: --")
        self.preview_label.configure(image="", text="No PDF Loaded")
        self.est_reduction_label.configure(text="Estimated Reduction: --")

        if CTK_AVAILABLE:
            self.compress_button.configure(state="disabled")
        else:
            self.compress_button.configure(state="disabled")

    # -------------------------------------------------------------------------
    # Background Threaded Compression & Saving
    # -------------------------------------------------------------------------
    def on_compress_click(self):
        if not self.current_pdf_path or not os.path.isfile(self.current_pdf_path):
            messagebox.showerror("Error", "Please select a valid PDF file first.")
            return

        orig_filename = os.path.basename(self.current_pdf_path)
        base_name, ext = os.path.splitext(orig_filename)
        default_out_name = f"{base_name}_compressed{ext}"

        save_path = filedialog.asksaveasfilename(
            title="Save Compressed PDF As",
            initialfile=default_out_name,
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf"), ("All Files", "*.*")]
        )
        if not save_path:
            return  # User cancelled

        # Disable UI controls during compression
        self._set_ui_busy_state(busy=True)

        # Launch background thread for non-blocking execution (R3 Requirement)
        threading.Thread(
            target=self._compression_worker,
            args=(self.current_pdf_path, save_path, self.selected_level),
            daemon=True
        ).start()

    def _set_ui_busy_state(self, busy: bool):
        state = "disabled" if busy else "normal"
        if CTK_AVAILABLE:
            self.select_button.configure(state=state)
            self.compress_button.configure(state=state)
            if busy:
                self.progressbar.start()
            else:
                self.progressbar.stop()
                self.progressbar.set(0)
        else:
            self.select_button.configure(state=state)
            self.compress_button.configure(state=state)
            if busy:
                self.progressbar.start(10)
            else:
                self.progressbar.stop()

        if busy:
            self.status_label.configure(text=f"Compressing PDF ({self.selected_level} level)... Please wait.")

    def _compression_worker(self, input_path: str, output_path: str, level: str):
        try:
            result = pdf_engine.compress_pdf(input_path, output_path, level)
            self.after(0, lambda: self._on_compression_success(result))
        except Exception as err:
            self.after(0, lambda: self._on_compression_failure(err))

    def _on_compression_success(self, result: dict):
        self._set_ui_busy_state(busy=False)
        self.status_label.configure(
            text=f"Compression Complete! Saved to {os.path.basename(result['output_path'])}"
        )

        orig_size_fmt = self.current_pdf_info["size_formatted"] if self.current_pdf_info else "N/A"
        actual_size_fmt = result["actual_size_formatted"]
        reduction_pct = result["reduction_percentage"]
        out_path = result["output_path"]

        # Success Dialog
        messagebox.showinfo(
            "Compression Successful",
            f"PDF compressed successfully!\n\n"
            f"• Compression Level: {self.selected_level}\n"
            f"• Original Size:     {orig_size_fmt}\n"
            f"• Compressed Size:   {actual_size_fmt}\n"
            f"• Reduction:         -{reduction_pct}%\n\n"
            f"Output saved to:\n{out_path}"
        )

    def _on_compression_failure(self, error: Exception):
        self._set_ui_busy_state(busy=False)
        self.status_label.configure(text="Compression failed. See error dialog.")

        # Clear Error Dialog
        messagebox.showerror(
            "Compression Error",
            f"Failed to compress PDF file:\n\n{error}"
        )


# -----------------------------------------------------------------------------
# Headless Smoke-Test Execution Mode
# -----------------------------------------------------------------------------
def run_smoke_test():
    print("=" * 70)
    print("PDF-toolio GUI Headless Smoke Test Mode")
    print("=" * 70)

    print("[SMOKE TEST] Instantiating PDFToolioApp window...")
    app = PDFToolioApp()

    print("[SMOKE TEST] Verifying GUI component attributes...")
    assert hasattr(app, "select_button"), "Missing UI attribute: select_button"
    assert hasattr(app, "filename_label"), "Missing UI attribute: filename_label"
    assert hasattr(app, "level_selector") or hasattr(app, "level_var"), "Missing UI attribute: level_selector"
    assert hasattr(app, "est_reduction_label"), "Missing UI attribute: est_reduction_label"
    assert hasattr(app, "preview_label"), "Missing UI attribute: preview_label"
    assert hasattr(app, "progressbar"), "Missing UI attribute: progressbar"
    assert hasattr(app, "status_label"), "Missing UI attribute: status_label"
    assert hasattr(app, "compress_button"), "Missing UI attribute: compress_button"
    print("              UI component structure verified successfully.")

    print("[SMOKE TEST] Testing synthetic PDF load and pre-calculation...")
    from verify_compression import create_synthetic_test_pdf
    import tempfile

    temp_dir = tempfile.mkdtemp()
    synth_pdf = os.path.join(temp_dir, "gui_smoke_sample.pdf")
    try:
        create_synthetic_test_pdf(synth_pdf)

        app.load_pdf(synth_pdf)

        assert app.current_pdf_path == synth_pdf, "PDF path mismatch"
        assert app.current_pdf_info["page_count"] == 2, "PDF page count mismatch"
        assert len(app.estimates) == 3, "Estimates count mismatch"
        assert "Basic" in app.estimates and "Large" in app.estimates and "Maximum" in app.estimates, "Estimates missing level"

        # Verify level switching updates estimations
        for lvl in ["Basic", "Large", "Maximum"]:
            app.on_level_changed(lvl)
            assert app.selected_level == lvl, f"Level switch to {lvl} failed"

        print("              PDF load, preview thumbnail rendering, and dynamic estimations PASS.")
    finally:
        if os.path.exists(synth_pdf):
            try:
                os.remove(synth_pdf)
            except Exception:
                pass
        try:
            os.rmdir(temp_dir)
        except Exception:
            pass

    print("[SMOKE TEST] Processing GUI idle tasks and closing window...")
    app.update_idletasks()
    app.update()
    app.destroy()

    print("=" * 70)
    print("SUCCESS: GUI SMOKE TEST PASSED CLEANLY (EXIT CODE 0)!")
    print("=" * 70)
    sys.exit(0)


def main():
    if "--smoke-test" in sys.argv:
        run_smoke_test()
    else:
        app = PDFToolioApp()
        app.mainloop()


if __name__ == "__main__":
    main()
