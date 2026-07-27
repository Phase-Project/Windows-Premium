import random
import tkinter as tk
from src import assets
from src import ui
from src.state import dollars
from src.ui import px

BLUE = "#0067c0"
BLUE_DARK = "#004b8d"
INK = "#1b1b1b"
SOFT = "#5c5c5c"
PANEL = "#f3f6fb"
GOLD = "#c99700"
STRIPE = "#635bff"
STRIPE_DARK = "#4f46e5"
RED = "#e23b3b"

PACKS = [
    {"name": "Trial Pack", "credits": 100, "price": "$1.99",
     "tag": "", "note": "Just enough to open Notepad."},
    {"name": "Starter Pack", "credits": 500, "price": "$4.99",
     "tag": "", "note": "Enough to click for a little while."},
    {"name": "Comfort Pack", "credits": 2000, "price": "$9.99",
     "tag": "POPULAR", "note": "The favorite of Premium users."},
    {"name": "Pro Pack", "credits": 10000, "price": "$29.99",
     "tag": "-70%", "note": "Unlimited productivity*. (*not unlimited)"},
    {"name": "Business Pack", "credits": 50000, "price": "$79.99",
     "tag": "BEST VALUE", "note": "For enterprises that really need Ctrl+C."},
    {"name": "Enterprise Pack", "credits": 200000, "price": "$199.99",
     "tag": "WOW", "note": "Covers your entire team of 1."},
    {"name": "Pay Your Debt", "debt": True, "credits": 0, "price": "$0.00",
     "tag": "REDEMPTION", "note": "Clear your balance. 1 credit = $0.01."},
]

CHECKOUT_STEPS = [
    (0, "Secure connection to Stripe..."),
    (5, "Verifying 3-D Secure..."),
    (10, "Charging card •••• 0819..."),
    (15, "Issuing your click license..."),
]

_SB_WIDTH = 18


