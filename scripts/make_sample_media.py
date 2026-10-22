"""Create Phase 6 sample media (idempotent).

- data/media/earnings_clip.wav : short spoken earnings-call excerpt (Windows TTS)
- data/media/competitor_dashboard.png : synthetic competitor dashboard screenshot

The audio is synthesized speech, the dashboard is a drawn mock. Both are
clearly synthetic stand-ins for a real call recording / real screenshot.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / "data" / "media"
WAV = MEDIA / "earnings_clip.wav"
PNG = MEDIA / "competitor_dashboard.png"

SCRIPT = (
    "Thank you for joining the Acme Semiconductor fourth quarter earnings call. "
    "Data center revenue grew forty two percent year over year to nine point one billion dollars. "
    "We expect Blackwell supply constraints from advanced packaging and H B M memory to persist "
    "through the first half of next year. Export controls on China remain a headwind, "
    "and we guided gross margin to seventy two percent."
)


def make_wav() -> Path:
    MEDIA.mkdir(parents=True, exist_ok=True)
    if WAV.exists() and WAV.stat().st_size > 10_000:
        return WAV
    ps = (
        "Add-Type -AssemblyName System.Speech;"
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer;"
        "$s.SelectVoice('Microsoft Zira Desktop');"
        f"$s.SetOutputToWaveFile('{WAV}');"
        f"$s.Speak(\"{SCRIPT}\");"
        "$s.Dispose()"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True)
    return WAV


def make_dashboard() -> Path:
    from PIL import Image, ImageDraw

    MEDIA.mkdir(parents=True, exist_ok=True)
    if PNG.exists() and PNG.stat().st_size > 2_000:
        return PNG
    img = Image.new("RGB", (900, 520), "#0f172a")
    d = ImageDraw.Draw(img)
    d.text((30, 20), "RivalCo Analytics - Competitor Dashboard (mock)", fill="white")
    tiles = [("Monthly Active Users", "4.2M", "+18% MoM"),
             ("Revenue Run-Rate", "$310M", "+9% QoQ"),
             ("Churn", "2.1%", "-0.4 pts"),
             ("Enterprise Customers", "1,240", "+85 this month")]
    for i, (label, value, delta) in enumerate(tiles):
        x = 30 + (i % 2) * 430
        y = 70 + (i // 2) * 130
        d.rectangle([x, y, x + 400, y + 110], fill="#1e293b", outline="#334155")
        d.text((x + 15, y + 12), label, fill="#94a3b8")
        d.text((x + 15, y + 45), value, fill="#38bdf8")
        d.text((x + 15, y + 80), delta, fill="#4ade80")
    bars = [60, 80, 75, 110, 140, 170]
    for i, h in enumerate(bars):
        d.rectangle([60 + i * 60, 470 - h, 100 + i * 60, 470], fill="#38bdf8")
    d.text((60, 480), "Signups by month (Jan-Jun): steady growth, sharp rise since April", fill="#94a3b8")
    img.save(PNG)
    return PNG


if __name__ == "__main__":
    print("wav:", make_wav())
    print("png:", make_dashboard())
    sys.exit(0)
