# The twin

A twin of you that runs on your machine. It keeps your notes as a memory you can see, answers from them, checks drafts against your voice rules, stops at your limits, and lets every coding session ask it first.

## Start it

```bash
python3 twin/twin.py
```

It opens `http://127.0.0.1:4747`. Out of the box it runs the demo: Maya, a made-up person, with made-up notes. Python 3.9 or newer. Nothing to install for this step.

## Make it yours

Open **Setup** in the top right.

| Step | What you do | What it needs |
|---|---|---|
| 1. Face | Drop one photo. It checks the photo first and says what to fix. Then it builds a 3D head. | `FAL_KEY` in your shell, and `pip install numpy pillow trimesh opencv-python rembg`. One paid build on your own fal account. |
| 2. Voice | Pick the system voice (free, on macOS or with `espeak-ng`, and the text stays on your machine). With an ElevenLabs key you also get your account's voices and can record 30 to 60 seconds to clone your own, with the consent box ticked. | Nothing for the system voice. `ELEVENLABS_API_KEY` for the rest. Optional. |
| 3. Notes | Set your name, your notes folder and the git repos it may read. The page lists exactly what it will read before it reads. Then the head fills as each note lands. **Learn from my repos** reads the instruction files in those repos (`CLAUDE.md`, `AGENTS.md`, `.cursorrules`, `CONTRIBUTING.md`) and proposes their rules. You accept or drop each one. | A folder of Markdown, one note per file. See `examples/twin-notes/`. |

No photo is fine. The twin works with the demo head and your own notes.

Claude Code users: your memory folder (`~/.claude/projects/<project>/memory`) works as the notes folder as it is.

## What each part does

| Part | What it does | Uses a model |
|---|---|---|
| The head | Every dot belongs to one note. Hover for the note, its reason and its date. Click to mark it still true or outdated. | No |
| Ask | Answers from your notes and shows which ones. Says so when the notes do not settle it. | Your choice |
| Check a draft | Runs `scripts/twin_check.py` with your rules. Names each failing line. | No |
| Rewrite it as me | Rewrites the draft, then checks the result. | Yes |
| Limits | Pushing, publishing, sending, spending and deleting always come back as "needs your yes". The twin has no code that does any of them. | No |
| Priorities | An ordered list. Type "add ..." or "done with 2". | No |
| Shipped | What reached the main branch of the repos you listed. | No |
| Audit my work | Read only. Not pushed, not committed, drafts that fail your rules, possible keys in tracked files, old notes. | No |
| Timeline | Drag back to see what the twin knew on a given day. | No |
| Teach it | Type `teach: ...` and the note lands on the head. | No |

## Connect your coding sessions

The twin is also an MCP server, so any tool that speaks MCP can ask it. It uses no model and no network.

Claude Code:

```bash
claude mcp add twin -- python3 /full/path/to/twin/twin_mcp.py
claude mcp remove twin        # to turn it off
```

Any other MCP client: add a server whose command is `python3` and whose argument is the full path to `twin/twin_mcp.py`.

| Tool | A session calls it to |
|---|---|
| `twin_recall` | look up what you already decided, before guessing |
| `twin_check_draft` | check copy before you see it |
| `twin_allowed` | ask whether an action needs your yes |
| `twin_propose_note` | propose a note after you correct it. You accept or drop it in the page |
| `twin_brief` | read what is open, shipped and waiting |
| `twin_priorities` | read your ordered list |
| `twin_audit` | run the read-only audit |

A session can only propose. Nothing becomes part of the twin until you accept it.

## What leaves your machine

| Setting | What leaves | Where |
|---|---|---|
| Answers: notes only (the default) | Nothing | Nowhere |
| Answers: Claude | Your question, the few notes that match, and the work lists on the page | Claude, through your own `claude` CLI |
| Voice on, system voice | Nothing | Nowhere |
| Voice on, ElevenLabs voice | The text of each reply | ElevenLabs, through your own key |
| Cloning a voice | The recording you made, once | ElevenLabs, through your own key |
| Building the head | The cut-out photo, once | fal, through your own key |
| The photo check, first run | A request for a small face-finder model | github.com/opencv/opencv_zoo |
| Everything else | Nothing | A folder on your machine (`~/.twin`) |

The page shows the current line in the top right at all times. The server listens on `127.0.0.1` only and refuses requests without its session token.

## What it is allowed to read

Only the notes folder and the repos you list in Setup. It never walks your home folder. In the repos it runs git read commands and reads tracked text files. It has no code that writes to, moves or deletes your files. Its own data lives in `~/.twin`.

## Keep things out

Four optional settings in `~/.twin/config.json`, each a regular expression:

| Key | Effect |
|---|---|
| `allow_files` | only note files whose name matches are loaded |
| `allow_terminals` | only sessions whose title matches are shown |
| `deny` | notes, sessions and commit lines that match are dropped |
| `never` | a note that mentions it anywhere is dropped whole, and questions that mention it are refused |

## The microphone

Speech to text runs on your machine with whisper.cpp. Install `whisper-cli` and `ffmpeg`, download a model file, and set `"whisper"` in `~/.twin/config.json` to its path (or `TWIN_WHISPER_MODEL` before the first run). Without it, typing works and the mic says what is missing.

## Rules for using it

- Your own face and voice, or ones you have written consent for.
- Your own notes. Never a coworker's messages or a client's data.
- A twin of a person is theirs. Do not use one to monitor or score anyone.

## Limits today

- The session list reads Claude Code sessions only.
- Answers by Claude need the `claude` CLI.
- Voice cloning depends on your ElevenLabs plan allowing instant clones.
- The head build has been run on two faces. Odd angles, hats and glasses can still throw the mouth line off.
