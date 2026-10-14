"""
pdf_engine.py - Core PDF Compression Engine & Utilities

Provides PDF metadata inspection, page 1 preview rendering, pre-compression size estimation,
and multi-level PDF compression (Basic, Large, Maximum) using PyMuPDF (fitz) and Pillow (PIL).
"""

import os
import io
import math
import logging
import fitz  # PyMuPDF
from PIL import Image

logger = logging.getLogger(__name__)


def format_size(size_bytes: int) -> str:
    """
    Format a byte count into a human-readable string (e.g., '1.2 MB', '450 KB', '800 B').
    """
    if size_bytes < 0:
        size_bytes = 0

    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        val = size_bytes / 1024.0
        val_str = f"{val:.1f}"
        if val_str.endswith(".0"):
            val_str = val_str[:-2]
        return f"{val_str} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        val = size_bytes / (1024.0 * 1024.0)
        val_str = f"{val:.1f}"
        if val_str.endswith(".0"):
            val_str = val_str[:-2]
        return f"{val_str} MB"
    else:
        val = size_bytes / (1024.0 * 1024.0 * 1024.0)
        val_str = f"{val:.1f}"
        if val_str.endswith(".0"):
            val_str = val_str[:-2]
        return f"{val_str} GB"


def get_pdf_info(pdf_path: str) -> dict:
    """
    Inspect a PDF file and return basic metadata & Page 1 preview thumbnail as PNG bytes.

    Returns:
        {
            "name": str,
            "size_bytes": int,
            "size_formatted": str,
            "preview_image_bytes": bytes,
            "page_count": int
        }
    """
    if not os.path.isfile(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    size_bytes = os.path.getsize(pdf_path)
    file_name = os.path.basename(pdf_path)

    try:
        doc = fitz.open(pdf_path)
    except fitz.FileDataError:
        raise ValueError(f"Invalid or corrupted PDF file: {pdf_path}")

    try:
        if doc.is_encrypted:
            raise ValueError("Encrypted PDF files are not supported without a password.")
        page_count = len(doc)
        preview_bytes = b""
        if page_count > 0:
            page = doc[0]
            pix = page.get_pixmap(dpi=96)
            preview_bytes = pix.tobytes("png")

        return {
            "name": file_name,
            "size_bytes": size_bytes,
            "size_formatted": format_size(size_bytes),
            "preview_image_bytes": preview_bytes,
            "page_count": page_count
        }
    finally:
        doc.close()


def _analyze_pdf_structure(doc) -> dict:
    """
    Internal helper to inspect PDF image XObjects, stream sizes, and effective DPIs.
    """
    total_image_bytes = 0
    images_meta = []
    processed_xrefs = set()

    for page_idx in range(len(doc)):
        page = doc[page_idx]

        # Get detailed image info for this page
        try:
            image_info_list = page.get_image_info(hashes=False, xrefs=True)
        except Exception:
            image_info_list = []

        for info in image_info_list:
            xref = info.get("xref")
            if not xref or xref in processed_xrefs:
                continue
            processed_xrefs.add(xref)

            width = info.get("width", 0)
            height = info.get("height", 0)
            bbox = info.get("bbox", (0, 0, 0, 0))

            disp_w_pts = abs(bbox[2] - bbox[0])
            disp_h_pts = abs(bbox[3] - bbox[1])

            disp_w_in = disp_w_pts / 72.0 if disp_w_pts > 0 else (width / 72.0 if width > 0 else 1.0)
            disp_h_in = disp_h_pts / 72.0 if disp_h_pts > 0 else (height / 72.0 if height > 0 else 1.0)

            dpi_w = width / disp_w_in if disp_w_in > 0 else 72.0
            dpi_h = height / disp_h_in if disp_h_in > 0 else 72.0
            effective_dpi = max(dpi_w, dpi_h)

            img_bytes_count = 0
            try:
                img_data = doc.extract_image(xref)
                if img_data:
                    img_bytes_count = len(img_data.get("image", b""))
            except Exception:
                img_bytes_count = width * height * 3

            total_image_bytes += img_bytes_count

            images_meta.append({
                "xref": xref,
                "width": width,
                "height": height,
                "disp_w_in": disp_w_in,
                "disp_h_in": disp_h_in,
                "effective_dpi": effective_dpi,
                "original_bytes": img_bytes_count
            })

    return {
        "images_meta": images_meta,
        "total_image_bytes": total_image_bytes
    }


def estimate_compressed_size(pdf_path: str, level: str) -> dict:
    """
    Estimate post-compression reduction range for a given level ('Basic', 'Large', 'Maximum').

    Returns approximate percentage reduction range based on content analysis
    (image-heavy vs text-heavy PDFs compress very differently).

    Returns:
        {
            "reduction_min": float,
            "reduction_max": float,
            "reduction_label": str
        }
    """
    if not os.path.isfile(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    original_size = os.path.getsize(pdf_path)
    if original_size == 0:
        return {
            "reduction_min": 0.0,
            "reduction_max": 0.0,
            "reduction_label": "~0%"
        }

    level_norm = level.strip().capitalize()
    if level_norm not in ("Basic", "Large", "Maximum"):
        level_norm = "Basic"

    try:
        doc = fitz.open(pdf_path)
    except fitz.FileDataError:
        raise ValueError(f"Invalid or corrupted PDF file: {pdf_path}")

    try:
        if doc.is_encrypted:
            raise ValueError("Encrypted PDF files are not supported without a password.")
        analysis = _analyze_pdf_structure(doc)
        total_img_bytes = analysis["total_image_bytes"]

        # Ratio of image data to total file size determines compression potential
        img_ratio = total_img_bytes / original_size if original_size > 0 else 0.0

        if level_norm == "Basic":
            if img_ratio > 0.5:
                reduction_min = 30.0
                reduction_max = 60.0
            elif img_ratio > 0.1:
                reduction_min = 10.0
                reduction_max = 30.0
            else:
                reduction_min = 1.0
                reduction_max = 10.0

        elif level_norm == "Large":
            if img_ratio > 0.5:
                reduction_min = 55.0
                reduction_max = 80.0
            elif img_ratio > 0.1:
                reduction_min = 25.0
                reduction_max = 55.0
            else:
                reduction_min = 5.0
                reduction_max = 25.0

        else:  # Maximum
            if img_ratio > 0.5:
                reduction_min = 75.0
                reduction_max = 95.0
            elif img_ratio > 0.1:
                reduction_min = 45.0
                reduction_max = 75.0
            else:
                reduction_min = 10.0
                reduction_max = 35.0

        reduction_label = f"~{reduction_min:.0f}–{reduction_max:.0f}%"

        return {
            "reduction_min": reduction_min,
            "reduction_max": reduction_max,
            "reduction_label": reduction_label
        }
    finally:
        doc.close()


def _reencode_and_replace_image(doc, xref_info: dict, threshold_dpi: float, target_dpi: float, jpeg_quality: int) -> int:
    """
    Helper function to downsample and re-encode PDF images based on DPI threshold and JPEG quality.
    Iterates directly over unique image xrefs once per document (O(N)).
    Returns number of successfully replaced image streams.
    """
    if len(doc) == 0 or not xref_info:
        return 0

    replaced_count = 0

    for xref, info in xref_info.items():
        max_dpi = info["max_dpi"]
        disp_w_in = info["disp_w_in"]
        disp_h_in = info["disp_h_in"]

        # Extract raw image stream
        try:
            img_dict = doc.extract_image(xref)
        except Exception as err:
            logger.warning(f"Failed to extract image xref {xref}: {err}")
            continue

        if not img_dict:
            logger.warning(f"Empty image dictionary for xref {xref}")
            continue

        image_bytes = img_dict.get("image")
        if not image_bytes:
            logger.warning(f"No image bytes found for xref {xref}")
            continue

        try:
            pil_img = Image.open(io.BytesIO(image_bytes))
        except Exception as err:
            logger.warning(f"Failed to decode image xref {xref} with PIL: {err}")
            continue

        orig_w, orig_h = pil_img.size

        # Determine target dimensions
        need_downsample = max_dpi > threshold_dpi
        if need_downsample:
            target_w = max(1, int(round(disp_w_in * target_dpi)))
            target_h = max(1, int(round(disp_h_in * target_dpi)))
        else:
            target_w, target_h = orig_w, orig_h

        # Convert color mode to RGB for JPEG encoding
        if pil_img.mode in ("RGBA", "LA") or (pil_img.mode == "P" and "transparency" in pil_img.info):
            bg = Image.new("RGB", pil_img.size, (255, 255, 255))
            if pil_img.mode != "RGBA":
                pil_img = pil_img.convert("RGBA")
            bg.paste(pil_img, mask=pil_img.split()[3])
            pil_img = bg
        elif pil_img.mode != "RGB":
            pil_img = pil_img.convert("RGB")

        # Resize if target dimensions are smaller than original
        if target_w < orig_w or target_h < orig_h:
            pil_img = pil_img.resize((target_w, target_h), Image.Resampling.LANCZOS)

        # Re-encode to JPEG
        out_buffer = io.BytesIO()
        pil_img.save(out_buffer, format="JPEG", quality=jpeg_quality, optimize=True)
        new_jpg_bytes = out_buffer.getvalue()

        # Do not replace if re-encoded image stream is not smaller than original image stream,
        # unless downsampling actually occurred (where resolution reduction is mandatory).
        is_downsampled = (target_w < orig_w) or (target_h < orig_h)
        if not is_downsampled and len(new_jpg_bytes) >= len(image_bytes):
            continue

        # Perform replacement on fitz.Document using PyMuPDF doc.update_image API
        replacement_success = False
        try:
            # Primary PyMuPDF Document API
            doc.update_image(xref, stream=new_jpg_bytes)
            replacement_success = True
        except (AttributeError, TypeError, Exception) as primary_err:
            logger.warning(f"Primary doc.update_image(xref, stream=...) failed for xref {xref}: {primary_err}")
            try:
                # Secondary PyMuPDF method: Pixmap wrapper
                new_pix = fitz.Pixmap(new_jpg_bytes)
                doc.update_image(xref, pixmap=new_pix)
                replacement_success = True
            except Exception as sec_err:
                logger.warning(f"Secondary doc.update_image(xref, pixmap=...) failed for xref {xref}: {sec_err}")
                try:
                    # Low-level fallback: update_stream + xref metadata dictionary sync
                    # compress=0 prevents PyMuPDF from wrapping JPEG bytes in FlateDecode
                    doc.update_stream(xref, new_jpg_bytes, compress=0)
                    doc.xref_set_key(xref, "Width", str(target_w))
                    doc.xref_set_key(xref, "Height", str(target_h))
                    doc.xref_set_key(xref, "Filter", "/DCTDecode")
                    doc.xref_set_key(xref, "ColorSpace", "/DeviceRGB")
                    doc.xref_set_key(xref, "BitsPerComponent", "8")
                    replacement_success = True
                except Exception as fallback_err:
                    logger.error(f"All image stream replacement methods failed for xref {xref}: {fallback_err}")
                    raise RuntimeError(f"Failed to replace image stream for xref {xref}: {fallback_err}") from fallback_err

        if replacement_success:
            doc.xref_set_key(xref, "Width", str(target_w))
            doc.xref_set_key(xref, "Height", str(target_h))
            replaced_count += 1

    return replaced_count


def compress_pdf(input_path: str, output_path: str, level: str) -> dict:
    """
    Compress a PDF file according to the selected compression level.

    Levels:
        - "Basic": Stream deflate (deflate=True), garbage collection (garbage=4), metadata cleaning.
        - "Large": Basic + downsampling raster images >150 DPI to 150 DPI + re-encoding to JPEG Q=75.
        - "Maximum": Basic + downsampling raster images >96 DPI to 96 DPI + re-encoding to JPEG Q=50.

    Saves compressed output file to `output_path`.

    Returns:
        {
            "output_path": str,
            "actual_size_bytes": int,
            "actual_size_formatted": str,
            "reduction_percentage": float
        }
    """
    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"Input PDF file not found: {input_path}")

    original_size = os.path.getsize(input_path)
    level_norm = level.strip().capitalize()
    if level_norm not in ("Basic", "Large", "Maximum"):
        level_norm = "Basic"

    # Ensure target output directory exists
    out_dir = os.path.dirname(os.path.abspath(output_path))
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    try:
        doc = fitz.open(input_path)
    except fitz.FileDataError:
        raise ValueError(f"Invalid or corrupted PDF file: {input_path}")

    try:
        if doc.is_encrypted:
            raise ValueError("Encrypted PDF files are not supported without a password.")
        # Clean metadata across all levels
        doc.set_metadata({
            "producer": "PDF-toolio",
            "creator": "PDF-toolio Core Engine"
        })

        # Gather image effective DPIs for all levels (all levels do image re-encoding)
        xref_info = {}
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            try:
                img_infos = page.get_image_info(hashes=False, xrefs=True)
            except Exception:
                img_infos = []

            for info in img_infos:
                xref = info.get("xref")
                if not xref or xref <= 0:
                    continue

                w = info.get("width", 0)
                h = info.get("height", 0)
                bbox = info.get("bbox", (0, 0, 0, 0))

                disp_w_pts = abs(bbox[2] - bbox[0])
                disp_h_pts = abs(bbox[3] - bbox[1])

                disp_w_in = disp_w_pts / 72.0 if disp_w_pts > 0 else (w / 72.0 if w > 0 else 1.0)
                disp_h_in = disp_h_pts / 72.0 if disp_h_pts > 0 else (h / 72.0 if h > 0 else 1.0)

                dpi_w = w / disp_w_in if disp_w_in > 0 else 72.0
                dpi_h = h / disp_h_in if disp_h_in > 0 else 72.0
                effective_dpi = max(dpi_w, dpi_h)

                if xref not in xref_info or effective_dpi > xref_info[xref]["max_dpi"]:
                    xref_info[xref] = {
                        "max_dpi": effective_dpi,
                        "disp_w_in": disp_w_in,
                        "disp_h_in": disp_h_in,
                        "width": w,
                        "height": h,
                        "page_idx": page_idx
                    }

        # If get_image_info didn't pick up all xrefs, scan page images directly
        for page_idx in range(len(doc)):
            try:
                p_imgs = doc.get_page_images(page_idx)
            except Exception:
                p_imgs = []
            for p_img in p_imgs:
                xref = p_img[0]
                if xref > 0 and xref not in xref_info:
                    w = p_img[2]
                    h = p_img[3]
                    disp_w_in = w / 300.0 if w > 0 else 1.0
                    disp_h_in = h / 300.0 if h > 0 else 1.0
                    xref_info[xref] = {
                        "max_dpi": 300.0,
                        "disp_w_in": disp_w_in,
                        "disp_h_in": disp_h_in,
                        "width": w,
                        "height": h,
                        "page_idx": page_idx
                    }

        # Evenly spaced compression levels:
        #   Basic:   keep original DPI, JPEG Q=95 (re-encode only, near-lossless)
        #   Large:   downsample >200 DPI to 200, JPEG Q=85
        #   Maximum: downsample >96 DPI to 96, JPEG Q=50
        if level_norm == "Basic":
            _reencode_and_replace_image(
                doc=doc,
                xref_info=xref_info,
                threshold_dpi=9999.0,
                target_dpi=300.0,
                jpeg_quality=95
            )
        elif level_norm == "Large":
            _reencode_and_replace_image(
                doc=doc,
                xref_info=xref_info,
                threshold_dpi=200.0,
                target_dpi=200.0,
                jpeg_quality=85
            )
        elif level_norm == "Maximum":
            _reencode_and_replace_image(
                doc=doc,
                xref_info=xref_info,
                threshold_dpi=96.0,
                target_dpi=96.0,
                jpeg_quality=50
            )

        # Save compressed document with deflate, garbage collection, clean streams
        doc.save(
            output_path,
            garbage=4,
            deflate=True,
            clean=True
        )

    finally:
        doc.close()

    actual_size = os.path.getsize(output_path)
    reduction_pct = max(0.0, round((1.0 - (actual_size / original_size)) * 100.0, 2)) if original_size > 0 else 0.0

    return {
        "output_path": output_path,
        "actual_size_bytes": actual_size,
        "actual_size_formatted": format_size(actual_size),
        "reduction_percentage": reduction_pct
    }
