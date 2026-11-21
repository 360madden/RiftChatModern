"""Privacy-redact only the two player-name labels in the public RCM screenshot.

Coordinates were inspected on the original 2560x1369 image:
- player frame: small name above the health bar
- telemetry panel: small name below its heading

No large panels or adjacent controls are blurred. Keep a local backup outside
the repository; Git history still retains the prior public screenshot.
"""
from pathlib import Path
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
SCREENSHOT = ROOT / "assets" / "screenshots" / "rcm-v0.2.2-physical-names-redacted.png"
BACKUP = ROOT / "artifacts" / "local-private-screenshot-backup.png"
BOXES = [
    (147, 29, 200, 51),    # player frame name only
    (13, 280, 73, 309),    # telemetry panel player name only
]


def main():
    image = Image.open(SCREENSHOT).convert("RGB")
    if image.size != (2560, 1369):
        raise RuntimeError(f"Unexpected screenshot dimensions: {image.size}")
    BACKUP.parent.mkdir(parents=True, exist_ok=True)
    if not BACKUP.exists():
        image.save(BACKUP, "PNG")
    for rect in BOXES:
        image.paste(image.crop(rect).filter(ImageFilter.GaussianBlur(radius=8)), rect)
    image.save(SCREENSHOT, "PNG", optimize=True)
    print(f"Redacted exactly {len(BOXES)} name regions; image {image.size}")
    print("Original backup is outside tracked Git assets:", BACKUP)
    print("Historical Git commits still contain the original screenshot.")


if __name__ == "__main__":
    main()
