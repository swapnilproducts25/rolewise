"""Register Rolewise Fill's local helper with Chrome (native messaging). Run once per laptop.

Usage: .venv/Scripts/python scripts/install_native_host.py <extension id>
The extension id is on chrome://extensions under Rolewise Fill (32 letters a-p).
Windows: writes the host manifest next to the helper and one per-user registry key
  HKCU\\Software\\Google\\Chrome\\NativeMessagingHosts\\com.rolewise.fill  (no admin rights needed).
macOS: writes the manifest to ~/Library/Application Support/Google/Chrome/NativeMessagingHosts/.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOST = "com.rolewise.fill"
NATIVE = ROOT / "extension" / "native"


def main(ext_id):
    if not re.fullmatch(r"[a-p]{32}", ext_id):
        sys.exit("That doesn't look like a Chrome extension id (32 letters a-p). Copy it from chrome://extensions.")
    if sys.platform == "win32":
        launcher = NATIVE / "rolewise_host.bat"
        py = ROOT / ".venv" / "Scripts" / "python.exe"
        launcher.write_text(f'@echo off\r\n"{py if py.exists() else "python"}" "{NATIVE / "rolewise_host.py"}" %*\r\n',
                            encoding="utf-8")
    else:
        launcher = NATIVE / "rolewise_host.sh"
        py = ROOT / ".venv" / "bin" / "python"
        launcher.write_text(f'#!/bin/sh\nexec "{py if py.exists() else "python3"}" "{NATIVE / "rolewise_host.py"}" "$@"\n',
                            encoding="utf-8")
        launcher.chmod(0o755)
    manifest = {"name": HOST, "description": "Rolewise Fill local helper", "path": str(launcher), "type": "stdio",
                "allowed_origins": [f"chrome-extension://{ext_id}/"]}
    target = NATIVE / f"{HOST}.json"
    if sys.platform == "darwin":
        target = Path.home() / "Library/Application Support/Google/Chrome/NativeMessagingHosts" / f"{HOST}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    if sys.platform == "win32":
        import winreg
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"Software\Google\Chrome\NativeMessagingHosts\{HOST}")
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, str(target))
        winreg.CloseKey(key)
    print(f"Registered {HOST} for extension {ext_id}.\nReload Rolewise Fill in chrome://extensions to use it.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
