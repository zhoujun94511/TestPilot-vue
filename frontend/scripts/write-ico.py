"""Write RGBA PNG frames to ICO (Pillow). Usage: python write-ico.py OUT.ico 16.png 32.png ..."""
import sys
from pathlib import Path

from PIL import Image


def main() -> None:
    if len(sys.argv) < 3:
        print("usage: write-ico.py OUT.ico frame.png ...", file=sys.stderr)
        sys.exit(1)
    out = Path(sys.argv[1])
    paths = [Path(p) for p in sys.argv[2:]]
    imgs = [Image.open(p).convert("RGBA") for p in paths]
    sizes = [(im.width, im.height) for im in imgs]
    pairs = sorted(zip(sizes, imgs), key=lambda x: x[0][0], reverse=True)
    imgs_sorted = [im for _, im in pairs]
    sizes_sorted = [sz for sz, _ in pairs]
    out.parent.mkdir(parents=True, exist_ok=True)
    imgs_sorted[0].save(out, format="ICO", sizes=sizes_sorted)


if __name__ == "__main__":
    main()
