#!/usr/bin/env python3
"""
pick_best_cards.py — collapse repeated captures of the same on-screen card.

When to run: extract_slides.py reported the slide region as ~100% of the frame
and saved far more captures than there are slides. That happens when the video
is a talking head with EDITOR-MADE GRAPHIC CARDS laid over it (webcam inside the
frame): every time the speaker moves, the "same" card is captured again.

What it does: groups captures by their OCR title line (first line, upper-case
headline), keeps the most complete capture of each (most OCR text = final build,
tie → longest on screen), and writes:

  <slides_dir>/cards/card_NN_MMmSSs.png   one PNG per distinct card, in order
  <slides_dir>/CARDS.md                   index: image, time first shown, text
  <slides_dir>/cards.json
  <slides_dir>/cards_sheet.jpg            all cards on one page — read this first

Usage:  python3 pick_best_cards.py "<OUT>/slides" [--url https://youtu.be/ID]
Requires Pillow (pip3 install Pillow).
The full capture set in slides/ is left untouched.
"""
import json, os, re, shutil, sys
from PIL import Image

def norm(t): return re.sub(r"[^A-Z ]", "", t.upper()).strip()

def main():
    d = os.path.abspath(sys.argv[1])
    url = sys.argv[sys.argv.index("--url") + 1] if "--url" in sys.argv else None
    meta = json.load(open(os.path.join(d, "slides.json")))
    groups = {}
    for e in meta["slides"]:
        o = e.get("ocr") or []
        if not o: continue
        first = o[0].lstrip('("“ ')
        k = norm(first)
        # a card headline: reasonably long and written in capitals
        if len(k) < 8 or sum(c.islower() for c in first) > len(first) * 0.2: continue
        groups.setdefault(k, []).append(e)
    best = []
    for k, es in groups.items():
        b = max(es, key=lambda e: (sum(len(x) for x in e["ocr"]), e["end"] - e["start"]))
        best.append({"title": k.title(), "first_shown": min(x["start"] for x in es),
                     "first_clock": min(es, key=lambda x: x["start"])["start_clock"],
                     "captures": len(es), "src": b["file"], "ocr": b["ocr"]})
    best.sort(key=lambda b: b["first_shown"])
    out = os.path.join(d, "cards"); os.makedirs(out, exist_ok=True)
    vid = re.search(r"(?:youtu\.be/|v=)([\w-]{11})", url).group(1) if url else None
    md = [f"# Cards — {len(best)} distinct on-screen cards", "",
          f"Picked from {len(meta['slides'])} captures (same card re-captured as the speaker moved). "
          "Most complete version of each, in order of first appearance.", ""]
    for i, b in enumerate(best, 1):
        t = int(b["first_shown"]); name = f"card_{i:02d}_{t//60:02d}m{t%60:02d}s.png"
        shutil.copyfile(os.path.join(d, b["src"]), os.path.join(out, name)); b["file"] = f"cards/{name}"
        ts = f"[{b['first_clock']}](https://youtu.be/{vid}?t={t})" if vid else b["first_clock"]
        md += [f"## Card {i} — {ts} — {b['title']}", "", f"![Card {i}]({b['file']})", "",
               "```text", *b["ocr"], "```", ""]
        print(f"{i:3d}  {b['first_clock']:>8}  x{b['captures']:<3} {b['title'][:60]}")
    open(os.path.join(d, "CARDS.md"), "w").write("\n".join(md))
    json.dump(best, open(os.path.join(d, "cards.json"), "w"), indent=1)
    if best:
        ims = [Image.open(os.path.join(d, b["file"])).convert("RGB").resize((640, 360)) for b in best]
        rows = (len(ims) + 2) // 3
        s = Image.new("RGB", (1920, rows * 360), "white")
        for i, im in enumerate(ims): s.paste(im, ((i % 3) * 640, (i // 3) * 360))
        s.save(os.path.join(d, "cards_sheet.jpg"), quality=82)
    print(f"{len(best)} cards → {out}")

if __name__ == "__main__":
    main()
