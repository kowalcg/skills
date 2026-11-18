#!/usr/bin/env python3
"""
build_guide_html.py — turn a comprehensive guide .md into a self-contained HTML page.

Part of the video-to-skill package (gregkowalczyk.com/skills/video-to-skill/).

What it does:
  * renders ```mermaid fences as real diagrams (mermaid.js inlined — works offline)
  * inlines any ![alt](diagrams/*.svg) as base64 data URIs, wrapped in a dark figure card
  * inlines any ![alt](slides/*.png|jpg) — video slide captures from extract_slides.py —
    re-encoded as JPEG (max 1600px wide, q82) so 40 slides stay ~5 MB, in a light
    "slide" card; the alt text becomes the caption (put the timestamp in it)
  * light/dark aware, responsive, print-friendly
  * output is ONE file with zero external requests

USAGE
    python3 build_guide_html.py <guide.md> <output.html> ["Page Title"]

The .md may reference diagrams as `diagrams/<name>.svg` relative to the .md's folder.
Any SVG you place in a diagrams/ folder next to the .md is inlined.

MERMAID WIDTH RULE
    Wide `flowchart LR` diagrams get scaled down to illegibility in a ~900px column.
    Keep every diagram under ~1350px natural width. If a chain has more than ~5 nodes,
    use `flowchart TB`. Verify with verify_guide_html.py after building.
"""

import base64
import html as _h
import os
import re
import sys
import urllib.request

MERMAID_CDN = "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"
MERMAID_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mermaid.min.js")

CSS = """
:root{--bg:#ffffff;--fg:#1a1d23;--dim:#5b6472;--line:#e3e6ea;--card:#f7f8fa;
--acc:#c2410c;--acc2:#0369a1;--code:#f1f3f5;--quote:#fff8ed;--quoteb:#f59e0b;}
@media (prefers-color-scheme:dark){:root{--bg:#0f1218;--fg:#e6e9ef;--dim:#9aa3b5;--line:#252b36;
--card:#161b24;--acc:#fb923c;--acc2:#38bdf8;--code:#1a1f29;--quote:#1c1a12;--quoteb:#a16207;}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
font:16px/1.72 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,sans-serif;-webkit-font-smoothing:antialiased;}
.wrap{max-width:960px;margin:0 auto;padding:48px 28px 120px;}
h1{font-size:2.35rem;line-height:1.15;letter-spacing:-.02em;margin:0 0 .3em;
border-bottom:4px solid var(--acc);padding-bottom:.35em;}
h1+h2{border:none;color:var(--dim);font-weight:500;margin-top:0;font-size:1.15rem;}
h2{font-size:1.55rem;letter-spacing:-.01em;margin:2.6em 0 .7em;padding-bottom:.3em;border-bottom:1px solid var(--line);}
h3{font-size:1.18rem;margin:2em 0 .5em;color:var(--acc2);}
a{color:var(--acc2);text-decoration:none;border-bottom:1px solid transparent}
a:hover{border-bottom-color:var(--acc2)}
code{background:var(--code);padding:.12em .42em;border-radius:4px;
font:.87em ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;}
pre{background:var(--code);padding:16px 18px;border-radius:10px;overflow-x:auto;border:1px solid var(--line);}
pre code{background:none;padding:0;font-size:.85rem;line-height:1.6}
blockquote{margin:1.4em 0;padding:.85em 1.2em;background:var(--quote);
border-left:4px solid var(--quoteb);border-radius:0 8px 8px 0;}
blockquote p{margin:.4em 0}
table{border-collapse:collapse;width:100%;margin:1.3em 0;font-size:.93rem;display:block;overflow-x:auto;}
th,td{border:1px solid var(--line);padding:9px 13px;text-align:left;vertical-align:top}
th{background:var(--card);font-weight:650;white-space:nowrap}
tbody tr:nth-child(even){background:var(--card)}
hr{border:0;border-top:1px solid var(--line);margin:2.6em 0}
ul,ol{padding-left:1.4em} li{margin:.3em 0}
input[type=checkbox]{margin-right:.5em}
figure.diag{margin:1.8em 0;padding:0;background:#0f1218;border:1px solid var(--line);
border-radius:14px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,.18);}
figure.diag img{display:block;width:100%;height:auto}
figure.slide{margin:1.6em 0;padding:0;background:#fff;border:1px solid var(--line);
border-radius:12px;overflow:hidden;box-shadow:0 3px 14px rgba(0,0,0,.12);}
figure.slide img{display:block;width:100%;height:auto}
figure.slide figcaption{padding:8px 14px;font-size:.8rem;color:var(--dim);background:var(--card);border-top:1px solid var(--line);}
figure.diag figcaption{padding:10px 16px;font-size:.8rem;color:#9aa3b5;background:#0b0e13;border-top:1px solid #252b36;}
figure.diag figcaption code{background:#1a1f29;color:#c9d1e0}
/* Mermaid renders on a fixed light card in BOTH page themes. The house palette
   (GUIDE-STANDARD.md §1) is built from light pastel fills, so node text must stay
   dark — a dark-theme mermaid puts light text on those light fills and the diagram
   becomes unreadable. Keep the surface light and the text dark, always. */
pre.mermaid{background:#fbfcfe;border:1px solid var(--line);border-radius:12px;
padding:26px 22px;text-align:center;overflow-x:auto}
pre.mermaid .nodeLabel,pre.mermaid .edgeLabel,pre.mermaid .cluster-label,
pre.mermaid .titleText,pre.mermaid text{color:#0f172a}
pre.mermaid .edgeLabel{background:#fbfcfe}
pre.mermaid .edgeLabel rect{fill:#fbfcfe!important;opacity:1!important}
sub{color:var(--dim);font-size:.8rem}
@media(max-width:640px){.wrap{padding:28px 16px 80px}h1{font-size:1.8rem}}
@media print{figure.diag,figure.slide,pre.mermaid{break-inside:avoid}}
/* Print/PDF fix: `overflow-x:auto` on table is a screen-only affordance (drag to scroll a
   wide table). There is no scrolling in a printed page, so any table wider than the page
   just gets silently clipped at the right edge — the content is still there, you just can't
   see or select it. In print, force the table back into normal table layout and let cells
   wrap instead of overflowing. */
@media print{
  table{display:table;table-layout:fixed;overflow-x:visible;font-size:.8rem}
  th,td{white-space:normal;overflow-wrap:anywhere;word-break:break-word}
  pre{overflow-x:visible;white-space:pre-wrap;word-break:break-word}
}
"""


