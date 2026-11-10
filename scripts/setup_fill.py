"""Set up Rolewise Fill on this laptop with one command (run it from your rolewise folder).

Usage: python scripts/setup_fill.py

It installs the two Python packages, opens Chrome's extensions page and copies the add-on folder's path, waits while
you switch on Developer mode and click Load unpacked (Chrome only allows that by hand), then registers the local helper
and builds your job queue. Safe to run again any time.
"""
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
EXT = ROOT / "extension"
WIN, MAC = platform.system() == "Windows", platform.system() == "Darwin"


def step(n, text):
    print(f"\n[{n}/4] {text}", flush=True)


def chrome_path():
    for p in (shutil.which("chrome"), shutil.which("google-chrome"),
              r"C:\Program Files\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
              os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
              "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"):
        if p and Path(p).exists():
            return p
    return None


def copy(text):
    try:
        cmd = ["clip"] if WIN else ["pbcopy"] if MAC else ["xclip", "-selection", "clipboard"]
        subprocess.run(cmd, input=text.encode("utf-16le" if WIN else "utf-8"), check=True)
        return True
    except (OSError, subprocess.CalledProcessError):
        return False


def main():
    if not (ROOT / ".git").exists():
        print("Note: this folder isn't a git clone, so new jobs won't reach the add-on. Use `git clone` instead of a zip.")

    step(1, "Python packages")
    user = [] if sys.prefix != sys.base_prefix else ["--user"]   # --user isn't allowed inside a virtualenv
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", *user, "python-docx", "pyyaml"])
    import install_native_host as host   # after the packages, which build_kits needs

    step(2, "Load the add-on in Chrome")
    ext_id = host.find_ext_id()
    if ext_id:
        print("Already loaded.")
    else:
        chrome = chrome_path()
        if not chrome:
            sys.exit("Chrome isn't installed. Install it from google.com/chrome, then run this again.")
        subprocess.Popen([chrome, "chrome://extensions/"])
        copied = copy(str(EXT))
        print("Chrome is opening its Extensions page. There:\n"
              "  1. Switch on Developer mode (top right).\n"
              "  2. Click Load unpacked and choose this folder"
              + (" (its path is copied: paste it into the folder box):" if copied else ":") + f"\n     {EXT}\n"
              "Waiting for it to appear...")
        for _ in range(300):   # up to 10 minutes
            time.sleep(2)
            ext_id = host.find_ext_id()
            if ext_id:
                break
        if not ext_id:
            sys.exit("Didn't see Rolewise Fill in Chrome yet. Load it as above, then run this again.")
        print("Found it.")

    step(3, "Local helper (one-click Skip, Applied, Pause, Debrief)")
    host.main(ext_id)

    step(4, "Your job queue")
    subprocess.run([sys.executable, str(ROOT / "scripts" / "build_kits.py")], cwd=ROOT)
    print("\nDone. In chrome://extensions click the reload arrow on Rolewise Fill, then pin it (puzzle icon, pin).\n"
          "Click it any time to see your queue; it fetches new jobs by itself.")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
