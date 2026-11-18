#!/usr/bin/env python3
"""
verify_guide_html.py — prove a built guide actually renders before you call it done.

Catches the failure that silently ruins guides: a `flowchart LR` whose natural width
is 2000-4000px gets scaled to fit a ~900px column and renders as an unreadable
39-pixel-tall smear. It does NOT throw an error, so it passes every static check.

Checks performed in a real headless browser:
  1. every ```mermaid fence produced an <svg>  (no silent parse failures)
  2. no diagram is wider than MAX_W px natural  (the legibility killer)
  3. every embedded <img> actually decoded
  4. the page body does not scroll horizontally

USAGE
    python3 verify_guide_html.py <output.html> [max_width]

Requires playwright:  pip3 install playwright && python3 -m playwright install chromium
If playwright is unavailable, falls back to static checks and says so.

FIXING A TOO-WIDE DIAGRAM
    * `flowchart LR` with >5 chained nodes  ->  `flowchart TB`
    * side-by-side subgraphs with many rows ->  drop the subgraphs, use paired rows
    * very long node labels                 ->  break with <br/>
"""

import os
import re
import sys

MAX_W = 1350
COLUMN_W = 900


def static_checks(path):
    s = open(path).read()
    return {
        "mermaid_blocks": s.count('<pre class="mermaid">'),
        "svg_figures": s.count('figure class="diag"'),
        "slide_figures": s.count('figure class="slide"'),
        "has_mermaid_js": "mermaid.initialize" in s,
        "bytes": len(s),
    }


def browser_checks(path, max_w):
    from playwright.sync_api import sync_playwright

    url = "file://" + os.path.abspath(path)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1080, "height": 900})
        pg.goto(url, wait_until="load")
        pg.wait_for_timeout(3500)
        data = pg.evaluate(
            """(maxW) => {
            const pres = [...document.querySelectorAll('pre.mermaid')];
            const unrendered = [], tooWide = [];
            pres.forEach((el, i) => {
                const svg = el.querySelector('svg');
                if (!svg) { unrendered.push(i); return; }
                const vb = (svg.getAttribute('viewBox') || '').split(' ');
                const w = Math.round(+vb[2] || 0), h = Math.round(+vb[3] || 0);
                if (w > maxW) tooWide.push({i, w, h});
            });
            const broken = [];
            [...document.querySelectorAll('figure.diag img, figure.slide img')].forEach((im, i) => {
                if (!im.naturalWidth) broken.push(i);
            });
            // an image the builder could not inline (missing file) is left as a relative src
            const unresolved = [...document.querySelectorAll('img')]
                .filter(im => !im.src.startsWith('data:')).map(im => im.getAttribute('src'));
            return {total: pres.length, unrendered, tooWide, broken, unresolved,
                    hScroll: document.body.scrollWidth > window.innerWidth + 2};
        }""",
            max_w,
        )
        b.close()
    return data


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    path = sys.argv[1]
    max_w = int(sys.argv[2]) if len(sys.argv) > 2 else MAX_W

    st = static_checks(path)
    print(f"📄 {os.path.basename(path)}  ({st['bytes']/1024/1024:.1f} MB)")
    print(f"   mermaid fences: {st['mermaid_blocks']}   embedded SVGs: {st['svg_figures']}"
          f"   slide images: {st['slide_figures']}")
    if not st["has_mermaid_js"]:
        print("   ❌ mermaid.js is not inlined — diagrams will not render")
        sys.exit(1)

    try:
        r = browser_checks(path, max_w)
    except Exception as e:
        print(f"   ⚠️  browser check skipped ({type(e).__name__}). Static checks only.")
        print("      pip3 install playwright && python3 -m playwright install chromium")
        sys.exit(0)

    ok = True
    if r["unrendered"]:
        ok = False
        print(f"   ❌ {len(r['unrendered'])} mermaid block(s) produced no SVG: {r['unrendered']}")
    else:
        print(f"   ✅ all {r['total']} mermaid diagrams rendered")

    if r["tooWide"]:
        ok = False
        print(f"   ❌ {len(r['tooWide'])} diagram(s) too wide (>{max_w}px) — will render illegibly:")
        for d in r["tooWide"]:
            scaled = round(d["h"] * COLUMN_W / d["w"])
            print(f"        block {d['i']}: {d['w']}x{d['h']}px  ->  renders only {scaled}px tall")
        print("      Fix: switch `flowchart LR` to `flowchart TB`, or drop side-by-side subgraphs.")
    else:
        print(f"   ✅ every diagram fits the column (<{max_w}px)")

    if r["broken"]:
        ok = False
        print(f"   ❌ {len(r['broken'])} embedded image(s) failed to decode: {r['broken']}")
    elif st["svg_figures"] or st["slide_figures"]:
        print(f"   ✅ all {st['svg_figures']} embedded SVGs + {st['slide_figures']} slide images decoded")

    if r["unresolved"]:
        ok = False
        print(f"   ❌ {len(r['unresolved'])} image(s) not inlined (file missing?): {r['unresolved'][:5]}")

    if r["hScroll"]:
        ok = False
        print("   ❌ page scrolls horizontally")
    else:
        print("   ✅ no horizontal overflow")

    print("\n" + ("✅ PASS — safe to ship" if ok else "❌ FAIL — fix the above before shipping"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