class Shop:

    def __init__(self, root, wallet, on_quit=None):
        self.root = root
        self.wallet = wallet
        self.on_quit = on_quit or (lambda: None)
        self.win = None
        self._selected = 2
        self._cards = []
        self._busy = False
        self._scroll_canvas = None

    def is_open(self):
        return self.win is not None and bool(self.win.winfo_exists())

    def open(self):
        try:
            self.root.withdraw()
        except tk.TclError:
            pass
        if self.is_open():
            self.win.deiconify()
            self.win.lift()
            self.win.focus_force()
            return
        self._busy = False
        self._build()

    def close(self):
        if self.win is not None:
            try:
                self.win.destroy()
            except tk.TclError:
                pass
            self.win = None
        try:
            self.root.deiconify()
            self.root.lift()
        except tk.TclError:
            pass

    def _close_if_allowed(self):
        if not self._busy and self.wallet.balance > 0:
            self.close()

    def _build(self):
        self.win = tk.Toplevel(self.root)
        self.win.title("Activate Windows Premium Edition")
        self.win.attributes("-fullscreen", True)
        self.win.attributes("-topmost", True)
        self.win.configure(bg="#0b1220")
        self.win.protocol("WM_DELETE_WINDOW", self._close_if_allowed)
        self.win.bind("<Escape>", lambda e: self._close_if_allowed())

        sw = self.win.winfo_screenwidth()
        sh = self.win.winfo_screenheight()
        max_h = int(sh * 0.92)
        card_w = px(640)

        self.bg_canvas = tk.Canvas(self.win, width=sw, height=sh,
                                   highlightthickness=0, bg="#0b1220")
        self.bg_canvas.pack(fill="both", expand=True)
        bg = assets.load("paywall_bg.jpg", sw, sh)
        if bg is not None:
            self.bg_canvas.create_image(0, 0, image=bg, anchor="nw")
        else:
            for i in range(0, sh, 4):
                t = i / max(1, sh)
                r = int(11 + 20 * t)
                g = int(18 + 35 * t)
                b = int(32 + 80 * t)
                self.bg_canvas.create_rectangle(
                    0, i, sw, i + 4, fill=f"#{r:02x}{g:02x}{b:02x}", width=0)

        card_outer = tk.Frame(self.win, bg="white")
        card_outer.place(relx=0.5, rely=0.5, anchor="center",
                         width=card_w, height=max_h)

        self._scroll_canvas = tk.Canvas(card_outer, bg="white",
                                        highlightthickness=0, bd=0)
        scroll_bar = tk.Scrollbar(card_outer, orient="vertical",
                                  command=self._scroll_canvas.yview)
        self._scroll_canvas.configure(yscrollcommand=scroll_bar.set)

        scroll_bar.place(relx=1.0, rely=0, relheight=1.0, anchor="ne")
        self._scroll_canvas.place(relx=0, rely=0, relheight=1.0,
                                  width=card_w - _SB_WIDTH)

        card = tk.Frame(self._scroll_canvas, bg="white")
        self._card_win = self._scroll_canvas.create_window(
            (0, 0), window=card, anchor="nw")
        self.card = card

        head = tk.Frame(card, bg=BLUE_DARK)
        head.pack(fill="x")
        head_in = tk.Frame(head, bg=BLUE_DARK)
        head_in.pack(anchor="w", padx=px(20), pady=px(12))
        coin = assets.load("coin.png", px(40), px(40))
        if coin is not None:
            tk.Label(head_in, image=coin,
                     bg=BLUE_DARK).pack(side="left", padx=(0, px(10)))
        head_txt = tk.Frame(head_in, bg=BLUE_DARK)
        head_txt.pack(side="left")
        tk.Label(head_txt, text="Windows Premium Edition",
                 bg=BLUE_DARK, fg="white",
                 font=("Segoe UI Semibold", 16, "bold")).pack(anchor="w")
        tk.Label(head_txt, text="Pay2Win Edition: your PC is pay-per-use.",
                 bg=BLUE_DARK, fg="#d9e8f7",
                 font=("Segoe UI", 9)).pack(anchor="w")

        self.balance_lbl = tk.Label(card, text="", bg="white",
                                    font=("Segoe UI Semibold", 11, "bold"))
        self.balance_lbl.pack(pady=(px(10), 0))
        self.banner_lbl = tk.Label(card, text="", bg="white", fg=RED,
                                   font=("Segoe UI Semibold", 10, "bold"))
        self.banner_lbl.pack()

        promo = tk.Frame(card, bg="#fff6d6")
        promo.pack(fill="x", pady=(px(6), 0))
        tk.Label(promo,
                 text="Made By Phase Project",
                 bg="#fff6d6", fg=GOLD,
                 font=("Segoe UI Semibold", 9, "bold")).pack(pady=px(4))

        body = tk.Frame(card, bg="white")
        body.pack(fill="x", padx=px(18), pady=(px(6), 0))
        self._cards = []
        for i, pack in enumerate(PACKS):
            self._pack_card(body, pack, i)
        self._highlight()

        pay = tk.Frame(card, bg="white")
        pay.pack(fill="x", padx=px(18), pady=(px(8), 0))

        self.status = tk.Label(pay, text="", bg="white", fg=SOFT,
                               font=("Segoe UI", 9))
        self.status.pack()
        self.progress = tk.Canvas(pay, height=px(6), bg="#eef2f8",
                                  highlightthickness=0)
        self.progress.pack(fill="x", pady=(px(2), px(6)))

        self.pay_btn = tk.Button(
            pay, text="", relief="flat", bd=0, cursor="hand2",
            bg=STRIPE, fg="white", activebackground=STRIPE_DARK,
            activeforeground="white",
            font=("Segoe UI Semibold", 12, "bold"), pady=px(8),
            command=self._buy,
        )
        self.pay_btn.pack(fill="x")
        tk.Label(pay, text="",
                 bg="white", fg="#9aa1ab",
                 font=("Segoe UI", 8)).pack(pady=(px(3), 0))

        foot = tk.Frame(card, bg="white")
        foot.pack(fill="x", padx=px(18), pady=(px(6), px(12)))
        self.return_btn = tk.Button(
            foot, text="Return to your PC  →", relief="flat",
            bg="#eef2f8", fg=BLUE_DARK, activebackground="#dde7f3",
            activeforeground=BLUE_DARK, cursor="hand2",
            font=("Segoe UI Semibold", 10, "bold"), padx=px(12), pady=px(5),
            command=self._close_if_allowed,
        )
        quit_lbl = tk.Label(foot, text="Quit demo (panic)",
                            bg="white", fg="#9aa1ab", cursor="hand2",
                            font=("Segoe UI", 8, "underline"))
        quit_lbl.pack(side="right")
        quit_lbl.bind("<Button-1>", lambda e: self.on_quit())

        self._scroll_canvas.update_idletasks()

        cw = self._scroll_canvas.winfo_width()
        if cw > 1:
            self._scroll_canvas.itemconfig(self._card_win, width=cw)

        bbox = self._scroll_canvas.bbox("all")
        if bbox:
            self._scroll_canvas.configure(scrollregion=bbox)

        self._scroll_canvas.bind(
            "<Configure>", self._on_canvas_configure)

        card.bind("<Configure>", self._on_card_configure)

        self._scroll_canvas.bind("<MouseWheel>", self._on_scroll_wheel)
        card.bind("<MouseWheel>", self._on_scroll_wheel)
        self._bind_mousewheel_recursive(card)

        self._update_pay_btn()
        self._refresh()

    def _on_canvas_configure(self, event):
        self._scroll_canvas.itemconfig(self._card_win, width=event.width)

    def _on_card_configure(self, _event):
        bbox = self._scroll_canvas.bbox("all")
        if bbox:
            self._scroll_canvas.configure(scrollregion=bbox)

    def _on_scroll_wheel(self, event):
        self._scroll_canvas.yview_scroll(
            int(-1 * (event.delta / 120)), "units")

    def _bind_mousewheel_recursive(self, widget):
        def _enter(_e):
            self._scroll_canvas.bind_all("<MouseWheel>",
                                         self._on_scroll_wheel)
        def _leave(_e):
            self._scroll_canvas.unbind_all("<MouseWheel>")
        widget.bind("<Enter>", _enter)
        widget.bind("<Leave>", _leave)
        for child in widget.winfo_children():
            self._bind_mousewheel_recursive(child)

    def _pack_card(self, parent, pack, index):
        border = tk.Frame(parent, bg=PANEL, highlightbackground="#d7e1ee",
                          highlightthickness=2)
        border.pack(fill="x", pady=px(3))

        left = tk.Frame(border, bg=PANEL)
        left.pack(side="left", fill="both", expand=True, padx=px(10),
                  pady=px(5))

        title_row = tk.Frame(left, bg=PANEL)
        title_row.pack(anchor="w")
        tk.Label(title_row, text=pack["name"], bg=PANEL, fg=INK,
                 font=("Segoe UI Semibold", 11, "bold")).pack(side="left")
        if pack["tag"]:
            tk.Label(title_row, text=f"  {pack['tag']}  ", bg=GOLD,
                     fg="white",
                     font=("Segoe UI", 7, "bold")).pack(side="left",
                                                        padx=px(6))

        if pack.get("debt"):
            bal = self.wallet.balance
            debt = abs(bal) if bal < 0 else 0
            credits_txt = f"{debt:,} credits to clear debt".replace(",", " ")
            price_txt = dollars(debt)
        else:
            credits_txt = f"{pack['credits']:,} credits".replace(",", " ")
            price_txt = pack["price"]
        tk.Label(left, text=credits_txt, bg=PANEL, fg=BLUE_DARK,
                 font=("Segoe UI Semibold", 10)).pack(anchor="w")
        tk.Label(left, text=pack["note"], bg=PANEL, fg=SOFT,
                 font=("Segoe UI", 8)).pack(anchor="w")

        tk.Label(border, text=price_txt, bg=PANEL, fg=INK,
                 font=("Segoe UI Semibold", 12, "bold")).pack(side="right",
                                                              padx=px(12))

        def select(_event, i=index):
            if not self._busy:
                self._selected = i
                self._highlight()
                self._update_pay_btn()

        for w in (border, left, title_row, *left.winfo_children(),
                  *title_row.winfo_children(), *border.winfo_children()):
            w.bind("<Button-1>", select)
        self._cards.append(border)

    def _highlight(self):
        for i, border in enumerate(self._cards):
            if i == self._selected:
                border.config(highlightbackground=STRIPE,
                              highlightthickness=2)
            else:
                border.config(highlightbackground="#d7e1ee",
                              highlightthickness=2)

    def _update_pay_btn(self):
        pack = PACKS[self._selected]
        if pack.get("debt"):
            bal = self.wallet.balance
            debt = abs(bal) if bal < 0 else 0
            if debt <= 0:
                self.pay_btn.config(text="No debt to clear",
                                    state="disabled", bg="#b9b4f5")
            else:
                price = dollars(debt)
                self.pay_btn.config(text=f"🔒  Pay {price} to clear debt",
                                    state="normal", bg=STRIPE)
        else:
            self.pay_btn.config(text=f"🔒  Pay {pack['price']} with Stripe",
                                state="normal", bg=STRIPE)

    def _refresh(self):
        if not self.is_open():
            return
        bal = self.wallet.balance
        self.balance_lbl.config(
            text=f"Balance: {bal} credits  (\u2248 {dollars(bal)})",
            fg=RED if bal <= 0 else BLUE_DARK)
        if bal <= 0:
            self.banner_lbl.config(
                text="⛔ CREDITS DEPLETED: your PC is suspended")
            self.return_btn.pack_forget()
        else:
            self.banner_lbl.config(text="")
            if not self.return_btn.winfo_ismapped():
                self.return_btn.pack(side="left")
        self.win.after(250, self._refresh)

    def _buy(self):
        if self._busy:
            return
        self._busy = True
        self.pay_btn.config(state="disabled", bg="#b9b4f5")
        self._progress_step(0, PACKS[self._selected])

    def _progress_step(self, step, pack):
        if not self.is_open():
            return
        for threshold, text in CHECKOUT_STEPS:
            if step == threshold:
                self.status.config(text=text, fg=SOFT)
        self.progress.delete("all")
        w = self.progress.winfo_width() or px(560)
        self.progress.create_rectangle(0, 0, int(w * step / 20), px(6),
                                       fill=STRIPE, width=0)
        if step < 20:
            self.win.after(120, lambda: self._progress_step(step + 1, pack))
        else:
            self._paid(pack)

    def _paid(self, pack):
        if pack.get("debt"):
            bal = self.wallet.balance
            credits = abs(bal) if bal < 0 else 0
            self.wallet.add(credits, label="Debt Cleared")
            self.status.config(
                text=f"Debt cleared! 🎉  +{credits} credits",
                fg=BLUE_DARK)
        else:
            self.wallet.add(pack["credits"], label=pack["name"])
            self.status.config(
                text=f"Thanks for your purchase 🎉  +{pack['credits']} credits",
                fg=BLUE_DARK)
        self._confetti()

    def _confetti(self):
        if not self.is_open():
            return
        sw = self.bg_canvas.winfo_width() or 1920
        sh = self.bg_canvas.winfo_height() or 1080
        colors = [STRIPE, GOLD, RED, "#2fae66", "#0067c0", "white"]
        pieces = []
        for _ in range(120):
            x = random.randint(0, sw)
            y = -random.randint(0, sh // 2)
            c = random.choice(colors)
            r = self.bg_canvas.create_rectangle(x, y, x + px(7), y + px(12),
                                                fill=c, width=0)
            pieces.append([r, random.randint(px(4), px(10)),
                           random.randint(-px(2), px(2))])
        self._rain(pieces, sh, 0)

    def _rain(self, pieces, sh, frame):
        if not self.is_open():
            return
        if frame > 80:
            for p in pieces:
                self.bg_canvas.delete(p[0])
            self._checkout_done()
            return
        for p in pieces:
            self.bg_canvas.move(p[0], p[2], p[1])
        self.win.after(30, lambda: self._rain(pieces, sh, frame + 1))

    def _checkout_done(self):
        self._busy = False
        self.pay_btn.config(state="normal", bg=STRIPE)
        self.status.config(text="Credits added. Your PC is usable again… "
                                "as long as you have balance.")
        self.win.after(1400, self._close_if_allowed)

    def hwnds(self):
        out = []
        if self.is_open():
            try:
                out.append(int(self.win.winfo_id()))
            except tk.TclError:
                pass
        return out
