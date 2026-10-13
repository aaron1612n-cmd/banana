"""Make numbered contact sheets: sheets.py OUTDIR PREFIX FILE... ; prints index -> file map to OUTDIR/PREFIX.map"""
import sys, os
from PIL import Image, ImageDraw
out, prefix, files = sys.argv[1], sys.argv[2], sys.argv[3:]
os.makedirs(out, exist_ok=True)
T, C, R = 220, 6, 5
with open(os.path.join(out, prefix + ".map"), "w") as m:
    for s in range(0, len(files), C * R):
        sheet = Image.new("RGB", (C * T, R * T), "white"); d = ImageDraw.Draw(sheet)
        for i, f in enumerate(files[s:s + C * R]):
            try:
                im = Image.open(f).convert("RGB"); im.thumbnail((T - 6, T - 22))
                sheet.paste(im, ((i % C) * T + 3, (i // C) * T + 20))
            except Exception:
                pass
            d.rectangle([(i % C) * T, (i // C) * T, (i % C) * T + 40, (i // C) * T + 18], fill="black")
            d.text(((i % C) * T + 4, (i // C) * T + 3), str(s + i), fill="yellow")
            m.write(f"{s + i}\t{f}\n")
        sheet.save(os.path.join(out, f"{prefix}-{s // (C * R):03d}.jpg"), quality=80)
