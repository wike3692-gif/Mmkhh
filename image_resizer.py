"""
High-quality image resize tool using Pillow.
Supports JPEG, PNG, WebP, BMP, TIFF and more.
Designed to be used standalone (e.g., Pythonista 3) or via the Flask web app.
"""

from PIL import Image
import io
import os


# Resampling filter that gives the highest quality result
RESAMPLE = Image.Resampling.LANCZOS


def resize_image(
    input_path_or_bytes,
    width=None,
    height=None,
    scale_percent=None,
    keep_aspect_ratio=True,
    output_format=None,
    jpeg_quality=95,
):
    """
    Resize an image with the highest possible quality.

    Parameters
    ----------
    input_path_or_bytes : str | bytes | BytesIO
        File path, raw bytes, or BytesIO object of the source image.
    width : int | None
        Target width in pixels.
    height : int | None
        Target height in pixels.
    scale_percent : float | None
        Scale factor as a percentage (e.g. 50 = 50 %).
        Takes priority over width/height when provided.
    keep_aspect_ratio : bool
        Preserve the original aspect ratio when only one dimension is given.
    output_format : str | None
        Output format string such as 'JPEG', 'PNG', 'WEBP'.
        Detected from the source image when None.
    jpeg_quality : int
        Quality setting for JPEG / WebP output (1–95).
        95 is visually lossless for most images.

    Returns
    -------
    bytes
        The resized image as a bytes object.
    str
        The output format string (e.g. 'JPEG').
    """
    # ── Load ────────────────────────────────────────────────────────────────
    if isinstance(input_path_or_bytes, (str, os.PathLike)):
        img = Image.open(input_path_or_bytes)
    elif isinstance(input_path_or_bytes, bytes):
        img = Image.open(io.BytesIO(input_path_or_bytes))
    else:
        img = Image.open(input_path_or_bytes)

    original_format = output_format or img.format or "PNG"

    # Convert palette / RGBA images to RGB when saving as JPEG
    save_format = original_format.upper()
    if save_format in ("JPG",):
        save_format = "JPEG"

    # ── Compute target size ─────────────────────────────────────────────────
    orig_w, orig_h = img.size

    if scale_percent is not None:
        factor = scale_percent / 100.0
        new_w = max(1, int(orig_w * factor))
        new_h = max(1, int(orig_h * factor))
    elif width and height:
        if keep_aspect_ratio:
            ratio = min(width / orig_w, height / orig_h)
            new_w = max(1, int(orig_w * ratio))
            new_h = max(1, int(orig_h * ratio))
        else:
            new_w, new_h = width, height
    elif width:
        new_w = width
        new_h = max(1, int(orig_h * width / orig_w)) if keep_aspect_ratio else orig_h
    elif height:
        new_h = height
        new_w = max(1, int(orig_w * height / orig_h)) if keep_aspect_ratio else orig_w
    else:
        raise ValueError("Specify at least one of: width, height, scale_percent")

    # ── Resize ──────────────────────────────────────────────────────────────
    # Convert to RGBA for alpha-aware operations, then back as needed
    mode = img.mode
    if save_format == "JPEG" and mode in ("RGBA", "P", "LA"):
        # Composite onto white background to avoid JPEG alpha errors
        background = Image.new("RGB", img.size, (255, 255, 255))
        if mode == "P":
            img = img.convert("RGBA")
        background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
        img = background

    resized = img.resize((new_w, new_h), RESAMPLE)

    # ── Save ────────────────────────────────────────────────────────────────
    buf = io.BytesIO()
    save_kwargs = {}

    if save_format == "JPEG":
        save_kwargs["quality"] = jpeg_quality
        save_kwargs["subsampling"] = 0      # 4:4:4 — maximum colour detail
        save_kwargs["optimize"] = True
        if resized.mode != "RGB":
            resized = resized.convert("RGB")
    elif save_format == "PNG":
        save_kwargs["optimize"] = True
        save_kwargs["compress_level"] = 1   # Fast, near-lossless
    elif save_format == "WEBP":
        save_kwargs["quality"] = jpeg_quality
        save_kwargs["method"] = 6           # Slowest / best encoder
        save_kwargs["lossless"] = False

    resized.save(buf, format=save_format, **save_kwargs)
    buf.seek(0)
    return buf.read(), save_format


def resize_file(input_path, output_path, **kwargs):
    """
    Convenience wrapper: resize *input_path* and write the result to
    *output_path*.  All keyword arguments are forwarded to :func:`resize_image`.
    """
    data, fmt = resize_image(input_path, **kwargs)
    with open(output_path, "wb") as f:
        f.write(data)
    print(f"Saved {fmt} image → {output_path}  ({len(data):,} bytes)")


# ── CLI (Pythonista 3 / terminal) ───────────────────────────────────────────
if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser(
        description="Resize an image with maximum quality (LANCZOS filter)."
    )
    parser.add_argument("input", help="Input image file path")
    parser.add_argument("output", help="Output image file path")

    size_group = parser.add_mutually_exclusive_group(required=True)
    size_group.add_argument("--scale", type=float, metavar="PCT",
                            help="Scale percentage  (e.g. 50 for 50%%)")
    size_group.add_argument("--width", type=int,
                            help="Target width in pixels")
    size_group.add_argument("--height", type=int,
                            help="Target height in pixels")

    parser.add_argument("--no-aspect", action="store_true",
                        help="Do NOT preserve aspect ratio")
    parser.add_argument("--quality", type=int, default=95, metavar="1-95",
                        help="JPEG/WebP quality (default: 95)")

    args = parser.parse_args()

    resize_file(
        args.input,
        args.output,
        scale_percent=args.scale,
        width=args.width,
        height=args.height,
        keep_aspect_ratio=not args.no_aspect,
        jpeg_quality=args.quality,
    )
