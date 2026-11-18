# Guide Standard — comprehensive, visual, self-contained

The standard every guide produced by `video-to-skill` follows.

## The three non-negotiables

1. **Comprehensive.** A reference document, not a summary. 8,000–12,000 words for a full methodology; proportionally less for a short talk.
2. **Visual.** Diagrams carry the structure, prose carries the nuance. 8–20 Mermaid diagrams per guide.
3. **One self-contained HTML file.** Opens from any folder, works offline, makes no external requests.

---

## 1. Diagrams

Write diagrams inline in the `.md` as fenced blocks:

    ```mermaid
    flowchart TB
      A["Input"] --> B["The important step"] --> C["Output"]
      style B fill:#fff4e5,stroke:#f59e0b
      style C fill:#dcfce7,stroke:#22c55e
    ```

**Types worth using:** `flowchart TB` (default) · `sequenceDiagram` (before/after contrasts) · `gantt` (parallel work over time) · `flowchart LR` (short chains only, see the width rule) · `quadrantChart` (two-axis comparisons) · `timeline` (history of a method or tool).

### The width rule, the one that silently ruins guides

A guide column is about 900px. A `flowchart LR` with 9 nodes has a natural width of 2,000–4,000px. Mermaid scales it down to fit and produces a 39-pixel-tall unreadable smear, with no error. It passes every static check.

**Keep every diagram under 1350px natural width.**

| Symptom | Fix |
|---|---|
| `flowchart LR` with more than 5 chained nodes | Switch to `flowchart TB` |
| Side-by-side subgraphs with many rows each | Drop the subgraphs; use paired rows (`R1 --> G1`, `R2 --> G2`) |
| A row of 5+ sibling nodes fanning out | Group them into 2–3 nodes with `&middot;` separators |
| Very long node labels | Break with `<br/>` |

`scripts/verify_guide_html.py` catches this. Run it every time.

### Authoring notes
- Use HTML entities (`&middot;` `&mdash;` `&#9654;`) rather than raw Unicode in labels
- `<b>`, `<i>`, `<br/>`, `<code>` all work inside `["..."]` labels
- Every node needs a real edge. No floating boxes.
- Style the key nodes with the palette below. Never leave a diagram all grey.

### The palette

| Meaning | Fill | Stroke |
|---|---|---|
| Input / neutral | `#e8f0fe` | `#4285f4` |
| The important thing | `#fff4e5` | `#f59e0b` |
| Success / output / free | `#dcfce7` | `#22c55e` |
| Warning / failure / cost | `#fee2e2` | `#dc2626` |
| Secondary accent | `#fce8f3` | `#d946ef` |
| Note / aside (`stroke-dasharray: 4 4`) | `#fffbeb` | `#f59e0b` |

Optional: any `.svg` you place in a `diagrams/` folder next to the `.md` and reference as `![Caption](diagrams/name.svg)` is inlined into the HTML.

---

## 2. Guide structure

```
# Title
## Subtitle — what this is

Source · Speaker · Date · Prepared with video-to-skill

> Framing note: why this guide exists in this shape

## Table of Contents          ← grouped into Parts, anchor-linked

# PART I — ORIENTATION
  Who the speaker is, what they claim, why it matters
  ⚑ "What changed since this was recorded"   ← mandatory for any source over a month old

# PART II–N — THE CONTENT
  One section per framework. Each: what it is → verbatim quotes → diagram → how to apply

# PART — APPLICATION
  Applying this in your business  (table: their tool | what it costs | free or cheaper alternative | what you give up)
  Evaluation checklist            ← checkboxes; every "no" is a to-do
  Common mistakes                 ← table: ❌ Mistake | ✅ Fix | § reference
  First-week plan                 ← literally Day 1–5, using tools that exist today
  Key quotes
  Sources and verification        ← including anything you could NOT verify
```

### Writing rules
- **Quote verbatim and often.** The speaker's own words carry more than paraphrase. Bold the operative clause.
- **Every named example gets:** what it was → what the alternative was → what the outcome was.
- **Report honestly.** If the speaker's result was mediocre, say so.
- **Flag what is now out of date.** Never present months-old tool advice as current without checking.
- **Say what you could not verify.** A "noted as unverified" line is worth more than false confidence.
- **Make it applicable.** Every tool the speaker uses gets its cost and a cheaper or free alternative.

---

## 3. Slide-by-slide guides (when the video shows slides)

When `scripts/extract_slides.py` found a deck, a screen-share, a whiteboard or on-screen documents,
**Part II of the guide is the deck**, one section per page, in the order shown:

1. **Screenshot(s)**: every build or hover state that adds information, captioned
   `Slide N/M (build|final|hover): short title · MM:SS`.
   Path: `![…](slides/slides/slide_NNN_MMmSSs.png)` relative to the `.md` (or `slides/cards/card_NN_….png`).
2. **On the slide (verbatim)**: every word, including footers, legends and footnotes. Grids become
   tables. Never guess an unreadable logo or number; describe it instead ("green 'P' logo").
3. **What it means, step by step**: numbered; explain *why* each element is on the slide.
4. **What the speaker said**: verbatim quotes from the transcript while it was on screen
   (`slides/SLIDES.md` has them pre-attached to each slide).
5. **Rebuilt diagram**: the slide's logic redrawn as a Mermaid diagram in the palette above. This is
   what makes the idea reusable in your own decks and documents.
6. **Applying it in your business**: what this page means for a small business, with the tool,
   its cost and a cheaper alternative where relevant.

Also: label every client example with the slide's own provenance tag ("names and figures changed",
"composite / illustrative"), and put non-deck captures (cold open, sponsor segment) in an appendix.

**Size:** the builder inlines slides as JPEG (at most 1600px wide, quality 82, about 190 KB each),
so a 40-slide guide stays around 8 MB and still opens offline from one file.

## 4. Build and verify, both steps, always

```bash
# 1. build the HTML (one file, mermaid.js inlined, works offline)
python3 "$SKILL_DIR/scripts/build_guide_html.py" "<OUT>/<topic>-guide.md" "<OUT>/<topic>-guide.html"

# 2. verify, never skip
python3 "$SKILL_DIR/scripts/verify_guide_html.py" "<OUT>/<topic>-guide.html"
```

Verification must print **✅ PASS** before the guide is reported done. With Playwright installed it checks in a real browser: every mermaid fence rendered, no diagram over-wide, every embedded image decoded (diagrams and slides), no image left un-inlined, no horizontal overflow. Without Playwright it runs static checks and tells you so.

---

## 5. File placement

Everything goes in `~/Downloads/Video Skills/<Topic Title>/`:

| File | Purpose |
|---|---|
| `<topic>-guide.html` | The guide. The thing you open. |
| `<topic>-guide.md` | Same guide as Markdown, for editing or pasting into Notion, Docs, a wiki |
| `transcript.txt` | Full transcript |
| `transcript-timestamped.txt` | Same transcript with `[MM:SS]` stamps (YouTube), used to attach speech to slides |
| `slides/` | Every distinct slide as PNG, `SLIDES.md` index with on-slide text and what was said, `contact_sheet.jpg` overview |
| `SKILL.md` | The Claude skill (Full Skill mode), also installed at `~/.claude/skills/<topic-slug>/` |
| `README.md` | What is in the folder and how to use the skill |
