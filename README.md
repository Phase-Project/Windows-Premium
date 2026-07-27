<p align="center">
  <img src="https://raw.githubusercontent.com/phaseworld-creator/phase-raid-bot/refs/heads/main/assets/phase.png?s=512" alt="Phase Raid Bot" width="200" height="200">
</p>

<h1 align="center">Windows Premium Edition</h1>

<p align="center">Your PC now charges you for every click, every keystroke, every breath you take on this machine.</p>


Windows Premium Edition is a joke app that turns your computer into a
dystopian pay-per-use nightmare. Left-click? That'll be 3 cents. Typed a
letter? 1 cent. Opened an app? 30 cents. When your balance hits zero, a
giant fullscreen shop **locks you out of your own PC** until you "buy"
more credits (free, obviously — no real money, no credit card, just
pure satire).

---

## How It Works

**On launch**, a fullscreen activation screen offers credit packs via a
fake Stripe button. You click, a fake payment sequence runs, confetti
falls, credits arrive. **No real payment. No credit card.**

Then, every action on your PC costs credits:

| Action | Cost |
|---|---|
| Left click | 3 credits |
| Right click | 5 credits |
| Middle click | 4 credits |
| Scroll (per notch) | 1 credit |
| Keystroke | 1 credit |
| Create a folder | 20 credits |
| Create a file | 10 credits |
| Delete a file | 15 credits |
| Launch an application | 30 credits |

> 1 credit = $0.01. Every action literally costs a few cents.

A small bubble appears near your mouse on each charge. If you minimize
the window, a floating **"Credits remaining"** counter stays visible in
the bottom-right corner of your screen (click it to reopen).

When you hit 0 credits, the shop window **comes back to block the
screen** and your clicks are actually suspended (left / right / middle)
except over app windows, so you can always "repurchase" credits.

---

## Credit Packs

The shop offers several tiers:

| Pack | Credits | Price |
|---|---|---|
| Trial Pack | 100 | $1.99 |
| Starter Pack | 500 | $4.99 |
| Comfort Pack | 2,000 | $9.99 |
| Pro Pack | 10,000 | $29.99 |
| Business Pack | 50,000 | $79.99 |
| Enterprise Pack | 200,000 | $199.99 |
| Pay Your Debt | Clears debt | Varies |

> All prices are fictional. No real money is involved.

---

## Installation

1. **Install Python** (free): [python.org/downloads](https://www.python.org/downloads/)
   Check *"Add python.exe to PATH"* during installation.

2. **Install dependencies:**
   ```
   py -m pip install -r requirements.txt
   ```

3. **Launch:**
   ```
   py main.py
   ```

### Dependencies

| Package | Purpose |
|---|---|
| `pillow>=10.0.0` | Image loading and resizing for the UI |
| `watchdog>=3.0.0` | File system watcher (charges for file operations) |

---

## Panic Key

> **Ctrl + Alt + Shift + P**

Shuts everything down immediately and gives back mouse control.

You can also click the **"Quit demo (panic)"** link on the shop screen,
or close the Windows Premium Edition window.

If the app crashes, Windows removes the hooks automatically — no risk
of getting stuck.

---

## Project Structure

```
main.py              Entry point
src/
  assets.py          Image loading (Pillow with fallback)
  fswatch.py         File system watcher (charges for file ops)
  hooks.py           Low-level mouse/keyboard hooks (Win32)
  overlay.py         Floating charge bubbles near the cursor
  procwatch.py       Application launcher watcher
  shop.py            Fullscreen credit shop (fake Stripe checkout)
  state.py           Wallet, cost table, persistence
  ui.py              DPI scaling helper
assets/
  coin.png           Credit coin icon
  paywall_bg.jpg     Shop background image
  icons/             Action icons for charge bubbles
```

---

## Test Mode

To test without risk of getting locked out:

```
set WPE_TEST=1 && py main.py
```

Click blocking is disabled and actions are simulated automatically.

---

## Uninstallation

1. Delete this folder.
2. (Optional) Delete the saved balance:
   ```
   %APPDATA%\WindowsPremiumEdition
   ```

---

**Windows only.** Your balance (and your debt) is saved between launches,
because that's funnier.
