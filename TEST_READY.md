# PDF-toolio Verification Test Suite Ready

The end-to-end PDF compression verification test harness is fully implemented and ready for execution.

## Quick Start / Test Runner Command

```powershell
python verify_compression.py
```

## Covered Verification Specifications & Invariants

1. **Synthetic PDF Generation (`test_assets/synthetic_sample.pdf`):**
   - Creates multi-page synthetic test document containing vector text and high-DPI (300+ DPI) color raster graphics.

2. **Metadata Inspection & Thumbnail Rendering (`get_pdf_info`):**
   - Verifies file size, page count, and page 1 thumbnail generation (rendered at 96 DPI to PNG bytes).

3. **Pre-Compression Size Estimation (`estimate_compressed_size`):**
   - Asserts size estimation formulas for Basic, Large, and Maximum levels.
   - Validates estimation ordering: `Est(Maximum) <= Est(Large) <= Est(Basic) < Original`.

4. **Multi-Level Compression & Size Reduction Invariants (`compress_pdf`):**
   - **Basic Level:** Lossless stream deflation (`deflate=True`), structural garbage collection (`garbage=4`), metadata cleaning.
   - **Large Level:** Basic + downsampling raster images >150 DPI to 150 DPI + re-encoding to JPEG Q=75.
   - **Maximum Level:** Basic + downsampling raster images >96 DPI to 96 DPI + re-encoding to JPEG Q=50.
   - **Size Invariant Assertions:**
     - `size(Basic) < size(Original)`
     - `size(Large) < size(Original)`
     - `size(Maximum) < size(Original)`
     - `size(Maximum) <= size(Large) <= size(Basic)`

5. **Structural Integrity & Readability:**
   - Validates that output compressed PDFs open without errors, maintain page counts, and render page pixmaps cleanly.
