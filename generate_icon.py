"""
generate_icon.py
Generates a modern minimalist multi-resolution Windows icon (pdf_icon.ico)
for PDF-toolio.
"""

import os
import sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter


def get_fonts(font_size_pdf: int, font_size_tool: int):
    """
    Attempts to load clean sans-serif system fonts in priority order.
    Returns tuple of (font_pdf, font_tool).
    """
    font_candidates = [
        "segoeuib.ttf",   # Segoe UI Bold (Windows standard)
        "arialbd.ttf",    # Arial Bold
        "calibrib.ttf",   # Calibri Bold
        "trebucbd.ttf",   # Trebuchet MS Bold
        "verdanab.ttf",   # Verdana Bold
    ]

    for font_name in font_candidates:
        try:
            font_pdf = ImageFont.truetype(font_name, font_size_pdf)
            font_tool = ImageFont.truetype(font_name, font_size_tool)
            return font_pdf, font_tool
        except IOError:
            continue

    # Fallback if no TTF found
    return ImageFont.load_default(), ImageFont.load_default()


def generate_icon(output_path: str = "pdf_icon.ico", canvas_size: int = 512):
    """
    Creates high-DPI canvas, renders modern card background, drop shadow,
    and two-line typography ('PDF' / 'tool' + 'io'), then saves multi-size .ico.
    """
    # 1. Base Canvas (Transparent RGBA)
    img = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))

    # 2. Card Geometry
    margin = 32
    card_box = [margin, margin, canvas_size - margin, canvas_size - margin]
    corner_radius = 80

    # 3. Soft Drop Shadow
    shadow = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_box = [margin + 4, margin + 12, canvas_size - margin + 4, canvas_size - margin + 12]
    shadow_draw.rounded_rectangle(shadow_box, radius=corner_radius, fill=(0, 0, 0, 110))
    shadow = shadow.filter(ImageFilter.GaussianBlur(16))

    # Composite shadow onto base canvas
    img = Image.alpha_composite(img, shadow)

    # 4. Main Card Background (Dark Slate Blue #0F172A)
    bg_color = (15, 23, 42, 255)       # #0F172A (Slate 900)
    border_color = (51, 65, 85, 255)   # #334155 (Slate 700)

    card_draw = ImageDraw.Draw(img)
    card_draw.rounded_rectangle(card_box, radius=corner_radius, fill=bg_color, outline=border_color, width=4)

    # 5. Typography Colors & Sizes
    font_size_pdf = 140
    font_size_tool = 96
    font_pdf, font_tool = get_fonts(font_size_pdf, font_size_tool)

    draw = ImageDraw.Draw(img)

    color_pdf = (239, 68, 68, 255)     # Crimson Red (#EF4444)
    color_tool = (255, 255, 255, 255)  # Pure White (#FFFFFF)
    color_io = (56, 189, 248, 255)      # Electric Sky Blue (#38BDF8)

    # 6. Text Dimensions & Bounding Boxes
    bbox_pdf = draw.textbbox((0, 0), "PDF", font=font_pdf)
    pdf_w = bbox_pdf[2] - bbox_pdf[0]
    pdf_h = bbox_pdf[3] - bbox_pdf[1]

    bbox_tool = draw.textbbox((0, 0), "tool", font=font_tool)
    tool_w = bbox_tool[2] - bbox_tool[0]
    tool_h = bbox_tool[3] - bbox_tool[1]

    bbox_io = draw.textbbox((0, 0), "io", font=font_tool)
    io_w = bbox_io[2] - bbox_io[0]
    io_h = bbox_io[3] - bbox_io[1]

    line2_w = tool_w + io_w
    line2_h = max(tool_h, io_h)

    gap = 24
    total_content_h = pdf_h + gap + line2_h

    # 7. Vertical Placement
    card_center_y = canvas_size / 2
    start_y = card_center_y - (total_content_h / 2)

    y_pdf = start_y - bbox_pdf[1]
    y_line2 = start_y + pdf_h + gap - min(bbox_tool[1], bbox_io[1])

    # 8. Horizontal Placement & Render
    # Line 1: PDF
    x_pdf = (canvas_size - pdf_w) / 2 - bbox_pdf[0]
    draw.text((x_pdf, y_pdf), "PDF", font=font_pdf, fill=color_pdf)

    # Line 2: tool + io
    start_x_line2 = (canvas_size - line2_w) / 2
    x_tool = start_x_line2 - bbox_tool[0]
    x_io = start_x_line2 + tool_w - bbox_io[0]

    draw.text((x_tool, y_line2), "tool", font=font_tool, fill=color_tool)
    draw.text((x_io, y_line2), "io", font=font_tool, fill=color_io)

    # 9. Save as Multi-Resolution ICO
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(output_path, format="ICO", sizes=sizes)
    print(f"Generated {output_path} with sizes: {sizes}")


if __name__ == "__main__":
    out_file = sys.argv[1] if len(sys.argv) > 1 else "pdf_icon.ico"
    generate_icon(out_file)
