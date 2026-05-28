"""Entry point for the packaged desktop application.

When you double-click BulkMailer.exe this file runs:
  1. First-run setup — create config/data/templates dirs next to the exe.
  2. Start Flask in a background thread.
  3. Wait until the local server is ready, then open the browser.
  4. Show a system-tray icon with Open / Quit options.
"""

import os
import sys
import threading
import time
import webbrowser
import urllib.request

# ── first-run setup ───────────────────────────────────────────────────────────
# Must happen before importing app so paths are initialised correctly.
from main import _create_starter_files
_create_starter_files()

# ── import Flask app ──────────────────────────────────────────────────────────
from app import flask_app

PORT = 5000
URL  = f"http://127.0.0.1:{PORT}"


def _run_flask():
    flask_app.run(host="127.0.0.1", port=PORT, debug=False, use_reloader=False)


def _wait_for_server(timeout: float = 15.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(URL, timeout=1)
            return True
        except Exception:
            time.sleep(0.25)
    return False


def _make_icon():
    """Draw a simple envelope icon with Pillow."""
    from PIL import Image, ImageDraw
    size = 128
    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d    = ImageDraw.Draw(img)

    m  = size // 8          # margin
    bx = [m, size // 3, size - m, size - m]   # envelope body rect

    # body
    d.rectangle(bx, fill=(31, 57, 125))
    # flap (triangle)
    mid = size // 2
    fold_y = bx[1] + (bx[3] - bx[1]) // 2
    d.polygon([(m, bx[1]), (size - m, bx[1]), (mid, fold_y)],
              fill=(255, 255, 255, 200))
    # outline
    d.rectangle(bx, outline=(200, 215, 255), width=3)
    # bottom-left crease
    d.line([(m, bx[3]), (mid - size // 10, fold_y)],
           fill=(200, 215, 255, 160), width=2)
    # bottom-right crease
    d.line([(size - m, bx[3]), (mid + size // 10, fold_y)],
           fill=(200, 215, 255, 160), width=2)
    return img


def main():
    # start Flask
    t = threading.Thread(target=_run_flask, daemon=True)
    t.start()

    ready = _wait_for_server()
    if not ready:
        # show an error in a message box on Windows; just print elsewhere
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(   # type: ignore[attr-defined]
                0,
                "Could not start the local server.\nCheck that port 5000 is free.",
                "Bulk Gmail Mailer",
                0x10,
            )
        except Exception:
            print("ERROR: server did not start on port 5000")
        sys.exit(1)

    webbrowser.open(URL)

    # ── system tray ───────────────────────────────────────────────────────────
    try:
        import pystray

        def _open(_icon=None, _item=None):
            webbrowser.open(URL)

        def _quit(icon, _item=None):
            icon.stop()
            os._exit(0)

        tray_icon = pystray.Icon(
            "BulkMailer",
            _make_icon(),
            "Bulk Gmail Mailer",
            menu=pystray.Menu(
                pystray.MenuItem("Open Mailer", _open, default=True),
                pystray.MenuItem("Quit",        _quit),
            ),
        )
        tray_icon.run()

    except Exception:
        # No tray support — keep the process alive until Ctrl-C
        try:
            t.join()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
