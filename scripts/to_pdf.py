"""Convert a job's CV and cover letter (.docx) to PDF with LibreOffice, next to the originals.

Usage: .venv/Scripts/python scripts/to_pdf.py <job id> [<job id> ...]     # or --all for every job folder
       .venv/Scripts/python scripts/to_pdf.py --styles                      # cv-styles/*.docx previews
Skips files whose PDF is newer than the .docx. Needs LibreOffice (soffice); on a Linux cloud machine it tries a one-off install, else prints a hint.
build_kits.py then prefers the PDFs automatically.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

from userconf import USER  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CANDIDATES = [r"C:\Program Files\LibreOffice\program\soffice.exe",
              r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"]


def soffice():
    found = shutil.which("soffice") or shutil.which("libreoffice")
    return found or next((c for c in CANDIDATES if Path(c).exists()), None)


def install_on_linux():
    """Cloud sessions (claude.ai/code) are Linux machines without LibreOffice: try a one-off quiet install."""
    if not sys.platform.startswith("linux") or not shutil.which("apt-get"):
        return None
    sudo = [] if hasattr(os, "geteuid") and os.geteuid() == 0 else (["sudo", "-n"] if shutil.which("sudo") else None)
    if sudo is None:
        return None
    env = dict(os.environ, DEBIAN_FRONTEND="noninteractive")
    for cmd in (["apt-get", "update", "-qq"], ["apt-get", "install", "-y", "-qq", "--no-install-recommends",
                                              "libreoffice-writer-nogui"]):
        try:
            subprocess.run(sudo + cmd, check=True, capture_output=True, timeout=600, env=env)
        except (subprocess.SubprocessError, OSError) as e:
            print(f"LibreOffice install failed ({type(e).__name__}); the .docx files will be used.")
            return None
    return soffice()


def convert(job_id, exe):
    folder = ROOT / "applications" / job_id
    done = []
    for docx in sorted(folder.glob(f"{USER.get('file_prefix') or USER['name']} - *.docx")):
        pdf = docx.with_suffix(".pdf")
        if pdf.exists() and pdf.stat().st_mtime >= docx.stat().st_mtime:
            continue
        subprocess.run([exe, "--headless", "--convert-to", "pdf", "--outdir", str(folder), str(docx)],
                       check=True, capture_output=True, timeout=120)
        done.append(pdf.name)
    return done


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    exe = soffice() or install_on_linux()
    if not exe:
        sys.exit("LibreOffice not found. Windows: winget install --id TheDocumentFoundation.LibreOffice -e | "
                 "Mac: brew install --cask libreoffice | Linux/cloud: apt-get install -y libreoffice-writer (else use the .docx)")
    if sys.argv[1:] == ["--styles"]:   # the CV style previews made during /onboard
        for docx in sorted((ROOT / "cv-styles").glob("*.docx")):
            subprocess.run([exe, "--headless", "--convert-to", "pdf", "--outdir", str(docx.parent), str(docx)],
                           check=True, capture_output=True, timeout=120)
            print(docx.with_suffix(".pdf").name)
        sys.exit(0)
    apps = ROOT / "applications"
    ids = ([p.name for p in apps.iterdir() if p.is_dir()] if apps.exists() else []) if sys.argv[1:] == ["--all"] else sys.argv[1:]
    for jid in ids:
        out = convert(jid, exe)
        if out:
            print(f"{jid}: {', '.join(out)}")
