import ctypes
import os
import tkinter as tk
import tkinter.font as tkfont

from src import assets
from src.ui import px

user32 = ctypes.WinDLL("user32", use_last_error=True)

GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020
WS_EX_LAYERED = 0x00080000
WS_EX_TOOLWINDOW = 0x00000080
GA_ROOT = 2
LWA_COLORKEY = 0x00000001
LWA_ALPHA = 0x00000002

_TRANSPARENT_KEY = "#ff00ff"
_TRANSPARENT_REF = 0x00FF00FF

user32.GetAncestor.restype = ctypes.c_void_p
user32.GetAncestor.argtypes = (ctypes.c_void_p, ctypes.c_uint)
user32.SetLayeredWindowAttributes.argtypes = (
    ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ubyte, ctypes.c_ulong,
)
try:
    user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
    user32.SetWindowLongPtrW.restype = ctypes.c_ssize_t
    _get_long = user32.GetWindowLongPtrW
    _set_long = user32.SetWindowLongPtrW
except AttributeError:  # 32-bit Python
    user32.GetWindowLongW.restype = ctypes.c_long
    user32.SetWindowLongW.restype = ctypes.c_long
    _get_long = user32.GetWindowLongW
    _set_long = user32.SetWindowLongW


def _root_hwnd(widget):
    child = widget.winfo_id()
    root = user32.GetAncestor(ctypes.c_void_p(child), GA_ROOT)
    return root or child


GWLP_HWNDPARENT = -8


def detach_owner(widget, toolwindow=True):
    hwnd = _root_hwnd(widget)
    _set_long(hwnd, GWLP_HWNDPARENT, 0)
    if toolwindow:
        ex = _get_long(hwnd, GWL_EXSTYLE)
        _set_long(hwnd, GWL_EXSTYLE, ex | WS_EX_TOOLWINDOW)
    return hwnd


def _make_click_through(hwnd, alpha=255):
    ex = _get_long(hwnd, GWL_EXSTYLE)
    ex |= WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW
    _set_long(hwnd, GWL_EXSTYLE, ex)
    _set_long(hwnd, GWLP_HWNDPARENT, 0)
    user32.SetLayeredWindowAttributes(
        ctypes.c_void_p(hwnd), _TRANSPARENT_REF, alpha,
        LWA_COLORKEY | LWA_ALPHA,
    )


class FloatingPopup:

    LIFETIME_MS = 950
    RISE_PX = 34

    def __init__(self, root, text, color, x, y, icon=None):
        self.root = root
        self.win = tk.Toplevel(root)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        try:
            self.win.attributes("-transparentcolor", _TRANSPARENT_KEY)
        except tk.TclError:
            pass
        self.win.configure(bg=_TRANSPARENT_KEY)

        font = tkfont.Font(family="Segoe UI Semibold", size=12, weight="bold")
        pad = px(6)
        gap = px(5) if icon is not None else 0
        iw = icon.width() if icon is not None else 0
        ih = icon.height() if icon is not None else 0
        tw = font.measure(text)
        w = pad + iw + gap + tw + pad
        h = max(font.metrics("linespace"), ih) + pad * 2
        canvas = tk.Canvas(self.win, width=w, height=h,
                           bg=_TRANSPARENT_KEY, highlightthickness=0)
        canvas.pack()
        if icon is not None:
            self._icon = icon
            canvas.create_image(pad + iw // 2, h // 2, image=icon)
        tx = pad + iw + gap + tw // 2
        canvas.create_text(tx + px(1), h // 2 + px(2), text=text,
                           font=font, fill="#1a1a1a")
        canvas.create_text(tx, h // 2, text=text, font=font, fill=color)

        self.x = x
        self.y = y
        self.win.update_idletasks()
        self.win.geometry(f"+{x}+{y}")
        self.hwnd = None
        try:
            self.hwnd = _root_hwnd(self.win)
            _make_click_through(self.hwnd)
        except Exception:
            self.hwnd = None

        self._tick(0)

    def _set_alpha(self, alpha):
        if self.hwnd is not None:
            user32.SetLayeredWindowAttributes(
                ctypes.c_void_p(self.hwnd), _TRANSPARENT_REF,
                max(0, min(255, int(alpha * 255))),
                LWA_COLORKEY | LWA_ALPHA,
            )
        else:
            try:
                self.win.attributes("-alpha", alpha)
            except tk.TclError:
                pass

    def _tick(self, elapsed):
        if elapsed >= self.LIFETIME_MS:
            self._destroy()
            return
        frac = elapsed / self.LIFETIME_MS
        y = int(self.y - px(self.RISE_PX) * frac)
        try:
            self.win.geometry(f"+{self.x}+{y}")
        except tk.TclError:
            return
        self._set_alpha(max(0.0, 1.0 - frac * frac))
        self.root.after(16, lambda: self._tick(elapsed + 16))

    def _destroy(self):
        try:
            self.win.destroy()
        except tk.TclError:
            pass


class OverlayManager:

    def __init__(self, root):
        self.root = root
        self._alive = 0
        self.MAX_ALIVE = 12

    def spawn(self, text, color, x, y, kind=None):
        if self._alive >= self.MAX_ALIVE:
            return
        self._alive += 1
        icon = None
        if kind is not None:
            icon = assets.load_icon(os.path.join("icons", f"{kind}.png"),
                                    px(20))
        FloatingPopup(self.root, text, color, x + px(14), y - px(8),
                      icon=icon)
        self.root.after(FloatingPopup.LIFETIME_MS + 50, self._release)

    def _release(self):
        self._alive = max(0, self._alive - 1)
