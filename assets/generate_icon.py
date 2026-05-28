"""Generate assets/icon.png and assets/icon.ico.

Run once before building:
    python assets/generate_icon.py
"""

from pathlib import Path
from PIL import Image, ImageDraw

SIZES = [16, 32, 48, 64, 128, 256]
OUT_DIR = Path(__file__).parent


def draw_envelope(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d   = ImageDraw.Draw(img)

    m      = max(2, size // 8)
    top    = size // 3
    bottom = size - m
    left   = m
    right  = size - m
    mid    = size // 2
    fold_y = top + (bottom - top) // 2

    # envelope body
    d.rectangle([left, top, right, bottom], fill=(31, 57, 125))

    # white flap
    d.polygon([(left, top), (right, top), (mid, fold_y)],
              fill=(255, 255, 255, 200))

    # outline
    lw = max(1, size // 32)
    d.rectangle([left, top, right, bottom], outline=(180, 200, 255), width=lw)

    # crease lines
    d.line([(left,  bottom), (mid - size // 10, fold_y)], fill=(180, 200, 255, 150), width=lw)
    d.line([(right, bottom), (mid + size // 10, fold_y)], fill=(180, 200, 255, 150), width=lw)

    return img


def main():
    frames = [draw_envelope(s) for s in SIZES]

    # PNG (largest size)
    png_path = OUT_DIR / "icon.png"
    frames[-1].save(png_path)
    print(f"Saved {png_path}")

    # ICO (all sizes embedded — Windows)
    ico_path = OUT_DIR / "icon.ico"
    frames[-1].save(
        ico_path,
        format="ICO",
        sizes=[(s, s) for s in SIZES],
        append_images=frames[:-1],
    )
    print(f"Saved {ico_path}")


if __name__ == "__main__":
    main()