def _mermaid_js():
    if not os.path.exists(MERMAID_CACHE):
        os.makedirs(os.path.dirname(MERMAID_CACHE), exist_ok=True)
        urllib.request.urlretrieve(MERMAID_CDN, MERMAID_CACHE)
    return open(MERMAID_CACHE).read()


def _inside(base, rel):
    """Resolve rel under base; None if it escapes the guide folder (../, absolute, symlink)."""
    root = os.path.realpath(base)
    fp = os.path.realpath(os.path.join(root, rel))
    return fp if fp.startswith(root + os.sep) else None


def build(md_path, out_path, title=None):
    import markdown

    base = os.path.dirname(os.path.abspath(md_path))
    src = open(md_path).read()

    # 1. stash mermaid fences so the markdown converter leaves them alone
    mer = []

    def stash(m):
        mer.append(m.group(1))
        return f"\n@@MERMAID{len(mer) - 1}@@\n"

    src = re.sub(r"```mermaid\n(.*?)\n```", stash, src, flags=re.S)

    # 2. inline local SVGs as data URIs
    def embed(m):
        alt, rel = m.group(1), m.group(2)
        fp = _inside(base, rel)
        if not fp or not os.path.exists(fp):
            return m.group(0)
        # An SVG with an embedded font can be >1 MB. If a same-named .png twin sits next to
        # it, use that when the SVG is heavy — the guide stays small.
        png = fp[:-4] + ".png"
        if os.path.getsize(fp) > 400_000 and os.path.exists(png):
            b64, mime = base64.b64encode(open(png, "rb").read()).decode(), "image/png"
        else:
            b64, mime = base64.b64encode(open(fp, "rb").read()).decode(), "image/svg+xml"
        slug = os.path.basename(rel).rsplit(".", 1)[0]
        return (f'<figure class="diag"><img src="data:{mime};base64,{b64}" '
                f'alt="{_h.escape(alt)}"><figcaption>{_h.escape(alt)} &middot; source: '
                f'<code>diagrams/{slug}.svg</code></figcaption></figure>')

    src = re.sub(r"!\[([^\]]*)\]\((diagrams/[^)]+\.svg)\)", embed, src)

    # 2b. inline video slide captures (raster) as compressed JPEG
    def embed_slide(m):
        alt, rel = m.group(1), m.group(2)
        fp = _inside(base, rel)
        if not fp or not os.path.exists(fp):
            return m.group(0)
        import io
        try:
            from PIL import Image
        except ImportError:
            sys.exit("Slide images need Pillow:  pip3 install Pillow")
        im = Image.open(fp).convert("RGB")
        if im.width > 1600:
            im = im.resize((1600, int(im.height * 1600 / im.width)), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=82, optimize=True)
        b64 = base64.b64encode(buf.getvalue()).decode()
        return (f'<figure class="slide"><img src="data:image/jpeg;base64,{b64}" '
                f'alt="{_h.escape(alt)}"><figcaption>{_h.escape(alt)}</figcaption></figure>')

    # also accepts one parent folder (e.g. claire-vo/slides/…) for a second video in the same folder
    src = re.sub(r"!\[([^\]]*)\]\(((?:[\w.-]+/)?slides/[^)]+\.(?:png|jpe?g))\)", embed_slide, src)

    body = markdown.markdown(src, extensions=["extra", "tables", "toc", "sane_lists", "attr_list"])

    # 3. restore mermaid
    for i, code in enumerate(mer):
        tag = f'<pre class="mermaid">{_h.escape(code)}</pre>'
        body = body.replace(f"<p>@@MERMAID{i}@@</p>", tag).replace(f"@@MERMAID{i}@@", tag)

    if not title:
        m = re.search(r"^#\s+(.+)$", open(md_path).read(), re.M)
        title = m.group(1).strip() if m else os.path.basename(md_path)

    out = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_h.escape(title)}</title>
