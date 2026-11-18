#!/usr/bin/env python3
"""
extract_slides.py — capture every distinct slide shown in a video presentation.

Works on: full-screen slide decks, screen-shares with a webcam strip/overlay,
podcasts that cut between faces and slides, and decks with progressive builds.

How it works
  1. Decode the video at 1 fps into small greyscale frames (fast, ffmpeg pipe).
  2. Find the SLIDE REGION automatically: pixels whose frame-to-frame change is
     almost always ~0 (slides) vs. constantly moving (webcam faces). The region
     is the bounding box of the "mostly still" pixels. Override with --crop.
  3. Walk the timeline: a slide is a run of frames that are stable (consecutive
     diff below --still) for at least --min-hold seconds inside the region.
     Stable frames whose region has a near-uniform/blank look are ignored.
  4. A new slide starts when the stable picture differs from the previous slide
     by more than --change. Progressive builds (one box lighting up) count as
     new slides — that's deliberate: builds carry meaning.
  5. Revisits (presenter flips back) are detected with a perceptual hash and
     recorded against the first capture instead of saved twice.
  6. For every slide: grab the FULL-RES frame from the middle of its hold,
     save the cropped slide PNG + the full frame JPG, and attach the transcript
     lines spoken while it was on screen.

Outputs (in --out):
  slides/slide_001_00m42s.png       cropped slide, full resolution
  frames/slide_001_00m42s_full.jpg  whole frame (with webcam) for context
  slides.json                       machine index (times, crop, revisits, text)
  SLIDES.md                         human index: image + timestamp + what was said
  contact_sheet.jpg                 all slides on one page for a quick scan

Usage
  python3 extract_slides.py VIDEO.mp4 --out "<folder>/slides" \
      [--transcript ts.txt] [--url https://youtu.be/ID] [--crop x,y,w,h]

  ts.txt = output of get_transcript.py --timestamps ("[MM:SS] text" lines).

Requirements: ffmpeg + ffprobe on the PATH, Python packages numpy and Pillow.
OCR (the exact text on each slide) uses Apple Vision and therefore only runs on
macOS, where ocr.swift is compiled on first use. On Windows and Linux the slides
are still captured and indexed; the "Text on slide" blocks are simply absent.
Part of the video-to-skill package (gregkowalczyk.com/skills/video-to-skill/).
"""
import argparse, json, os, re, shutil, subprocess, sys
try:
    import numpy as np
    from PIL import Image
except ImportError:
    sys.exit("extract_slides.py needs numpy and Pillow:  pip3 install numpy Pillow")

for _tool in ("ffmpeg", "ffprobe"):
    if not shutil.which(_tool):
        sys.exit(f"{_tool} not found. Install ffmpeg (macOS: brew install ffmpeg; "
                 "Windows/Linux: ffmpeg.org) and make sure it is on your PATH.")

SW, SH = 320, 180  # analysis resolution


def probe(video):
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height:format=duration",
        "-of", "json", video])
    j = json.loads(out)
    s = j["streams"][0]
    return s["width"], s["height"], float(j["format"]["duration"])


