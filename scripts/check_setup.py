"""Check that this machine is ready for Rolewise and say exactly how to fix anything missing.

Usage: python scripts/check_setup.py
Prints one line per item: OK / MISSING + the fix. Exit code 0 when everything needed to start is in place.
"""
import importlib.util
import json
import platform
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WIN = platform.system() == "Windows"
MAC = platform.system() == "Darwin"
results = []


def check(name, ok, fix, needed=True):
    results.append((name, ok, fix, needed))


check("Python 3.10+", sys.version_info >= (3, 10), "Install Python 3.12 from python.org (tick 'Add to PATH').")
for mod, pkg in (("docx", "python-docx"), ("yaml", "pyyaml")):
    check(f"Python package {pkg}", importlib.util.find_spec(mod) is not None, f"python -m pip install {pkg}")

soffice = shutil.which("soffice") or next((p for p in (
    r"C:\Program Files\LibreOffice\program\soffice.exe", "/Applications/LibreOffice.app/Contents/MacOS/soffice")
    if Path(p).exists()), None)
check("LibreOffice (for PDF CVs)", bool(soffice),
      "winget install --id TheDocumentFoundation.LibreOffice -e" if WIN else "brew install --cask libreoffice",
      needed=False)

chrome = shutil.which("chrome") or next((p for p in (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "/Applications/Google Chrome.app") if Path(p).exists()), None)
check("Google Chrome (for Rolewise Fill)", bool(chrome), "Install Chrome from google.com/chrome.")

user = ROOT / "profile" / "user.yaml"
named = False
if user.exists() and importlib.util.find_spec("yaml"):
    import yaml
    named = bool((yaml.safe_load(user.read_text(encoding="utf-8")) or {}).get("name"))
check("Profile set up", named, "Run /onboard.", needed=False)
check("CV data (profile/master-cv.yaml)", (ROOT / "profile" / "master-cv.yaml").exists(), "Run /onboard.", needed=False)
tracker = ROOT / "tracker" / "applications.json"
check("Tracker", tracker.exists(), "Created by /onboard.", needed=False)
kits = ROOT / "extension" / "kits" / "index.json"
n_kits = len(json.loads(kits.read_text(encoding="utf-8"))) if kits.exists() else 0
check("Rolewise Fill kits", n_kits > 0, "Built automatically once a job is prepared (scripts/build_kits.py).", needed=False)

width = max(len(r[0]) for r in results)
for name, ok, fix, needed in results:
    mark = "OK     " if ok else ("MISSING" if needed else "LATER  ")
    print(f"{mark}  {name.ljust(width)}" + ("" if ok else f"   ->  {fix}"))
sys.exit(0 if all(ok for _, ok, _, needed in results if needed) else 1)
