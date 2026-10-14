"""
verify_compression.py - E2E Verification Test Harness for PDF Compression Engine

Creates synthetic test PDFs containing high-DPI images and text, processes them across
Basic, Large, and Maximum compression levels, and verifies size reduction invariants,
rendering, and structural readability.
"""

import os
import io
import sys
import math
import fitz
from PIL import Image, ImageDraw, ImageFilter

from pdf_engine import format_size, get_pdf_info, estimate_compressed_size, compress_pdf


def create_photographic_test_image(width: int, height: int, seed: int = 1) -> Image.Image:
    """
    Generate a high-entropy, photographic-style synthetic image with continuous color gradients,
    layered translucent objects, continuous spatial tone variations, and smooth blur filtering.
    """
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)

    # 1. Multi-frequency continuous color gradient background
    for y in range(height):
        r = int(127.5 + 127.5 * math.sin(2 * math.pi * y / height + seed))
        g = int(127.5 + 127.5 * math.cos(2 * math.pi * y / (height * 0.6) + seed * 2))
        b = int(127.5 + 127.5 * math.sin(2 * math.pi * y / (height * 0.3) + seed * 3))
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # 2. Overlapping translucent shapes with high color variation
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)

    cx, cy = width // 2, height // 2
    max_dim = max(width, height)
    num_elements = 100

    for i in range(num_elements):
        t = i / num_elements
        angle = t * 6 * math.pi
        rad = (0.05 + 0.8 * t) * (max_dim // 2)
        x = int(cx + rad * math.cos(angle))
        y = int(cy + rad * math.sin(angle))
        rw = max(10, int(min(width, height) * (0.05 + 0.10 * (0.5 + 0.5 * math.sin(i * 0.4)))))
        rh = max(10, int(min(width, height) * (0.05 + 0.10 * (0.5 + 0.5 * math.cos(i * 0.4)))))

        cr = int(255 * (0.5 + 0.5 * math.sin(t * 10)))
        cg = int(255 * (0.5 + 0.5 * math.cos(t * 7)))
        cb = int(255 * (0.5 + 0.5 * math.sin(t * 13)))
        alpha = int(120 + 100 * math.sin(t * 5))

        ov_draw.ellipse([x - rw, y - rh, x + rw, y + rh], fill=(cr, cg, cb, alpha))
        ov_draw.rectangle([x - rh // 2, y - rw // 2, x + rh // 2, y + rw // 2], outline=(255 - cr, 255 - cg, 255 - cb, alpha), width=4)

    img.paste(overlay, (0, 0), overlay)

    # 3. Gaussian blur filter to simulate photographic optical continuous tones
    img = img.filter(ImageFilter.GaussianBlur(radius=4))
    return img


def create_synthetic_test_pdf(filepath: str) -> str:
    """
    Generate a multi-page synthetic test PDF with 300+ DPI photographic-style images and vector text.
    """
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    doc = fitz.open()

    # Image 1: 1600x2000 px image (High DPI ~225 DPI when drawn in 512x650 pt rect)
    img1 = create_photographic_test_image(1600, 2000, seed=1)
    buf1 = io.BytesIO()
    img1.save(buf1, format="PNG")
    png_bytes1 = buf1.getvalue()

    page1 = doc.new_page(width=612, height=792)
    page1.insert_text((50, 40), "PDF-toolio Synthetic Test Document - Page 1", fontsize=16)
    page1.insert_text((50, 65), "Verification harness for Basic, Large, and Maximum compression levels.", fontsize=11)
    page1.insert_image(fitz.Rect(50, 90, 562, 740), stream=png_bytes1)

    # Image 2: 2400x2400 px image (High DPI > 330 DPI when placed in 512x510 pt rect)
    img2 = create_photographic_test_image(2400, 2400, seed=2)
    buf2 = io.BytesIO()
    img2.save(buf2, format="PNG")
    png_bytes2 = buf2.getvalue()

    page2 = doc.new_page(width=612, height=792)
    page2.insert_text((50, 40), "PDF-toolio Synthetic Test Document - Page 2", fontsize=16)
    page2.insert_image(fitz.Rect(50, 90, 562, 600), stream=png_bytes2)

    # Save initial uncompressed synthetic PDF
    doc.save(filepath, deflate=False)
    doc.close()

    return filepath


def pixmap_is_blank(pix: fitz.Pixmap) -> bool:
    """
    Check if a rendered PyMuPDF Pixmap is visually blank (e.g. uniform blank white/solid canvas).
    Returns True if the pixmap is empty or has uniform/near-zero variation color, False otherwise.
    """
    if not pix or pix.width == 0 or pix.height == 0:
        return True

    samples = bytes(pix.samples)
    if not samples:
        return True

    min_sample = min(samples)
    max_sample = max(samples)

    if min_sample == max_sample:
        return True

    if (max_sample - min_sample) < 10:
        return True

    return False


def run_verification():
    print("=" * 70)
    print("PDF-toolio E2E Verification Harness")
    print("=" * 70)

    test_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_assets")
    synth_pdf_path = os.path.join(test_dir, "synthetic_sample.pdf")

    print(f"\n[1/5] Generating synthetic test PDF: {synth_pdf_path}")
    create_synthetic_test_pdf(synth_pdf_path)
    orig_size = os.path.getsize(synth_pdf_path)
    print(f"      Original PDF created cleanly ({orig_size} bytes, {format_size(orig_size)})")

    print("\n[2/5] Testing get_pdf_info()...")
    info = get_pdf_info(synth_pdf_path)
    assert info["name"] == "synthetic_sample.pdf", f"Expected name 'synthetic_sample.pdf', got {info['name']}"
    assert info["size_bytes"] == orig_size, f"Size mismatch: {info['size_bytes']} vs {orig_size}"
    assert info["page_count"] == 2, f"Expected 2 pages, got {info['page_count']}"
    assert isinstance(info["preview_image_bytes"], bytes) and len(info["preview_image_bytes"]) > 0, "Page 1 preview image bytes empty"
    print(f"      get_pdf_info PASS: 2 pages, preview size {len(info['preview_image_bytes'])} PNG bytes.")

    print("\n[3/5] Testing estimate_compressed_size()...")
    est_basic = estimate_compressed_size(synth_pdf_path, "Basic")
    est_large = estimate_compressed_size(synth_pdf_path, "Large")
    est_max = estimate_compressed_size(synth_pdf_path, "Maximum")

    print(f"      Estimate Basic:   {est_basic['reduction_label']}")
    print(f"      Estimate Large:   {est_large['reduction_label']}")
    print(f"      Estimate Maximum: {est_max['reduction_label']}")

    assert est_basic["reduction_min"] >= 0, "Basic reduction_min should be >= 0"
    assert est_large["reduction_min"] >= est_basic["reduction_min"], "Large reduction should be >= Basic"
    assert est_max["reduction_min"] >= est_large["reduction_min"], "Maximum reduction should be >= Large"
    print("      estimate_compressed_size PASS.")

    print("\n[4/5] Running PDF Compression Engine across Basic, Large, Maximum...")
    out_basic_path = os.path.join(test_dir, "output_basic.pdf")
    out_large_path = os.path.join(test_dir, "output_large.pdf")
    out_max_path = os.path.join(test_dir, "output_maximum.pdf")

    res_basic = compress_pdf(synth_pdf_path, out_basic_path, "Basic")
    res_large = compress_pdf(synth_pdf_path, out_large_path, "Large")
    res_max = compress_pdf(synth_pdf_path, out_max_path, "Maximum")

    size_orig = orig_size
    size_basic = res_basic["actual_size_bytes"]
    size_large = res_large["actual_size_bytes"]
    size_max = res_max["actual_size_bytes"]

    print(f"      Original: {format_size(size_orig)} ({size_orig} B)")
    print(f"      Basic:    {format_size(size_basic)} ({size_basic} B, -{res_basic['reduction_percentage']}%)")
    print(f"      Large:    {format_size(size_large)} ({size_large} B, -{res_large['reduction_percentage']}%)")
    print(f"      Maximum:  {format_size(size_max)} ({size_max} B, -{res_max['reduction_percentage']}%)")

    # Invariant checks
    print("\n[5/5] Verifying Invariants and Structural Integrity...")
    assert size_basic < size_orig, f"Strict Invariant Violation: size(Basic) [{size_basic} B] >= size(Original) [{size_orig} B]"
    assert size_large < size_basic, f"Strict Invariant Violation: size(Large) [{size_large} B] >= size(Basic) [{size_basic} B]"
    assert size_max < size_large, f"Strict Invariant Violation: size(Maximum) [{size_max} B] >= size(Large) [{size_large} B]"

    # Readability, valid PDF, and visual render non-blankness checks across all pages
    for label, path in [("Basic", out_basic_path), ("Large", out_large_path), ("Maximum", out_max_path)]:
        doc_check = fitz.open(path)
        assert len(doc_check) == 2, f"Corrupted PDF in {label}: expected 2 pages, got {len(doc_check)}"
        for page_idx in range(len(doc_check)):
            page = doc_check[page_idx]
            pix_check = page.get_pixmap(dpi=72)
            assert pix_check.width > 0 and pix_check.height > 0, f"Page {page_idx + 1} render failed for {label}"
            assert not pixmap_is_blank(pix_check), f"Page {page_idx + 1} in {label} rendered as blank visual content"
        doc_check.close()
    print("      Visual render non-blankness & readability checks PASS across all pages and levels.")
    # Corrupted PDF handling check
    corrupt_pdf_path = os.path.join(test_dir, "corrupt_sample.pdf")
    with open(corrupt_pdf_path, "wb") as f:
        f.write(b"NOT_A_VALID_PDF_FILE_HEADER_1234567890")

    try:
        get_pdf_info(corrupt_pdf_path)
        assert False, "get_pdf_info failed to raise ValueError for corrupted PDF"
    except ValueError as ve:
        assert "Invalid or corrupted PDF file" in str(ve), f"Unexpected exception message: {ve}"
        print("      Corrupted file handling in get_pdf_info PASS.")

    try:
        compress_pdf(corrupt_pdf_path, os.path.join(test_dir, "corrupt_out.pdf"), "Basic")
        assert False, "compress_pdf failed to raise ValueError for corrupted PDF"
    except ValueError as ve:
        assert "Invalid or corrupted PDF file" in str(ve), f"Unexpected exception message: {ve}"
        print("      Corrupted file handling in compress_pdf PASS.")

    print("\n" + "=" * 70)
    print("SUCCESS: ALL E2E COMPRESSION ASSERTIONS PASSED CLEANLY!")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(run_verification())
    except Exception as e:
        print(f"\nVERIFICATION FAILURE: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
