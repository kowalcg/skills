---
name: video-to-skill
description: Use when turning a YouTube video, podcast, talk, webinar, or audio file into a comprehensive written guide with diagrams and, optionally, a reusable Claude skill. Triggers on "video to skill", "learn from this video", "make a guide from this video", "summarize this video", "turn this podcast into a guide", "make a skill from this".
---

# Video-to-Skill

Turn any video, podcast or talk into a comprehensive, visual guide you can actually use in
your business, and optionally into a reusable Claude skill that applies what the expert taught.

**Usage:** `/video-to-skill [YouTube URL, podcast URL, audio URL, or local audio/video file]`

**Supported inputs**
- YouTube URL: transcript fetched from YouTube's captions with `scripts/get_transcript.py`
- Podcast page URL: find the MP3 on the page, download it, transcribe with Whisper
- Direct MP3 / M4A / WAV URL: download and transcribe with Whisper
- Local file (`.mp3`, `.m4a`, `.mp4`, `.mov`): transcribe with Whisper
- Facebook, Vimeo, TikTok, Instagram video URL: download audio with `yt-dlp`, transcribe with Whisper

**Everything this skill produces lands in one folder:**
`~/Downloads/Video Skills/[Topic Title]/`

No other folder on the machine is touched, except when the user chooses "Full Skill", in which
case the finished skill is also installed to `~/.claude/skills/[topic-slug]/SKILL.md` so Claude
can use it in future sessions. Always tell the user before installing anything.

---

## What this produces

| Mode | Output |
|---|---|
| **Full Skill** (default) | `transcript.txt` + `slides/` + `[topic]-guide.md` + `[topic]-guide.html` + `SKILL.md` + `README.md`, and the skill installed for Claude |
| **Guide Only** | `transcript.txt` + `slides/` + `[topic]-guide.md` + `[topic]-guide.html` + `README.md` |
| **Quick Summary** | A written summary in the chat. Nothing saved. |

> **Slides are captured on every YouTube run (Step 2b).** If the video shows slides, a screen-share,
> a deck, a whiteboard or on-screen documents, every distinct one is saved as a full-resolution PNG
> together with what was said while it was up (and, on macOS, the exact text on it). The guide is
> then built *from the slides*, page by page, so the numbers, labels and diagrams are the speaker's
> own rather than a paraphrase.

---

## The process

### Step 0: Ask what's needed

Before doing anything, ask:

