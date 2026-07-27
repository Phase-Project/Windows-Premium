import json
import os
import queue
import threading

COSTS = {
    "left_click":   3,
    "right_click":  5,
    "middle_click": 4,
    "scroll":       1,
    "keystroke":    1,
    "create_dir":  20,
    "create_file": 10,
    "delete_file": 15,
    "open_app":    30,
}

LABELS = {
    "left_click":   "Left click",
    "right_click":  "Right click",
    "middle_click": "Middle click",
    "scroll":       "Scroll",
    "keystroke":    "Keystroke",
    "create_dir":   "New folder",
    "create_file":  "New file",
    "delete_file":  "Deletion",
    "open_app":     "App launch",
}

STARTING_CREDITS = 0


def dollars(credits):
    return f"${credits / 100:.2f}"

_APP_DIR = os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")),
    "WindowsPremiumEdition",
)
_WALLET_PATH = os.path.join(_APP_DIR, "wallet.json")


class Wallet:

    def __init__(self):
        self._lock = threading.Lock()
        self._balance = self._load()
        self.events = queue.Queue()

    def _load(self):
        try:
            with open(_WALLET_PATH, "r", encoding="utf-8") as f:
                return int(json.load(f)["balance"])
        except Exception:
            return STARTING_CREDITS

    def _save(self):
        try:
            os.makedirs(_APP_DIR, exist_ok=True)
            with open(_WALLET_PATH, "w", encoding="utf-8") as f:
                json.dump({"balance": self._balance}, f)
        except Exception:
            pass

    @property
    def balance(self):
        with self._lock:
            return self._balance

    def is_broke(self):
        with self._lock:
            return self._balance <= 0

    def charge(self, kind, pos=None):
        cost = COSTS.get(kind, 1)
        with self._lock:
            self._balance -= cost
            bal = self._balance
            self._save()
        self.events.put({
            "kind": kind,
            "cost": cost,
            "balance": bal,
            "label": LABELS.get(kind, kind),
            "pos": pos,
        })
        return bal

    def add(self, amount, label="Purchase"):
        with self._lock:
            self._balance += int(amount)
            bal = self._balance
            self._save()
        self.events.put({
            "kind": "purchase",
            "cost": -int(amount),
            "balance": bal,
            "label": label,
            "pos": None,
        })
        return bal

    def reset(self):
        with self._lock:
            self._balance = STARTING_CREDITS
            bal = self._balance
            self._save()
        return bal
