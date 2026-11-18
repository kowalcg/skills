# Free Claude Code skills

Skills I give away, from [gregkowalczyk.com](https://www.gregkowalczyk.com/projects/). Each one runs
inside [Claude Code](https://claude.com/claude-code). MIT licence, use them however you like.

| Skill | What it does | Version |
|---|---|---|
| [video-to-skill](skills/video-to-skill/) | Turns a YouTube video, podcast, webinar or talk into a written guide with diagrams and a screenshot of every slide, and optionally into a reusable Claude skill. | 1.1 |

---

## Install

You need Claude Code first: [claude.com/claude-code](https://claude.com/claude-code). Install it,
run `claude` once in a terminal and sign in.

### Option 1: from inside Claude Code (recommended, gets updates)

Type these two lines in Claude Code:

```
/plugin marketplace add kowalcg/skills
/plugin install video-to-skill@greg-skills
```

Restart Claude Code. To get new versions later: `/plugin marketplace update greg-skills`.

### Option 2: copy the folder

macOS / Linux:
```bash
git clone https://github.com/kowalcg/skills.git
mkdir -p ~/.claude/skills
cp -R skills/skills/video-to-skill ~/.claude/skills/
```

Windows (PowerShell):
```powershell
git clone https://github.com/kowalcg/skills.git
New-Item -ItemType Directory -Force "$HOME\.claude\skills" | Out-Null
Copy-Item -Recurse "skills\skills\video-to-skill" "$HOME\.claude\skills\"
```

No git? Click **Code → Download ZIP** above, unzip, and copy `skills/video-to-skill` into
`~/.claude/skills/`. The file must end up at `~/.claude/skills/video-to-skill/SKILL.md`.

### Then

Install the Python packages and optional tools listed in the
[video-to-skill README](skills/video-to-skill/README.md#install-about-90-seconds) (Claude offers to
install them the first time it needs them), and try it:

```
/video-to-skill https://www.youtube.com/watch?v=...
```

---

**Want the next skill when it's out?** Leave your name and email on the
[video-to-skill page](https://www.gregkowalczyk.com/skills/video-to-skill/) and I'll let you know.

Questions or ideas: [gregkowalczyk.com/contact](https://www.gregkowalczyk.com/contact/).