> **What do you need from this video?**
> 1. **Full Skill** — transcript + comprehensive visual guide + a reusable Claude skill that applies the method *(default: use for a methodology you'll apply repeatedly)*
> 2. **Guide Only** — transcript + comprehensive visual guide *(use for training material, SOPs, reference docs, one-time learning)*
> 3. **Quick Summary** — key points in the chat, nothing saved *(use when you only need to know what's in it)*

If the user gives a URL with no other context, default to **Full Skill**.

- Full Skill: all steps
- Guide Only: Steps 1–5 (including 2b), then Step 8
- Quick Summary: Step 2 only, then summarize in the chat (no slide capture)

### Step 1: Create the output folder

```bash
mkdir -p ~/Downloads/"Video Skills"/"[Topic Title]"
```

`[Topic Title]` is Title Case, 3–7 words, describing the topic rather than the video title.
Example: `~/Downloads/Video Skills/Email Copywriting That Converts/`

Refer to this as `[OUT]` for the rest of the process.

### Step 2: Get the transcript, save to `[OUT]/transcript.txt`

Detect the input type first.

**YouTube URL** (captions available, which is most videos):
```bash
python3 "$SKILL_DIR/scripts/get_transcript.py" "[URL]" --output "[OUT]/transcript.txt"
```
`$SKILL_DIR` is the folder this SKILL.md lives in, normally `~/.claude/skills/video-to-skill`.
The script installs `youtube-transcript-api` on first run if it is missing.

**YouTube URL with no captions, or Facebook / Vimeo / TikTok / Instagram:**
```bash
yt-dlp -x --audio-format mp3 -o "[OUT]/source-audio.%(ext)s" "[URL]"
```
then transcribe (below). If `yt-dlp` is missing: `brew install yt-dlp` on macOS, `pip3 install yt-dlp` elsewhere.

**Podcast page URL with no direct MP3:** fetch the page (WebFetch) and ask for "any audio file URL (MP3, M4A) on this page", then treat it as a direct audio URL.

**Direct audio URL:**
```bash
curl -L "[AUDIO_URL]" -o "[OUT]/source-audio.mp3"
```

**Transcribe any audio or local file with Whisper (runs locally, no API key):**
```bash
whisper "[OUT]/source-audio.mp3" --model base --output_format txt --output_dir "[OUT]"
mv "[OUT]/source-audio.txt" "[OUT]/transcript.txt"
```
If `whisper` is not on the PATH, try `python3 -m whisper` and, failing that, tell the user how to install it:
```bash
brew install ffmpeg          # macOS; on Windows/Linux install ffmpeg from ffmpeg.org
pip3 install openai-whisper
```
`base` is fast and accurate enough for clear spoken English. Use `small` or `medium` for heavy
accents or technical jargon. A one-hour episode takes a few minutes on `base`.

**If no transcript can be obtained at all:** say so plainly, then build the guide from the video
description, any published show notes, and web research. Mark the guide "transcript unavailable"
at the top. Never invent quotes.

### Step 2b: Capture every slide, save to `[OUT]/slides/`

**Run this on every YouTube video** (and on any local video file). It takes about a minute per
hour of video and is the only reliable way to get the exact numbers, labels and diagrams: the
transcript paraphrases them, and rebuilding them from memory gets them wrong. If the video has no
slides, the script finds none (or a handful of scene stills) and you move on.

Needs `ffmpeg` plus the Python packages `numpy` and `Pillow`. If any is missing, tell the user
how to install it (README "Install"), or ask whether to continue without slides.

```bash
# 1. timestamped transcript, used to attach "what was said" to each slide
python3 "$SKILL_DIR/scripts/get_transcript.py" "[URL]" --timestamps --output "[OUT]/transcript-timestamped.txt"

# 2. download the video track only, best quality up to 1080p (a stale yt-dlp gets HTTP 403: update it first)
yt-dlp -U 2>/dev/null || true
yt-dlp -f "bestvideo[height<=1080][ext=mp4]/bestvideo[height<=1080]/best[height<=1080]" -o "[OUT]/source-video.%(ext)s" "[URL]"

# 3. extract every distinct slide (auto-detects the slide panel next to a webcam strip)
python3 "$SKILL_DIR/scripts/extract_slides.py" "[OUT]/source-video.mp4" \
  --out "[OUT]/slides" --transcript "[OUT]/transcript-timestamped.txt" --url "[URL]"
```

For a local video file, skip steps 1 and 2 and point step 3 at the file (no `--transcript` means
slides are indexed without the spoken text; if Whisper produced a `.srt` or `.vtt` you can convert
it to `[MM:SS] text` lines and pass that). When done, delete `source-video.mp4` unless the user
wants it: it is about 0.5 GB per hour.

**What you get in `[OUT]/slides/`:**

| File | What it is |
|---|---|
| `slides/slide_NNN_MMmSSs.png` | Each distinct slide, full resolution, cropped to the slide panel (full frame for full-screen stills) |
| `frames/slide_NNN_MMmSSs_full.jpg` | The whole frame including the webcam, for context |
| `SLIDES.md` | Index: image + clickable timestamp + page number + text on the slide (macOS) + what was said while it was on screen |
| `slides.json` | The same, machine-readable (crop box, revisits, page coverage) |
| `contact_sheet.jpg` | Every slide on one page. Read this first to see the shape of the deck |

**What the script handles:** a webcam strip or side-by-side layout (the slide region is found from
the pixels that stay still most of the time) · progressive builds (a new capture when 0.8% or more
of the pixels change and stay changed for 2 seconds) · hover tooltips held for 2 seconds or more ·
revisits (the presenter flips back: recorded against the first capture, not saved twice) ·
full-screen title cards (not cropped) · a completeness check when slides carry "N / M" page
numbers (`deck page check: 16/16 ✅`; missing pages are listed so you can look at those timestamps).

**Text on slides (OCR):** on macOS the script compiles `scripts/ocr.swift` on first run (needs the
Xcode Command Line Tools: `xcode-select --install`) and reads every slide with Apple Vision. On
Windows and Linux the slides are still captured; read them with the Read tool instead.

**If the region came out as about 100% of the frame and there are far more captures than slides**
(a talking-head video with editor-made graphic cards over it: every head movement re-captures the
same card), collapse them:

```bash
python3 "$SKILL_DIR/scripts/pick_best_cards.py" "[OUT]/slides" --url "[URL]"
```

It groups captures by each card's headline and keeps the most complete version, writing
`slides/cards/card_NN_MMmSSs.png`, `slides/CARDS.md` and `slides/cards_sheet.jpg`. Reference those in
the guide as `slides/cards/….png`. Such cards are usually the **editor's summaries, not the speaker's
own slides**: check their wording against the transcript and flag any line the speaker did not say.
(Needs OCR, so macOS only; elsewhere pick the best captures by reading `contact_sheet.jpg`.)

**Then, before writing anything:**
1. Read `contact_sheet.jpg` to see the deck's shape (what is deck, cold open, sponsor segment).
2. **Read every deck slide at full resolution** with the Read tool (about 1.5k tokens each; a
   16-page deck is 25–40 captures). This is the point of the exercise. OCR text is a backup for
   exact wording, not a substitute for looking.
3. Watch for footer cues like "→ for more" (an unfinished build): if the final build is missing, find it.
4. Never name a logo, brand or number you cannot actually read. Describe it instead.

**Tuning flags** (rarely needed): `--crop x,y,w,h` (force the region) · `--min-hold 1.5` (faster
decks) · `--build-frac 0.005` (subtler builds) · `--change 4` (noisier video) · `--no-ocr`.

### Step 3: Research the speaker and the topic

Use web search (WebSearch / WebFetch) to establish:
- Who the speaker is: background, credentials, track record, published work
- Named frameworks or books they are known for
- Supplementary frameworks on the same topic from other credible sources
- Additional named examples beyond the ones in the video
- Any criticism or counterpoints worth noting
- **What changed since the video was recorded** (product updates, pricing, new features). For anything about AI tools or software, assume a video older than a month is partly out of date and check.

Keep a list of every source URL you used. It goes in the guide.

### Step 4: Analyze the transcript for teachable structure

Extract:
- **Core frameworks**: named or unnamed systems the speaker uses
- **Step-by-step processes**: sequences that can be replicated
- **Principles**: the "why" behind the tactics
- **Named examples**: specific case studies with outcomes
- **Quotes**: verbatim lines worth preserving
- **Mistakes and anti-patterns**: what not to do
- **Tools and resources** mentioned

### Step 5: Write the guide, then build and verify the HTML

> Read `$SKILL_DIR/GUIDE-STANDARD.md` before writing. It defines the structure, the diagram
> rules and the build/verify steps.

> **When slides were captured, build the guide slide by slide** (GUIDE-STANDARD.md §3). For each
> deck page: the screenshot(s) `![Slide N/M: title · MM:SS](slides/slides/slide_….png)` → every word
> on it transcribed (tables for grids) → what it means, step by step → what the speaker said while
> it was up (verbatim) → the slide's logic rebuilt as a Mermaid diagram → how to apply it in a
> business. The builder inlines the PNGs as compressed JPEG and the verifier checks every one decoded.

File: `[OUT]/[topic]-guide.md`

Structure (full version in GUIDE-STANDARD.md):

```markdown
# [Title]
## [Speaker] on [Source]

Source · Speaker · Guide created · Prepared with video-to-skill

> Framing note: why this guide exists in this shape

## Table of Contents          ← grouped into Parts, anchor-linked

# PART I — ORIENTATION
1. Who is [Speaker], and why listen
2. The central claim
3. What changed since this was recorded    ← mandatory if the source is over a month old

# PART II … N — THE CONTENT
   One section per framework: what it is → verbatim quotes → diagram → how to apply

# PART — APPLICATION
   Applying this in your business   ← their tool | what it costs | a free or cheaper alternative | what you give up
   Evaluation checklist             ← checkboxes; every "no" is a to-do
   Common mistakes                  ← ❌ Mistake | ✅ Fix | § reference
   First-week plan                  ← Day 1–5, using only tools that exist today
   Key quotes
   Sources and verification         ← including what you could NOT verify
```

**Quality bar:** a reference document, not a summary. 8,000–12,000 words for a full methodology,
proportionally shorter for a short talk. Quote verbatim and often, bolding the operative clause.
Report results honestly. Flag anything now out of date.

**Diagrams are mandatory.** 8–20 Mermaid diagrams per guide, inline in the `.md` as
```` ```mermaid ```` fences: concepts, processes, comparisons, timelines. `flowchart TB` by
default. Style key nodes with the palette in GUIDE-STANDARD.md. Never ship an all-grey diagram.

> **The width rule.** A `flowchart LR` with more than about 5 chained nodes renders as an
> unreadable smear in a 900px column and throws no error. Keep every diagram under 1350px
> natural width. Use `flowchart TB`. The verifier catches violations.

**Build the HTML** (one self-contained file, works offline, opens anywhere):
```bash
python3 "$SKILL_DIR/scripts/build_guide_html.py" "[OUT]/[topic]-guide.md" "[OUT]/[topic]-guide.html"
```
Requires the `markdown` package (`pip3 install markdown`), plus `Pillow` when the guide contains slides.

**Verify it** (never skip):
```bash
python3 "$SKILL_DIR/scripts/verify_guide_html.py" "[OUT]/[topic]-guide.html"
```
It must print **✅ PASS** before you tell the user the guide is done. With Playwright installed
it renders the page in a real browser and checks every diagram; without it, it runs static
checks and says so. To get the full check: `pip3 install playwright && python3 -m playwright install chromium`.

### Step 6: Write the skill (Full Skill only)

File: `[OUT]/SKILL.md`

**The skill encodes the method, not the content.** It tells Claude how to apply the expert's
framework when helping with a real task.

```markdown
---
name: [topic-slug]
description: Use when [specific triggering situations]. Triggers on "[phrase 1]", "[phrase 2]", "[phrase 3]".
---

# [Title] — [Speaker]'s method

[One line: what this skill enables]

**Full guide:** ~/Downloads/Video Skills/[Topic Title]/[topic]-guide.html

## [Core step 1]
[Actionable instructions]

## [Core step 2]
…

## Quick reference
[Table of the key frameworks and rules]

## Common mistakes
[Table: Mistake → Fix]
```

Rules: the description says **when** to use it, not what it does. Each section is one
actionable step. Include the named examples as quick reference. Keep it under 300 lines and
link to the guide for depth.

### Step 7: Install the skill (Full Skill only)

Tell the user what you are about to do, then:
```bash
mkdir -p ~/.claude/skills/[topic-slug]
cp "[OUT]/SKILL.md" ~/.claude/skills/[topic-slug]/SKILL.md
```
The skill is available in the next Claude Code session as `/[topic-slug]` and by its trigger phrases.

### Step 8: Write the README and deliver

File: `[OUT]/README.md`

```markdown
# [Title]

**Speaker:** [Name]
**Source:** [Title / URL]
**Created:** [Date]

## What's in this folder
| File | Purpose |
|---|---|
| `[topic]-guide.html` | The guide. Open this. Works offline. |
| `[topic]-guide.md` | The same guide as Markdown, for editing or pasting elsewhere |
| `transcript.txt` | The full transcript |
| `slides/` | Every slide shown in the video, with `SLIDES.md` as the index (when the video had slides) |
| `SKILL.md` | The Claude skill (Full Skill only). Installed at `~/.claude/skills/[topic-slug]/` |

## How to use the skill
Say "[trigger phrase]" or type `/[topic-slug]` in Claude Code.

## The method in five lines
- …
```

Then report to the user:

```
## ✅ Done: [Title]

**Speaker:** [Name]   **Source:** [URL]

**What was learned**
- [Framework 1]
- [Framework 2]
- [Key insight]

**Files** (~/Downloads/Video Skills/[Topic Title]/)
- [topic]-guide.html   ← open this
- [topic]-guide.md
- transcript.txt
- slides/   ← [X] slides captured, deck page check [n/m] (SLIDES.md is the index)
- SKILL.md + README.md (Full Skill only)

**Skill installed:** ~/.claude/skills/[topic-slug]/  — say "[trigger phrase]" or type /[topic-slug]
```

---

## Quality standards

- Every slide captured and read (Step 2b): the deck page check passes, or the gap is explained
- The guide is comprehensive: a reference document, not a summary
- Visual by default: 8–20 Mermaid diagrams, none over 1350px wide, `flowchart TB` unless the chain is 5 nodes or fewer
- Every named example: what it was → what the alternative was → what the outcome was
- Every framework usable without watching the video
- A "What changed since this was recorded" section whenever the source is over a month old
- An "Applying this in your business" section with costs and a cheaper alternative for every tool
- Skills stay concise: 100–300 lines, linking to the guide for depth
- `verify_guide_html.py` prints ✅ PASS before you report done

## Error handling

- **No captions and no Whisper:** build from description, show notes and research; mark the guide "transcript unavailable"
- **Slide capture fails (no ffmpeg, no yt-dlp, download blocked):** say so, offer the install line, and continue with the transcript alone. Note "slides not captured" in the guide's framing note
- **Far more captures than slides:** run `pick_best_cards.py` (Step 2b); if the region looks wrong, re-run `extract_slides.py` with `--crop`
- **Speaker not findable:** build from the content alone; note the research limitation
- **Technical, code-heavy video:** add a "Quick start" section with working code examples
- **Very long source (over 3 hours):** ask whether to cover all of it or a chosen segment before transcribing
