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
| Limits | Pushing, publishing, sending, spending and deleting always come back as "needs your yes", and so does anything that matches one of your limit notes. The twin has no code that does any of them. It cannot stop another tool from acting: it gives advice, and the session has to ask. | No |
| Priorities | An ordered list. Type "add ..." or "done with 2". | No |
| Shipped | What reached the main branch of the repos you listed. | No |
| Sessions | Your open Claude Code sessions and which are waiting on you. Off by default, because it reads session titles from `~/.claude`. Turn it on in Setup. | No |
| Audit my work | Read only. Not pushed, not committed, drafts that fail your rules, possible keys in tracked files, old notes. | No |
| Timeline | A date filter over your current notes: drag back and notes first seen after that day drop away. It is not a stored history. | No |
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

The page shows which client last used the twin and when, under the session list. The client reports its own name, so treat it as a label. If it says no session has asked yet, the connection is not being used.

Settings changed in the page reach open sessions on their next question. Remove a notes folder or a repo in Setup, and a session that was already running stops seeing it.

## How it learns, and how you undo it

- Everything the twin learns is one Markdown file in `~/.twin/notes/`, with its area, scope, source and the time you accepted it. You can read, edit, copy or delete those files by hand.
- When a proposed note clashes with one you already have, the page shows both and asks: replace the old one, keep both, or drop it.
- A replaced note is kept and marked replaced. **Review** lists replaced notes with a Restore button. Restoring one marks the note that replaced it as replaced in turn, so only one stays active.
- Your choice is tied to the exact proposal and the exact old note on screen. If either changed since you looked, nothing happens and the page reloads.
- A note has a scope: `personal`, `brand`, or `project:<name>`. A session can pass its project name to `twin_recall`, and notes for that project rank first.
- `python3 twin/twin.py export FOLDER` needs a new or empty folder. It writes active notes to `notes/`, replaced ones to `replaced/`, a `memory.json` of every active note it can read, the rules file and the log.

## What leaves your machine

| Setting | What leaves | Where |
|---|---|---|
| Answers: notes only (the default) | Nothing | Nowhere |
| Answers: Claude | Your question, your display name, the notes that match, your priorities, your repo and shipped lists, and your voice profile. These are sent as they are, not redacted further | Claude, through your own `claude` CLI |
| Rewrite it as me | The draft, your voice rules and your voice profile. This runs even when answers are set to notes only | Claude, through your own `claude` CLI |
| Voice on, system voice | Nothing | Nowhere |
| Voice on, ElevenLabs voice | The text of each reply | ElevenLabs, through your own key |
| Cloning a voice | The recording you made, once | ElevenLabs, through your own key |
| Building the head | The cut-out photo, once | fal, through your own key |
| The photo check, first run | A request for a small face-finder model | github.com/opencv/opencv_zoo |
| Everything else | Nothing | A folder on your machine (`~/.twin`) |

The page shows the current line in the top right at all times. The server listens on `127.0.0.1` only and refuses requests without its session token.

## What it is allowed to read

Only the notes folder and the repos you list in Setup, plus Claude Code session titles if you turn that on. It never walks your home folder, and it will not follow a symlink that leads out of a folder you listed. Git runs with hooks switched off. In the repos it runs git read commands and reads tracked text files. It has no code that writes to, moves or deletes your files. Its own data lives in `~/.twin`.

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

## Your voice rules

**Check a draft** uses one rules file, and answers and rewrites by Claude use one voice profile. Out of the box both are the examples in `twins/example/`, not yours. Setup shows which files are active and lets you change both. To use your own, build a twin with the voice tools in this repo (see the README), then put the path to its `twin.rules.json` in Setup under Notes. Notes and "Teach it" add to memory. They do not change the checker's rules.

## Your data

Everything the twin keeps is in `~/.twin`: `twin.db` (priorities, notes you taught, your questions and its answers, proposals, and a log), `config.json`, the photo and head files, and cached speech. Questions and drafts you type are stored there as typed. Nothing in it expires on its own.

- See what changed the twin, and when: `python3 twin/twin.py log`. It records each accepted or dropped proposal with its source, each note taught or marked, and each consent tick for a photo or a voice.
- Take a copy: copy the `~/.twin` folder, or run `python3 twin/twin.py export FOLDER` for plain files only.
- Delete everything: stop the twin and delete the `~/.twin` folder. A cloned voice lives on your ElevenLabs account and is deleted there. A head build ran on your fal account and is governed by its retention terms.

## Rules for using it

- Your own face and voice, or ones you have written consent for. Setup makes you tick a box for each. That is your statement, recorded with the time. The twin cannot verify it. Running `twin/head/build.py` by hand needs the `--consent` flag for the same reason.
- Your own notes. Never a coworker's messages or a client's data.
- A twin of a person is theirs. Do not use one to monitor or score anyone.

## Limits today

- The session list reads Claude Code sessions only.
- Answers by Claude need the `claude` CLI.
- Voice cloning depends on your ElevenLabs plan allowing instant clones.
- The head build has been run on two faces. Odd angles, hats and glasses can still throw the mouth line off.
