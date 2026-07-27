import atexit
import ctypes
import os
import threading
import tkinter as tk

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

import src.assets as assets
import src.ui as ui
from src.hooks import HookThread, window_root_at
from src.overlay import OverlayManager, detach_owner
from src.shop import Shop, BLUE, BLUE_DARK, INK, SOFT
from src.state import Wallet, dollars

try:
    from src.fswatch import FsWatcher
except Exception:
    FsWatcher = None

try:
    from src.procwatch import ProcWatcher
except Exception:
    ProcWatcher = None

TEST_MODE = os.environ.get("WPE_TEST") == "1"

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
_OUR_PID = kernel32.GetCurrentProcessId()


def _cursor_pos():
    class _P(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
    p = _P()
    user32.GetCursorPos(ctypes.byref(p))
    return p.x, p.y


def _work_area():
    class _R(ctypes.Structure):
        _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                    ("right", ctypes.c_long), ("bottom", ctypes.c_long)]
    r = _R()
    SPI_GETWORKAREA = 0x0030
    if user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(r), 0):
        return r.left, r.top, r.right, r.bottom
    return (0, 0, user32.GetSystemMetrics(0), user32.GetSystemMetrics(1))


def _is_app_window_at(x, y):
    hwnd = window_root_at(x, y)
    if not hwnd:
        return False
    pid = ctypes.c_ulong(0)
    user32.GetWindowThreadProcessId(ctypes.c_void_p(hwnd), ctypes.byref(pid))
    return pid.value == _OUR_PID


