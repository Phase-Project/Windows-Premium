SCALE = 1.0


def init(widget):
    global SCALE
    try:
        SCALE = max(1.0, widget.winfo_fpixels("1i") / 96.0)
    except Exception:
        SCALE = 1.0


def px(n):
    return int(round(n * SCALE))
