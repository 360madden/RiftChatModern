"""Generate a GitHub social-preview PNG from RCM's editable brand palette.

Optional maintainer tool; requires Pillow. This is a graphic asset generator,
not part of the RIFT addon or its runtime dependencies.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "rcm-social-preview.png"
W, H = 1280, 640


def font(size: int, bold: bool = False):
    name = "segoeuib.ttf" if bold else "segoeui.ttf"
    for candidate in (Path("C:/Windows/Fonts") / name,
                      Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf")):
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def main():
    img = Image.new("RGB", (W, H))
    pixels = img.load()
    for y in range(H):
        t = y / (H - 1)
        for x in range(W):
            s = x / (W - 1)
            pixels[x, y] = (
                int(9 + 2*t),
                int(19 + 20*s + 8*t),
                int(33 + 16*s + 6*t),
            )
    draw = ImageDraw.Draw(img)
    for x in range(0, W, 48):
        draw.line((x, 0, x, H), fill=(20, 47, 62), width=1)
    for y in range(0, H, 48):
        draw.line((0, y, W, y), fill=(20, 47, 62), width=1)
    draw.rounded_rectangle((74, 166, 332, 424), radius=54,
                           fill=(17, 40, 56), outline=(94, 234, 212), width=5)
    draw.rounded_rectangle((122, 229, 290, 343), radius=27,
                           outline=(94, 234, 212), width=12)
    draw.polygon(((155, 339), (155, 377), (203, 340)), fill=(94, 234, 212))
    draw.line((153, 271, 259, 271), fill=(231, 255, 250), width=11)
    draw.line((153, 303, 220, 303), fill=(231, 255, 250), width=11)
    draw.ellipse((244, 296, 257, 309), fill=(94, 234, 212))

    draw.text((380, 184), "RiftChatModern", font=font(80, True), fill=(235, 255, 251))
    draw.rounded_rectangle((383, 299, 471, 305), radius=3, fill=(94, 234, 212))
    draw.text((380, 341), "Modern chat-style console for RIFT Live",
              font=font(32), fill=(197, 213, 225))
    draw.text((382, 402), "CHAT UI   /   ADDON TOOLS   /   DIAGNOSTICS",
              font=font(23, True), fill=(125, 211, 252))
    draw.rounded_rectangle((380, 481, 593, 529), radius=20, fill=(20, 75, 76))
    draw.text((403, 490), "LUA 5.1  •  v0.2.22",
              font=font(19, True), fill=(165, 243, 230))
    draw.text((80, 582), "github.com/360madden/RiftChatModern",
              font=font(20), fill=(148, 163, 184))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, optimize=True)
    print(f"{OUT} {img.width}x{img.height} {OUT.stat().st_size} bytes")


if __name__ == "__main__":
    main()
