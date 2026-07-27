import ctypes
import threading
import time
from ctypes import wintypes

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
user32 = ctypes.WinDLL("user32", use_last_error=True)

TH32CS_SNAPPROCESS = 0x00000002
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

POLL_S = 1.5
WINDOW_GRACE_S = 12
EXE_COOLDOWN_S = 30

DENY = {
    "svchost.exe", "conhost.exe", "runtimebroker.exe", "dllhost.exe",
    "backgroundtaskhost.exe", "searchhost.exe", "taskhostw.exe",
    "sihost.exe", "ctfmon.exe", "explorer.exe", "wmiprvse.exe",
    "audiodg.exe", "csrss.exe", "smss.exe", "fontdrvhost.exe",
    "textinputhost.exe", "searchindexer.exe", "werfault.exe",
    "openconsole.exe", "crashpad_handler.exe", "msedgewebview2.exe",
    "wininit.exe", "winlogon.exe", "services.exe", "lsass.exe",
    "spoolsv.exe", "securityhealthservice.exe", "shellexperiencehost.exe",
    "startmenuexperiencehost.exe", "lockapp.exe", "useroobebroker.exe",
    "dwm.exe", "py.exe", "python.exe", "pythonw.exe",
}


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", wintypes.LONG),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", wintypes.WCHAR * 260),
    ]


kernel32.CreateToolhelp32Snapshot.restype = ctypes.c_void_p
kernel32.CreateToolhelp32Snapshot.argtypes = (wintypes.DWORD, wintypes.DWORD)
kernel32.Process32FirstW.argtypes = (ctypes.c_void_p,
                                     ctypes.POINTER(PROCESSENTRY32W))
kernel32.Process32NextW.argtypes = (ctypes.c_void_p,
                                    ctypes.POINTER(PROCESSENTRY32W))
kernel32.CloseHandle.argtypes = (ctypes.c_void_p,)

WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, ctypes.c_void_p,
                                 wintypes.LPARAM)
user32.EnumWindows.argtypes = (WNDENUMPROC, wintypes.LPARAM)
user32.IsWindowVisible.argtypes = (ctypes.c_void_p,)
user32.GetWindowThreadProcessId.argtypes = (ctypes.c_void_p,
                                            ctypes.POINTER(wintypes.DWORD))


def _snapshot_processes():
    out = {}
    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if not snap or snap == INVALID_HANDLE_VALUE:
        return out
    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        ok = kernel32.Process32FirstW(snap, ctypes.byref(entry))
        while ok:
            out[int(entry.th32ProcessID)] = entry.szExeFile.lower()
            ok = kernel32.Process32NextW(snap, ctypes.byref(entry))
    finally:
        kernel32.CloseHandle(snap)
    return out


def _pids_with_visible_window():
    pids = set()

    def cb(hwnd, _):
        if user32.IsWindowVisible(hwnd):
            pid = wintypes.DWORD(0)
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            pids.add(int(pid.value))
        return True

    user32.EnumWindows(WNDENUMPROC(cb), 0)
    return pids


class ProcWatcher(threading.Thread):

    def __init__(self, wallet):
        super().__init__(daemon=True)
        self.wallet = wallet
        self._stop = threading.Event()
        self._our_pid = kernel32.GetCurrentProcessId()

    def run(self):
        known = set(_snapshot_processes())
        pending = {}
        charged = {}
        while not self._stop.wait(POLL_S):
            now = time.monotonic()
            procs = _snapshot_processes()
            for pid, exe in procs.items():
                if pid in known or pid in pending:
                    continue
                if pid == self._our_pid or exe in DENY:
                    continue
                pending[pid] = (exe, now + WINDOW_GRACE_S)
            known = set(procs)

            if pending:
                visible = _pids_with_visible_window()
                for pid in list(pending):
                    exe, deadline = pending[pid]
                    if pid in visible:
                        del pending[pid]
                        if now - charged.get(exe, -1e9) >= EXE_COOLDOWN_S:
                            charged[exe] = now
                            self.wallet.charge("open_app")
                    elif now > deadline or pid not in procs:
                        del pending[pid]

    def stop(self):
        self._stop.set()
