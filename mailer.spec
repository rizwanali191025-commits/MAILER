# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Bulk Gmail Mailer
# Build with:  pyinstaller mailer.spec

from pathlib import Path

ROOT = Path(".").resolve()

a = Analysis(
    ["launcher.py"],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        # web UI — Flask templates and static files
        ("web/templates", "web/templates"),
        ("web/static",    "web/static"),
    ],
    hiddenimports=[
        # Google auth
        "google.auth",
        "google.auth.transport",
        "google.auth.transport.requests",
        "google.oauth2",
        "google.oauth2.credentials",
        "google_auth_oauthlib",
        "google_auth_oauthlib.flow",
        "googleapiclient",
        "googleapiclient.discovery",
        "googleapiclient.http",
        # Flask / Jinja2
        "flask",
        "jinja2",
        "werkzeug",
        "werkzeug.serving",
        "werkzeug.routing",
        # python-pptx
        "pptx",
        "pptx.util",
        "pptx.dml.color",
        "pptx.enum.text",
        "pptx.oxml.ns",
        # parsing
        "bs4",
        "lxml",
        "lxml.etree",
        "lxml._elementpath",
        # image / tray
        "PIL",
        "PIL.Image",
        "PIL.ImageDraw",
        "pystray",
        "pystray._win32",   # Windows tray backend
        # misc
        "rich",
        "click",
        "pandas",
        "email.mime.multipart",
        "email.mime.text",
        "email.mime.application",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="BulkMailer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # no black terminal window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets/icon.ico", # Windows taskbar + Explorer icon
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="BulkMailer",       # output folder: dist/BulkMailer/
)
