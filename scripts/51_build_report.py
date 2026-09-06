"""Assemble the report: inline every referenced figure as a base64 data URI.

The Artifact CSP blocks external images entirely, so figures must ship inside the page. Each is
downscaled to a sensible display width first - the source PNGs are 200 dpi for print and far larger
than they need to be on screen.
"""
import base64, io, pathlib, re
from PIL import Image

ROOT = pathlib.Path(__file__).parent.parent
TPL = ROOT / "report" / "template.html"
FIG = ROOT / "figures"
OUT = ROOT / "report" / "index.html"
MAX_W = 1600

html = TPL.read_text(encoding="utf-8")
names = re.findall(r'src="FIG:([a-z0-9_]+)"', html)
print(f"figures referenced: {len(names)}")

total = 0
for n in dict.fromkeys(names):
    src = FIG / f"{n}.png"
    if not src.exists():
        raise FileNotFoundError(f"missing figure: {src}")
    im = Image.open(src).convert("RGB")
    if im.width > MAX_W:
        im = im.resize((MAX_W, round(im.height * MAX_W / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=88, optimize=True, progressive=True)
    b64 = base64.b64encode(buf.getvalue()).decode()
    total += len(b64)
    html = html.replace(f'src="FIG:{n}"', f'src="data:image/jpeg;base64,{b64}"')
    print(f"  {n:<38} {im.width}x{im.height}  {len(b64) / 1024:6.0f} KB")

assert "FIG:" not in html, "unreplaced figure placeholder"
OUT.write_text(html, encoding="utf-8")
print(f"\n-> {OUT}   {len(html) / 1024 / 1024:.2f} MB total  "
      f"(images {total / 1024 / 1024:.2f} MB)")
