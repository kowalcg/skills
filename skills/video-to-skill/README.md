# video-to-skill

Turn any YouTube video, podcast, webinar or talk into a comprehensive written guide with
diagrams, and optionally into a reusable Claude skill that applies what the expert taught.

**New in 1.1:** every slide shown in the video is captured as a screenshot, and the guide is
built from the slides, page by page, with the speaker's exact words under each one.

Free. Runs inside [Claude Code](https://claude.com/claude-code). Everything it produces goes into
`~/Downloads/Video Skills/`.

From Greg Kowalczyk, gregkowalczyk.com. Shared at the *AI for Business* meetups in Hamilton and
Oakville, Ontario.

---

## Install (about 90 seconds)

**1. You need Claude Code.** If you don't have it yet:
[claude.com/claude-code](https://claude.com/claude-code) — install, then run `claude` once in a
terminal and sign in.

**2. Put this folder where Claude Code looks for skills.**

macOS / Linux, in a terminal:
```bash
mkdir -p ~/.claude/skills
cp -R "video-to-skill" ~/.claude/skills/video-to-skill
```
Windows (PowerShell):
```powershell
New-Item -ItemType Directory -Force "$HOME\.claude\skills" | Out-Null
Copy-Item -Recurse "video-to-skill" "$HOME\.claude\skills\video-to-skill"
```
The folder must end up as `~/.claude/skills/video-to-skill/SKILL.md`.

**3. Python 3 plus two packages** (Claude will offer to install them the first time it needs them):
```bash
pip3 install youtube-transcript-api markdown
```

That's enough for the transcript and the guide of any YouTube video with captions.

**4. For slide capture** (recommended: this is what makes the guide exact):
```bash
brew install ffmpeg yt-dlp        # macOS. Windows/Linux: install from ffmpeg.org and github.com/yt-dlp
pip3 install numpy Pillow
```
On a Mac, the text on each slide is also read with Apple Vision. That needs the Xcode Command
Line Tools (`xcode-select --install`, one time). On Windows and Linux the slides are still
captured; Claude reads the images directly instead.

**Optional, for podcasts, audio files and videos without captions:**
```bash
pip3 install openai-whisper       # local transcription, no API key, no cost (needs ffmpeg, above)
```

**Optional, for the full browser-based diagram check:**
```bash
pip3 install playwright && python3 -m playwright install chromium
```

---

## Use it

Open a terminal in any folder, run `claude`, and type:

```
/video-to-skill https://www.youtube.com/watch?v=XXXXXXXXXXX
```

Or just say *"learn from this video"* and paste the link. Claude asks whether you want a
**Full Skill**, a **Guide Only**, or a **Quick Summary**, then does the work.

You get a folder in `~/Downloads/Video Skills/` with the transcript, a `slides/` folder holding
every slide the speaker showed (plus an index of what was said under each), the guide as a single
HTML file that works offline with the slides inlined, the same guide as Markdown, and (in Full
Skill mode) a `SKILL.md` that Claude installs so the method is available in every future session.

---

## What's in this package

| File | Purpose |
|---|---|
| `SKILL.md` | The skill itself. Claude reads this. |
| `GUIDE-STANDARD.md` | The structure, diagram and quality rules for every guide |
| `scripts/get_transcript.py` | Fetches YouTube captions, plain or timestamped |
| `scripts/extract_slides.py` | Captures every distinct slide from the video: handles webcam strips, progressive builds, revisits, page-number completeness check |
| `scripts/pick_best_cards.py` | Collapses repeated captures of editor-made graphic cards in talking-head videos |
| `scripts/ocr.swift` | Reads the text on each slide with Apple Vision (macOS only; compiled on first run) |
| `scripts/build_guide_html.py` | Turns the Markdown guide into one self-contained HTML file |
| `scripts/verify_guide_html.py` | Proves the diagrams actually rendered before the guide is called done |
| `scripts/mermaid.min.js` | The diagram library, bundled so guides work offline |

## Make it yours

Everything is plain text. Open `SKILL.md` and change the guide structure, add a section your
business always needs, change the output folder, or add your own quality rules. Claude
follows whatever the file says.

## Questions

gregkowalczyk.com/contact — or come to the next *AI for Business* meetup:
gregkowalczyk.com/meetups

## Changelog

- **1.1 (October 2026):** slide capture. Every distinct slide, build state and hover tooltip is
  saved as a PNG with a timestamp, what was said while it was on screen and (macOS) the exact text
  on it; the guide is written slide by slide; slides are inlined in the HTML as compressed JPEG;
  the verifier now also checks every slide image decoded. Print-to-PDF fixes in the HTML builder.
- **1.0 (September 2026):** first public release.

Version 1.1 · October 2026 · MIT licence, do what you like with it.