def decode_small(video, fps):
    cmd = ["ffmpeg", "-v", "error", "-i", video, "-vf",
           f"fps={fps},scale={SW}:{SH},format=gray", "-f", "rawvideo", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    frames = []
    n = SW * SH
    while True:
        buf = p.stdout.read(n)
        if len(buf) < n:
            break
        frames.append(np.frombuffer(buf, np.uint8).reshape(SH, SW).astype(np.int16))
    p.wait()
    return np.stack(frames)


def find_region(frames, motion_thresh=6, still_frac=0.80):
    """Bounding box (in analysis px) of pixels that are still most of the time."""
    d = np.abs(np.diff(frames, axis=0))            # (T-1, H, W)
    still = (d < motion_thresh).mean(axis=0)       # fraction of time each px is still
    mask = still >= still_frac
    # drop thin noise: require a column/row to be mostly still to count
    cols = np.where(mask.mean(axis=0) > 0.5)[0]
    rows = np.where(mask.mean(axis=1) > 0.5)[0]
    if len(cols) < SW * 0.25 or len(rows) < SH * 0.25:
        return (0, 0, SW, SH), mask
    # longest contiguous run of still columns/rows = the slide panel
    def longest_run(idx):
        best, start, prev = (idx[0], idx[0]), idx[0], idx[0]
        for i in idx[1:]:
            if i != prev + 1:
                if prev - start > best[1] - best[0]:
                    best = (start, prev)
                start = i
            prev = i
        if prev - start > best[1] - best[0]:
            best = (start, prev)
        return best
    x0, x1 = longest_run(cols)
    y0, y1 = longest_run(rows)
    return (x0, y0, x1 - x0 + 1, y1 - y0 + 1), mask


def ahash(img, size=16):
    small = np.array(Image.fromarray(img.astype(np.uint8)).resize((size, size), Image.BILINEAR), np.int16)
    return small > small.mean()


def fmt(t):
    t = int(round(t))
    return f"{t // 60:02d}m{t % 60:02d}s"


def clock(t):
    t = int(round(t))
    return f"{t // 3600}:{t % 3600 // 60:02d}:{t % 60:02d}" if t >= 3600 else f"{t // 60}:{t % 60:02d}"


def load_transcript(path):
    if not path or not os.path.exists(path):
        return []
    lines = []
    for ln in open(path, encoding="utf-8"):
        m = re.match(r"\[(?:(\d+):)?(\d+):(\d+)\]\s*(.*)", ln.strip())
        if m:
            h = int(m.group(1) or 0)
            lines.append((h * 3600 + int(m.group(2)) * 60 + int(m.group(3)), m.group(4)))
    return lines


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--out", required=True)
    ap.add_argument("--transcript", help="timestamped transcript ([MM:SS] lines)")
    ap.add_argument("--url", help="source URL, used for clickable timestamps in SLIDES.md")
    ap.add_argument("--crop", help="force slide region x,y,w,h in FULL-RES pixels")
    ap.add_argument("--fps", type=float, default=1.0, help="analysis sample rate (default 1)")
    ap.add_argument("--still", type=float, default=2.0, help="mean abs diff below which consecutive frames are 'stable'")
    ap.add_argument("--change", type=float, default=3.0, help="mean abs diff vs last slide that makes a NEW slide")
    ap.add_argument("--min-hold", type=float, default=2.0, help="seconds a slide must stay on screen")
    ap.add_argument("--min-detail", type=float, default=4.0, help="std-dev below which a frame is blank/black and skipped")
    ap.add_argument("--build-frac", type=float, default=0.008,
                    help="share of strongly-changed pixels that marks a progressive build (default 0.8%%)")
    ap.add_argument("--no-ocr", action="store_true", help="skip OCR (macOS-only Apple Vision step)")
    ap.add_argument("--revisit-bits", type=int, default=6, help="hash distance (of 256) treated as the same slide")
    a = ap.parse_args()

    W, H, dur = probe(a.video)
    print(f"video {W}x{H}, {dur/60:.1f} min — decoding at {a.fps} fps…", flush=True)
    frames = decode_small(a.video, a.fps)
    T = len(frames)
    sx, sy = W / SW, H / SH

    if a.crop:
        cx, cy, cw, ch = [int(v) for v in a.crop.split(",")]
        rx, ry, rw, rh = int(cx / sx), int(cy / sy), max(1, int(cw / sx)), max(1, int(ch / sy))
        region_src = "manual"
    else:
        (rx, ry, rw, rh), _ = find_region(frames)
        # pad 1 analysis px inward to avoid border bleed, then map to full res
        cx, cy = int(rx * sx), int(ry * sy)
        cw, ch = int(rw * sx), int(rh * sy)
        region_src = "auto"
    print(f"slide region ({region_src}): x={cx} y={cy} w={cw} h={ch} "
          f"({100*cw*ch/(W*H):.0f}% of frame)", flush=True)

    R = frames[:, ry:ry + rh, rx:rx + rw]
    step = 1.0 / a.fps
    hold = max(1, int(round(a.min_hold * a.fps)))

    # stable runs
    diffs = np.abs(np.diff(R, axis=0)).mean(axis=(1, 2))
    stable = np.concatenate([[False], diffs < a.still])
    runs, i = [], 0
    while i < T:
        if stable[i] or (i + 1 < T and stable[i + 1]):
            j = i
            while j + 1 < T and stable[j + 1]:
                j += 1
            if j - i + 1 >= hold:
                runs.append((i, j))
            i = j + 1
        else:
            i += 1

    # split runs that drift without a hard cut (slow builds, scrolling)
    # A build = a share of pixels changing strongly (>40 grey levels) and STAYING
    # changed for --min-hold. Mean difference misses small builds (a KPI strip
    # appearing under a diagram); compression noise is transient and stays <0.5%.
    def changed(k, ref):
        d = np.abs(R[k] - R[ref])
        return d.mean() > a.change or (d > 40).mean() >= a.build_frac

    segs = []
    for (i, j) in runs:
        s0 = i
        k = i + 1
        while k <= j:
            if changed(k, s0) and all(changed(m, s0) for m in range(k, min(j, k + hold - 1) + 1)):
                if k - s0 >= hold:
                    segs.append((s0, k - 1))
                s0 = k
            k += 1
        if j - s0 + 1 >= hold:
            segs.append((s0, j))

    slides, last = [], None
    for (seg_start, j) in segs:
        mid = (seg_start + j) // 2
        img = R[mid]
        if img.std() < a.min_detail:
            continue
        dl = np.abs(img - last["img"]) if last is not None else None
        if dl is not None and dl.mean() <= a.change and (dl > 40).mean() < a.build_frac:
            last["end"] = j  # same slide continues after a brief disturbance
            continue
        h = ahash(img)
        # revisit = same coarse hash AND no build-sized pixel difference
        dup = next((s for s in slides if (s["hash"] != h).sum() <= a.revisit_bits
                    and (np.abs(img - s["img"]) > 40).mean() < a.build_frac), None)
        if dup is not None:
            dup["revisits"].append(seg_start * step)
            last = {"img": img, "end": j, "ref": dup}
            continue
        # full-screen still (title card, full-screen slide) → don't crop it
        if j > seg_start and (rx, ry, rw, rh) != (0, 0, SW, SH):
            seg = frames[seg_start:j + 1]
            outside = np.ones((SH, SW), bool); outside[ry:ry + rh, rx:rx + rw] = False
            moving = np.abs(np.diff(seg, axis=0))[:, outside].mean()
            fullframe = moving < a.still and seg[len(seg) // 2][outside].std() >= a.min_detail
        else:
            fullframe = (rx, ry, rw, rh) == (0, 0, SW, SH)
        s = {"start": seg_start, "end": j, "mid": mid, "img": img, "hash": h, "revisits": [], "full": fullframe}
        slides.append(s)
        last = s
    # the "last" pointer may be a revisit wrapper; normalise ends
    slides.sort(key=lambda s: s["start"])
    print(f"{len(runs)} stable runs → {len(slides)} distinct slides", flush=True)

    out = os.path.abspath(a.out)
    os.makedirs(os.path.join(out, "slides"), exist_ok=True)
    os.makedirs(os.path.join(out, "frames"), exist_ok=True)
    tr = load_transcript(a.transcript)

    index = []
    for n, s in enumerate(slides, 1):
        t0, t1 = s["start"] * step, (s["end"] + 1) * step
        tmid = s["mid"] * step + step / 2
        name = f"slide_{n:03d}_{fmt(t0)}"
        full = os.path.join(out, "frames", name + "_full.jpg")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{tmid:.2f}", "-i", a.video,
                        "-frames:v", "1", "-q:v", "2", full], check=True)
        im = Image.open(full)
        (im if s["full"] else im.crop((cx, cy, cx + cw, cy + ch))).save(
            os.path.join(out, "slides", name + ".png"), optimize=True)
        # transcript spoken while the slide is up (until the next slide appears)
        t_next = slides[n]["start"] * step if n < len(slides) else dur
        said = " ".join(txt for (ts, txt) in tr if t0 - 1 <= ts < t_next)
        index.append({
            "n": n, "file": f"slides/{name}.png", "frame": f"frames/{name}_full.jpg",
            "start": round(t0, 1), "end": round(t1, 1), "start_clock": clock(t0),
            "revisits": [clock(r) for r in s["revisits"]],
            "cropped": not s["full"],
            "transcript": said,
        })
        print(f"  {n:3d}  {clock(t0):>7}–{clock(t1):<7} {name}.png", flush=True)

    # OCR (Apple Vision via compiled Swift helper) — exact slide wording
    pages = {}
    if a.no_ocr:
        pass
    elif sys.platform != "darwin":
        print("OCR skipped: the text-on-slide step uses Apple Vision and only runs on macOS "
              "(slides are still captured; read them with the Read tool)")
    else:
        here = os.path.dirname(os.path.abspath(__file__))
        binp = os.path.join(here, "ocr")
        if not os.path.exists(binp) and os.path.exists(binp + ".swift"):
            if shutil.which("swiftc"):
                print("compiling ocr.swift (first run only)…", flush=True)
                subprocess.run(["swiftc", "-O", binp + ".swift", "-o", binp], check=False)
            else:
                print("OCR skipped: swiftc not found (install Xcode Command Line Tools: xcode-select --install)")
        if os.path.exists(binp):
            paths = [os.path.join(out, e["file"]) for e in index]
            try:
                ocr = json.loads(subprocess.check_output([binp] + paths))
            except Exception as ex:
                ocr = {}; print(f"OCR failed: {ex}")
            for e, pth in zip(index, paths):
                e["ocr"] = ocr.get(pth, [])
                for line in e["ocr"]:
                    m = re.fullmatch(r"\s*(\d{1,3})\s*/\s*(\d{1,3})\s*", line)
                    if m and 0 < int(m.group(1)) <= int(m.group(2)) <= 300:
                        e["page"] = [int(m.group(1)), int(m.group(2))]
                        pages.setdefault(int(m.group(2)), set()).add(int(m.group(1)))
                        break
    coverage = None
    if pages:
        total = max(pages, key=lambda k: len(pages[k]))
        seen = pages[total]
        missing = [p for p in range(1, total + 1) if p not in seen]
        coverage = {"deck_pages": total, "pages_seen": sorted(seen), "missing": missing}
        print(f"deck page check: {len(seen)}/{total} numbered pages captured"
              + (f" — MISSING {missing}" if missing else " ✅"))

    meta = {"video": os.path.basename(a.video), "url": a.url, "resolution": [W, H],
            "duration_s": round(dur, 1), "crop": [cx, cy, cw, ch], "crop_source": region_src,
            "params": {k: getattr(a, k) for k in ("fps", "still", "change", "build_frac", "min_hold", "min_detail", "revisit_bits")},
            "page_coverage": coverage, "slides": index}
    json.dump(meta, open(os.path.join(out, "slides.json"), "w"), indent=2)

    vid = None
    if a.url:
        m = re.search(r"(?:youtu\.be/|v=)([\w-]{11})", a.url)
        vid = m.group(1) if m else None
    md = [f"# Slide index — {len(index)} slides", "",
          f"Source: {a.url or os.path.basename(a.video)} · {W}x{H} · crop {cx},{cy},{cw},{ch} ({region_src})", "",
          "Every distinct slide, in order, with what was said while it was on screen. "
          "Progressive builds are kept as separate slides. Revisits are listed, not re-saved.", ""]
    if coverage:
        md += [f"**Deck page check:** {len(coverage['pages_seen'])}/{coverage['deck_pages']} numbered pages captured"
               + (f" — missing {coverage['missing']} (unnumbered pages, e.g. a title slide, are normal)" if coverage["missing"] else " ✅"), ""]
    for e in index:
        link = f"https://youtu.be/{vid}?t={int(e['start'])}" if vid else None
        title = next((l for l in e.get("ocr", []) if len(l) > 3), "")
        pg = f" · page {e['page'][0]}/{e['page'][1]}" if e.get("page") else ""
        ts = f"[{e['start_clock']}]({link})" if link else e["start_clock"]
        head = f"## Slide {e['n']} — {ts}{pg}" + (f" — {title[:80]}" if title else "")
        md += [head, "", f"![Slide {e['n']}]({e['file']})", ""]
        if e["revisits"]:
            md += [f"*Shown again at {', '.join(e['revisits'])}*", ""]
        if e.get("ocr"):
            md += ["**Text on slide (OCR):**", "", "```text", *e["ocr"], "```", ""]
        if e["transcript"]:
            txt = e["transcript"]
            md += ["**Said while on screen:** " + (txt[:1200] + "…" if len(txt) > 1200 else txt), ""]
    open(os.path.join(out, "SLIDES.md"), "w").write("\n".join(md))

    # contact sheet
    if index:
        thumbs = [Image.open(os.path.join(out, e["file"])) for e in index]
        tw = 360
        th = int(tw * thumbs[0].height / thumbs[0].width)
        cols = 5
        rows = (len(thumbs) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * (tw + 8) + 8, rows * (th + 30) + 8), "white")
        from PIL import ImageDraw
        dr = ImageDraw.Draw(sheet)
        for k, (t, e) in enumerate(zip(thumbs, index)):
            x, y = 8 + (k % cols) * (tw + 8), 8 + (k // cols) * (th + 30)
            sheet.paste(t.convert("RGB").resize((tw, th)), (x, y))
            dr.text((x, y + th + 4), f"{e['n']}  {e['start_clock']}", fill="black")
        sheet.save(os.path.join(out, "contact_sheet.jpg"), quality=85)
    print(f"done → {out}")


if __name__ == "__main__":
    main()
