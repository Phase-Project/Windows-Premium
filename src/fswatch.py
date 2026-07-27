import os

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

_IGNORE_PARTS = {
    "appdata", ".git", "node_modules", "__pycache__", ".next", ".cache",
    "windowspremiumedition",
}


def _watched_dirs():
    home = os.path.expanduser("~")
    candidates = [
        os.path.join(home, "Desktop"),
        os.path.join(home, "OneDrive", "Desktop"),
        os.path.join(home, "Documents"),
    ]
    return [d for d in candidates if os.path.isdir(d)]


def _ignored(path):
    low = path.lower()
    return any(part in low.split(os.sep) for part in _IGNORE_PARTS)


class _Handler(FileSystemEventHandler):
    def __init__(self, wallet):
        self.wallet = wallet

    def on_created(self, event):
        if _ignored(event.src_path):
            return
        self.wallet.charge("create_dir" if event.is_directory
                           else "create_file")

    def on_deleted(self, event):
        if event.is_directory or _ignored(event.src_path):
            return
        self.wallet.charge("delete_file")


class FsWatcher:
    def __init__(self, wallet):
        self.observer = Observer()
        handler = _Handler(wallet)
        self._scheduled = False
        for d in _watched_dirs():
            try:
                self.observer.schedule(handler, d, recursive=True)
                self._scheduled = True
            except Exception:
                pass

    def start(self):
        if self._scheduled:
            self.observer.start()

    def stop(self):
        try:
            self.observer.stop()
            self.observer.join(timeout=2)
        except Exception:
            pass
