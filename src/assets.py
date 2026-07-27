import os
import tkinter as tk

try:
    from PIL import Image, ImageTk
except Exception:
    Image = None
    ImageTk = None

ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "assets")

_cache = {}


def _cover(im, w, h):
    sw, sh = im.size
    scale = max(w / sw, h / sh)
    nw, nh = max(1, round(sw * scale)), max(1, round(sh * scale))
    im = im.resize((nw, nh), Image.LANCZOS)
    x = (nw - w) // 2
    y = (nh - h) // 2
    return im.crop((x, y, x + w, y + h))


def load(name, width=None, height=None):
    path = os.path.join(ASSETS_DIR, name)
    if not os.path.isfile(path):
        return None
    key = (name, width, height)
    if key in _cache:
        return _cache[key]

    img = None
    if Image is not None and ImageTk is not None:
        try:
            im = Image.open(path).convert("RGBA")
            if width and height:
                im = _cover(im, int(width), int(height))
            img = ImageTk.PhotoImage(im)
        except Exception:
            img = None
    if img is None:
        try:
            img = tk.PhotoImage(file=path)
            if width and img.width() > width:
                img = img.subsample(max(1, round(img.width() / width)))
        except Exception:
            return None

    _cache[key] = img
    return img


def load_icon(name, size, matte="#ff00ff"):
    if Image is None or ImageTk is None:
        return None
    path = os.path.join(ASSETS_DIR, name)
    if not os.path.isfile(path):
        return None
    key = (name, size, matte)
    if key in _cache:
        return _cache[key]
    try:
        im = Image.open(path).convert("RGBA")
        im = im.resize((int(size), int(size)), Image.LANCZOS)
        mr = tuple(int(matte[i:i + 2], 16) for i in (1, 3, 5))
        im.putdata([
            mr + (255,) if p[3] < 128 else (p[0], p[1], p[2], 255)
            for p in im.getdata()
        ])
        img = ImageTk.PhotoImage(im)
    except Exception:
        return None
    _cache[key] = img
    return img
