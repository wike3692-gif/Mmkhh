"""
Flask web application for high-quality image resizing.
Run with:  python web_app.py
Then open  http://localhost:5000  in your browser.
"""

import io
import os
import mimetypes

from flask import (
    Flask,
    render_template,
    request,
    send_file,
    jsonify,
    url_for,
)
from werkzeug.utils import secure_filename
from PIL import Image

from image_resizer import resize_image

app = Flask(__name__)

# ── Configuration ────────────────────────────────────────────────────────────
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB upload limit
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "bmp", "tiff", "tif", "gif"}

FORMAT_MIME = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
    "BMP": "image/bmp",
    "TIFF": "image/tiff",
    "GIF": "image/gif",
}

FORMAT_EXT = {
    "JPEG": "jpg",
    "PNG": "png",
    "WEBP": "webp",
    "BMP": "bmp",
    "TIFF": "tif",
    "GIF": "gif",
}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ── Routes ───────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/resize", methods=["POST"])
def resize():
    # ── Validate file ────────────────────────────────────────────────────────
    if "image" not in request.files:
        return jsonify(error="画像ファイルが選択されていません。"), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify(error="ファイルが選択されていません。"), 400

    if not allowed_file(file.filename):
        return jsonify(error="対応していないファイル形式です。"), 415

    # ── Parse resize parameters ──────────────────────────────────────────────
    mode = request.form.get("mode", "scale")  # scale | width | height | custom
    quality = int(request.form.get("quality", 95))
    keep_aspect = request.form.get("keep_aspect", "true").lower() == "true"
    out_format = request.form.get("format", "").upper() or None

    try:
        if mode == "scale":
            scale = float(request.form.get("scale", 50))
            kwargs = dict(scale_percent=scale, jpeg_quality=quality)
        elif mode == "width":
            w = int(request.form.get("width", 800))
            kwargs = dict(width=w, keep_aspect_ratio=keep_aspect, jpeg_quality=quality)
        elif mode == "height":
            h = int(request.form.get("height", 600))
            kwargs = dict(height=h, keep_aspect_ratio=keep_aspect, jpeg_quality=quality)
        elif mode == "custom":
            w = int(request.form.get("width", 800))
            h = int(request.form.get("height", 600))
            kwargs = dict(
                width=w, height=h,
                keep_aspect_ratio=keep_aspect,
                jpeg_quality=quality,
            )
        else:
            return jsonify(error="無効なモードです。"), 400
    except (ValueError, TypeError) as exc:
        return jsonify(error=f"パラメータが不正です: {exc}"), 400

    # ── Determine output format ──────────────────────────────────────────────
    original_ext = file.filename.rsplit(".", 1)[-1].lower()
    if original_ext in ("jpg", "jpeg"):
        detected_format = "JPEG"
    else:
        detected_format = original_ext.upper()

    output_format = out_format or detected_format
    if output_format == "JPG":
        output_format = "JPEG"

    kwargs["output_format"] = output_format

    # ── Resize ───────────────────────────────────────────────────────────────
    try:
        image_bytes = file.read()
        resized_bytes, fmt = resize_image(image_bytes, **kwargs)
    except Exception as exc:
        return jsonify(error=f"リサイズ中にエラーが発生しました: {exc}"), 500

    # ── Return resized image ─────────────────────────────────────────────────
    ext = FORMAT_EXT.get(fmt, "png")
    base_name = secure_filename(file.filename).rsplit(".", 1)[0]
    download_name = f"{base_name}_resized.{ext}"
    mime = FORMAT_MIME.get(fmt, "application/octet-stream")

    return send_file(
        io.BytesIO(resized_bytes),
        mimetype=mime,
        as_attachment=True,
        download_name=download_name,
    )


@app.route("/info", methods=["POST"])
def image_info():
    """Return original image dimensions before resizing."""
    if "image" not in request.files:
        return jsonify(error="No file"), 400
    file = request.files["image"]
    try:
        img = Image.open(file.stream)
        return jsonify(width=img.width, height=img.height, format=img.format or "Unknown")
    except Exception as exc:
        return jsonify(error=str(exc)), 400


# ── Entry point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
