import os
import sys
import qrcode
from PIL import Image, ImageDraw, ImageFont

# ── Path setup ────────────────────────────────────────────────────────────────
if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

QR_DIR = os.path.join(APP_DIR, 'qr_codes')
os.makedirs(QR_DIR, exist_ok=True)


def generate_qr_code(student_id, name):
    """Generate and save a QR code image for a student."""

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )

    qr.add_data(student_id)
    qr.make(fit=True)

    qr_image = qr.make_image(
        fill_color="black",
        back_color="white"
    ).convert("RGB")

    # Add student name label below QR code
    width, height = qr_image.size
    new_height = height + 40
    labeled = Image.new("RGB", (width, new_height), "white")
    labeled.paste(qr_image, (0, 0))

    draw = ImageDraw.Draw(labeled)
    draw.text(
        (width // 2, height + 10),
        f"{student_id} - {name}",
        fill="black",
        anchor="mt"
    )

    # Save the image
    filename = os.path.join(QR_DIR, f"{student_id}.png")
    labeled.save(filename)

    print(f"✅ QR Code saved: {filename}")
    return filename