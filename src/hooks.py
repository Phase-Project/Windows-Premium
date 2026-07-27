import ctypes
import threading
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

WH_MOUSE_LL = 14
WH_KEYBOARD_LL = 13
WM_LBUTTONDOWN = 0x0201
WM_RBUTTONDOWN = 0x0204
WM_MBUTTONDOWN = 0x0207
WM_MOUSEWHEEL = 0x020A
WM_KEYDOWN = 0x0100
WM_SYSKEYDOWN = 0x0104
WM_QUIT = 0x0012
VK_P = 0x50
VK_CONTROL = 0x11
VK_MENU = 0x12
VK_SHIFT = 0x10

GA_ROOT = 2

ULONG_PTR = wintypes.WPARAM


class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("pt", POINT),
        ("mouseData", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


HOOKPROC = ctypes.CFUNCTYPE(
    ctypes.c_ssize_t, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM
)

user32.SetWindowsHookExW.restype = ctypes.c_void_p
user32.SetWindowsHookExW.argtypes = (
    ctypes.c_int, HOOKPROC, ctypes.c_void_p, wintypes.DWORD,
)
user32.CallNextHookEx.restype = ctypes.c_ssize_t
user32.CallNextHookEx.argtypes = (
    ctypes.c_void_p, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM,
)
user32.UnhookWindowsHookEx.argtypes = (ctypes.c_void_p,)
user32.WindowFromPoint.restype = ctypes.c_void_p
user32.WindowFromPoint.argtypes = (POINT,)
user32.GetAncestor.restype = ctypes.c_void_p
user32.GetAncestor.argtypes = (ctypes.c_void_p, wintypes.UINT)
kernel32.GetModuleHandleW.restype = ctypes.c_void_p
kernel32.GetModuleHandleW.argtypes = (wintypes.LPCWSTR,)


def _modifiers_down():
    hi = 0x8000
    return (
        user32.GetKeyState(VK_CONTROL) & hi
        and user32.GetKeyState(VK_MENU) & hi
        and user32.GetKeyState(VK_SHIFT) & hi
    )


class HookThread(threading.Thread):

    def __init__(self, wallet, is_app_window_at, on_panic):
        super().__init__(daemon=True)
        self.wallet = wallet
        self.is_app_window_at = is_app_window_at
        self.on_panic = on_panic
        self.blocking = True
        self._thread_id = None
        self._mouse_hook = None
        self._kbd_hook = None
        self._mouse_proc = HOOKPROC(self._mouse_cb)
        self._kbd_proc = HOOKPROC(self._kbd_cb)

    # --- callbacks ---
    def _mouse_cb(self, nCode, wParam, lParam):
        if nCode == 0:
            info = ctypes.cast(lParam, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
            pos = (info.pt.x, info.pt.y)
            kind = None
            blockable = False
            if wParam == WM_LBUTTONDOWN:
                kind, blockable = "left_click", True
            elif wParam == WM_RBUTTONDOWN:
                kind, blockable = "right_click", True
            elif wParam == WM_MBUTTONDOWN:
                kind, blockable = "middle_click", True
            elif wParam == WM_MOUSEWHEEL:
                kind = "scroll"

            if kind is not None:
                broke = self.wallet.is_broke()
                over_app = self.is_app_window_at(pos[0], pos[1])
                if self.blocking and broke and blockable and not over_app:
                    self.wallet.charge(kind, pos)
                    return 1
                self.wallet.charge(kind, pos)
        return user32.CallNextHookEx(None, nCode, wParam, lParam)

    def _kbd_cb(self, nCode, wParam, lParam):
        if nCode == 0 and wParam in (WM_KEYDOWN, WM_SYSKEYDOWN):
            info = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
            if info.vkCode == VK_P and _modifiers_down():
                try:
                    self.on_panic()
                finally:
                    return user32.CallNextHookEx(None, nCode, wParam, lParam)
            self.wallet.charge("keystroke", None)
        return user32.CallNextHookEx(None, nCode, wParam, lParam)

    def run(self):
        self._thread_id = kernel32.GetCurrentThreadId()
        hmod = kernel32.GetModuleHandleW(None)
        self._mouse_hook = user32.SetWindowsHookExW(
            WH_MOUSE_LL, self._mouse_proc, hmod, 0
        )
        self._kbd_hook = user32.SetWindowsHookExW(
            WH_KEYBOARD_LL, self._kbd_proc, hmod, 0
        )
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
        self._unhook()

    def _unhook(self):
        if self._mouse_hook:
            user32.UnhookWindowsHookEx(self._mouse_hook)
            self._mouse_hook = None
        if self._kbd_hook:
            user32.UnhookWindowsHookEx(self._kbd_hook)
            self._kbd_hook = None

    def stop(self):
        if self._thread_id:
            user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)


def window_root_at(x, y):
    hwnd = user32.WindowFromPoint(POINT(x, y))
    if not hwnd:
        return None
    root = user32.GetAncestor(hwnd, GA_ROOT)
    return root or hwnd