class App:
    def __init__(self):
        self.wallet = Wallet()
        self.panic_event = threading.Event()
        self.root = tk.Tk()
        self.root.title("Windows Premium Edition")
        ui.init(self.root)
        w, h = ui.px(440), ui.px(500)
        x = self.root.winfo_screenwidth() - w - ui.px(16)
        y = self.root.winfo_screenheight() - h - ui.px(88)
        self.root.geometry(f"{w}x{h}+{max(0, x)}+{max(0, y)}")
        self.root.configure(bg="white")
        self.root.attributes("-topmost", True)
        self.root.protocol("WM_DELETE_WINDOW", self.shutdown)
        self.overlay = OverlayManager(self.root)
        self.shop = Shop(self.root, self.wallet, on_quit=self.shutdown)
        self._build_hud()
        self._build_mini()
        self.hooks = HookThread(self.wallet, _is_app_window_at, self._on_panic)
        self.hooks.blocking = not TEST_MODE
        self.hooks.start()

        self.watcher = None
        if FsWatcher is not None and not TEST_MODE:
            try:
                self.watcher = FsWatcher(self.wallet)
                self.watcher.start()
            except Exception:
                self.watcher = None

        self.procwatcher = None
        if ProcWatcher is not None and not TEST_MODE:
            try:
                self.procwatcher = ProcWatcher(self.wallet)
                self.procwatcher.start()
            except Exception:
                self.procwatcher = None

        atexit.register(self._cleanup)
        if TEST_MODE:
            self._start_test_driver()
        self.root.after(300, self.shop.open)
        self._poll()

    # --- HUD ---
    def _build_hud(self):
        pad = ui.px(16)
        head = tk.Frame(self.root, bg=BLUE)
        head.pack(fill="x")
        tk.Label(head, text="Windows Premium Edition", bg=BLUE, fg="white",
                 font=("Segoe UI Semibold", 14, "bold")).pack(anchor="w",
                 padx=pad, pady=(ui.px(12), 0))
        tk.Label(head, text="Every gesture counts. Literally.",
                 bg=BLUE, fg="#d9e8f7",
                 font=("Segoe UI", 9)).pack(anchor="w", padx=pad,
                                            pady=(0, ui.px(12)))

        mid = tk.Frame(self.root, bg="white")
        mid.pack(fill="x", pady=(ui.px(14), 0))
        tk.Label(mid, text="Credit balance", bg="white", fg=SOFT,
                 font=("Segoe UI", 9)).pack()
        balance_row = tk.Frame(mid, bg="white")
        balance_row.pack()
        coin = assets.load("coin.png", ui.px(36), ui.px(36))
        if coin is not None:
            tk.Label(balance_row, image=coin,
                     bg="white").pack(side="left", padx=(0, ui.px(8)))
        self.balance_var = tk.StringVar(value=str(self.wallet.balance))
        self.balance_lbl = tk.Label(balance_row, textvariable=self.balance_var,
                                    bg="white", fg=BLUE_DARK,
                                    font=("Segoe UI Semibold", 40, "bold"))
        self.balance_lbl.pack(side="left")
        self.euros_var = tk.StringVar(value=f"\u2248 {dollars(self.wallet.balance)}")
        tk.Label(mid, textvariable=self.euros_var, bg="white", fg=SOFT,
                 font=("Segoe UI", 10)).pack()

        self.gauge = tk.Canvas(self.root, height=ui.px(10), bg="#eef2f8",
                               highlightthickness=0)
        self.gauge.pack(fill="x", padx=pad, pady=(ui.px(4), ui.px(2)))

        self.banner = tk.Label(self.root, text="", bg="white", fg="#e23b3b",
                               font=("Segoe UI Semibold", 10, "bold"))
        self.banner.pack(pady=ui.px(2))

        tk.Button(self.root, text="  Reload credits  ", relief="flat",
                  bg=BLUE, fg="white", activebackground=BLUE_DARK,
                  activeforeground="white", cursor="hand2",
                  font=("Segoe UI Semibold", 11, "bold"),
                  command=self.shop.open).pack(pady=ui.px(8))

        tk.Label(self.root, text="Recent charges", bg="white", fg=SOFT,
                 font=("Segoe UI", 9)).pack(anchor="w", padx=pad)
        self.log = tk.Listbox(self.root, height=6, bd=0,
                              highlightthickness=1,
                              highlightbackground="#e2e8f0",
                              font=("Consolas", 9), fg=INK,
                              activestyle="none")
        self.log.pack(fill="both", expand=True, padx=pad,
                      pady=(ui.px(2), ui.px(6)))

        tk.Label(self.root,
                 text="Panic: Ctrl+Alt+Shift+P  ·  No real payment.",
                 bg="white", fg="#9aa1ab",
                 font=("Segoe UI", 8)).pack(pady=(0, ui.px(8)))

    def _build_mini(self):
        self.mini = tk.Toplevel(self.root)
        self.mini.overrideredirect(True)
        self.mini.attributes("-topmost", True)
        self.mini.withdraw()
        self.mini.configure(bg="#d5dbe4")
        self.mini_var = tk.StringVar()
        self.mini_lbl = tk.Label(self.mini, textvariable=self.mini_var,
                                 bg="white", fg=SOFT, font=("Segoe UI", 8),
                                 padx=ui.px(6), pady=ui.px(2), cursor="hand2")
        self.mini_lbl.pack(padx=1, pady=1)
        self.mini_lbl.bind("<Button-1>", lambda e: self.root.deiconify())
        self.mini.update_idletasks()
        try:
            detach_owner(self.mini)
        except Exception:
            pass
        self._mini_text = None

    def _update_mini(self, balance):
        try:
            minimized = self.root.state() == "iconic"
        except tk.TclError:
            return
        if not minimized:
            if self.mini.winfo_viewable():
                self.mini.withdraw()
            return
        text = f"Credits remaining: {balance}"
        if text != self._mini_text:
            self._mini_text = text
            self.mini_var.set(text)
            self.mini_lbl.config(fg="#e23b3b" if balance <= 0 else SOFT)
            self.mini.update_idletasks()
            left, top, right, bottom = _work_area()
            x = right - self.mini.winfo_reqwidth() - ui.px(8)
            y = bottom - self.mini.winfo_reqheight() - ui.px(8)
            self.mini.geometry(f"+{x}+{y}")
        if not self.mini.winfo_viewable():
            self.mini.deiconify()
            self.mini.attributes("-topmost", True)

    def _update_gauge(self, balance):
        self.gauge.delete("all")
        w = self.gauge.winfo_width() or ui.px(408)
        frac = max(0.0, min(1.0, balance / 200.0))
        color = "#2fae66" if balance > 60 else ("#e0a800" if balance > 0
                                                else "#e23b3b")
        self.gauge.create_rectangle(0, 0, int(w * frac), ui.px(10),
                                    fill=color, width=0)

    def _poll(self):
        if self.panic_event.is_set():
            self.shutdown()
            return
        drained = 0
        while drained < 40:
            try:
                ev = self.wallet.events.get_nowait()
            except Exception:
                break
            drained += 1
            self._handle_event(ev)

        bal = self.wallet.balance
        self.balance_var.set(str(bal))
        self.euros_var.set(f"\u2248 {dollars(bal)}")
        self._update_gauge(bal)
        self._update_mini(bal)
        if bal <= 0:
            self.banner.config(
                text="LICENSE EXPIRED: your clicks are suspended")
            self.balance_lbl.config(fg="#e23b3b")
            if not self.shop.is_open():
                self.shop.open()
        else:
            self.banner.config(text="")
            self.balance_lbl.config(fg=BLUE_DARK)
        self.root.after(30, self._poll)

    def _handle_event(self, ev):
        pos = ev["pos"] or _cursor_pos()
        if ev["kind"] == "purchase":
            self.overlay.spawn(f"+{-ev['cost']} credits", "#2fae66",
                               *_cursor_pos(), kind="purchase")
            self._log(f"+{-ev['cost']:>5}  {ev['label']}")
        else:
            self.overlay.spawn(f"-{ev['cost']} · {ev['label']}", "#e23b3b",
                               *pos, kind=ev["kind"])
            self._log(f"-{ev['cost']:>5}  {ev['label']}")

    def _log(self, line):
        self.log.insert(0, line)
        if self.log.size() > 40:
            self.log.delete(40, tk.END)

    def _on_panic(self):
        self.panic_event.set()

    def _cleanup(self):
        try:
            self.hooks.stop()
        except Exception:
            pass
        if self.watcher is not None:
            try:
                self.watcher.stop()
            except Exception:
                pass
        if self.procwatcher is not None:
            try:
                self.procwatcher.stop()
            except Exception:
                pass

    def shutdown(self):
        self._cleanup()
        try:
            self.root.destroy()
        except Exception:
            pass

    def _start_test_driver(self):
        self._t = 0
        kinds = ["left_click", "right_click", "scroll", "keystroke",
                 "create_dir", "delete_file", "create_file"]

        def tick():
            self._t += 1
            k = kinds[self._t % len(kinds)]
            x, y = _cursor_pos()
            self.wallet.charge(k, (x, y))
            if self._t % 15 == 0:
                self.wallet.add(500, "Test Pack")
            self.root.after(300, tick)

        self.root.after(500, tick)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    App().run()