<style>{CSS}</style></head>
<body><div class="wrap">
{body}
</div>
<script>{_mermaid_js()}</script>
<script>
(function(){{
  // Always 'base' with an explicit light-fill / dark-text palette — never mermaid's
  // 'dark' theme. The house palette styles nodes with light pastel fills; the dark
  // theme pairs those with light text, which renders as unreadable low-contrast mush.
  // The diagram sits on its own light card (see pre.mermaid in CSS) in both themes.
  mermaid.initialize({{startOnLoad:true, theme:'base', securityLevel:'loose',
    themeVariables:{{
      background:'#fbfcfe',
      primaryColor:'#eef2f7', primaryBorderColor:'#94a3b8', primaryTextColor:'#0f172a',
      secondaryColor:'#e2e8f0', tertiaryColor:'#f8fafc',
      mainBkg:'#eef2f7', nodeBorder:'#94a3b8', nodeTextColor:'#0f172a',
      textColor:'#0f172a', lineColor:'#5b6b80',
      edgeLabelBackground:'#fbfcfe',
      clusterBkg:'#f5f8fc', clusterBorder:'#cbd5e1',
      titleColor:'#0f172a', fontSize:'15px',
      fontFamily:'ui-sans-serif,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif'
    }},
    flowchart:{{curve:'basis', useMaxWidth:true, htmlLabels:true, padding:14}},
    gantt:{{useMaxWidth:true}}, sequence:{{useMaxWidth:true}}}});
}})();
// Print/PDF fix: an SVG (mermaid diagram or embedded diagram image) is an atomic,
// non-fragmentable element to the browser's print/PDF paginator. When one is taller than a
// single printed page, the paginator can't split it — it defers the whole thing to a fresh
// page, but the empty space its own container already claimed on the PRIOR page renders as
// a fully blank page (this happens regardless of any break-inside CSS, which only governs
// *fragmentable* boxes). The only real fix is to make sure no diagram is taller than one
// page in the first place: shrink the SVG in place (viewBox keeps it proportional) so its
// container always fits within a single page's content height.
(function(){{
  var PAGE_BUDGET = 780; // px — safely under one A4 page's content height at 20mm margins
  function shrinkOversized(){{
    document.querySelectorAll('pre.mermaid svg').forEach(function(svg){{
      var h = svg.getBoundingClientRect().height;
      if (h > PAGE_BUDGET && !svg.dataset.shrunk) {{
        svg.style.height = PAGE_BUDGET + 'px';
        svg.style.width = 'auto';
        svg.style.maxWidth = '100%';
        svg.dataset.shrunk = '1';
      }}
    }});
    document.querySelectorAll('figure.diag img').forEach(function(img){{
      var h = img.getBoundingClientRect().height;
      if (h > PAGE_BUDGET && !img.dataset.shrunk) {{
        img.style.height = PAGE_BUDGET + 'px';
        img.style.width = 'auto';
        img.style.maxWidth = '100%';
        img.style.margin = '0 auto';
        img.dataset.shrunk = '1';
      }}
    }});
  }}
  var mo = new MutationObserver(shrinkOversized);
  mo.observe(document.body, {{childList:true, subtree:true}});
  window.addEventListener('load', function(){{
    setTimeout(function(){{ shrinkOversized(); window.__pdfReady = true; }}, 1200);
  }});
}})();
</script></body></html>"""

    open(out_path, "w").write(out)
    return {"bytes": len(out), "mermaid": len(mer), "svgs": out.count('figure class="diag"')}


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    r = build(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    print(f"✅ {sys.argv[2]}")
    print(f"   {r['bytes']/1024/1024:.1f} MB · {r['mermaid']} mermaid · {r['svgs']} embedded SVG")
    print("   ⚠️  Now run verify_guide_html.py to catch over-wide diagrams.")
