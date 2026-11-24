# The twin

A twin of you that runs on your machine. It keeps selected notes as a memory you can see, answers from them, checks drafts against a rules file and advises on recognized limits. Coding sessions can ask it through MCP.

## Start it

```bash
python3 twin/twin.py
```

The twin app requires macOS or Linux with Python 3.9 or newer and POSIX directory-relative file access that refuses links. It does not support native Windows. Linux and WSL were not verified in this release audit. These app requirements do not apply to the legacy voice scripts in `scripts/`.

It opens `http://127.0.0.1:4747`. Out of the box it runs the demo: Maya, a made-up person, with made-up notes. No extra packages or account are needed for the typed demo.

## Make it yours

Open **Setup** in the top right.

| Step | What you do | What it needs |
|---|---|---|
| 1. Face | Drop one photo. It checks the photo first and says what to fix. Then it builds a 3D head. | `FAL_KEY` in your shell, and `pip install numpy pillow trimesh opencv-python rembg`. One paid build on your own fal account. |
| 2. Voice | Pick the system voice (free, on macOS or with `espeak-ng`, and the text stays on your machine). With an ElevenLabs key you also get your account's voices and can record 30 to 60 seconds to clone your own, with the consent box ticked. | Nothing for the system voice. `ELEVENLABS_API_KEY` for the rest. Optional. |
| 3. Notes | Choose your name, notes folder, repos, rules file and voice profile. Setup shows the saved sources. Saving a new selection authorizes the read and loads its notes. **Learn from my repos** reads instruction files in saved repos (`CLAUDE.md`, `AGENTS.md`, `.cursorrules`, `CONTRIBUTING.md`) and proposes rules for you to accept or drop. | A folder of Markdown, one note per file. See `examples/twin-notes/`. |

No photo is fine. The twin works with the demo head and your own notes.

Claude Code users: your memory folder (`~/.claude/projects/<project>/memory`) works as the notes folder as it is.

## What each part does

| Part | What it does | Uses a model |
|---|---|---|
| The head | Every dot belongs to one note. Hover for the note, its reason and its date. Click to mark it still true or outdated. | No |
| Ask | Answers from your notes and shows which ones. Says so when the notes do not settle it. | Your choice |
| Check a draft | Runs `scripts/twin_check.py` with your rules. Names each failing line. | No |
| Rewrite it as me | Rewrites the draft, then checks the result. | Yes |
| Limits | Reports matching limit notes and asks for your yes on restricted actions it recognizes. An unmatched request is not permission. The twin cannot push, publish, send or spend for you, and it cannot stop another tool from acting. | No |
| Priorities | An ordered list. Type "add ..." or "done with 2". | No |
| Shipped | Commits found on the listed repos' local remote-tracking main branch. Current as of your last fetch. | No |
| Sessions | Your open Claude Code sessions and their status. Off by default. Enabling it reads session metadata and transcript tails under `~/.claude`, including titles, last prompts, working folders, status and timing. It is not limited to listed repos. | No |
| Audit my work | Read only. Not pushed, not committed, drafts that fail your rules, possible keys in tracked files, old notes. | No |
| Timeline | A date filter over your current notes: drag back and notes first seen after that day drop away. It is not a stored history. | No |
| Teach it | Type `teach: ...` and the note lands on the head. | No |

## Connect your coding sessions

The twin is also an MCP server, so any tool that speaks MCP can ask it. The server uses no model or direct network call. It returns requested notes, sources, rule results and work summaries to the calling client over local stdio. That client may send the results to its model provider. Its own account and privacy settings apply.

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

A session cannot accept its own proposed note. You review proposals in the page before they enter recall. Pending proposals and client-use records are saved immediately. Notes in a folder you select load without per-note approval. Teach is also an immediate owner action.

The page shows which client last used the twin and when, under the session list. The client reports its own name, so treat it as a label. If it says no session has asked yet, the connection is not being used.

Settings changed in the page reach open sessions on their next tool call. Removing a folder or repo revokes reads from that source. Notes you already accepted into the twin's own storage remain separate learned notes until you replace or delete them.

## How it learns, and how you undo it

- Accepted proposals and notes taught in the page are Markdown files in `~/.twin/notes/`, with area, scope, source and time. You can read, edit, copy or delete those learned notes by hand. Selected source notes stay in their original folder.
- When a proposed note clashes with one you already have, the page shows both and asks: replace the old one, keep both, or drop it.
- A replaced note is kept and marked replaced. **Review** lists replaced notes with a Restore button. Restoring one marks the note that replaced it as replaced in turn, so only one stays active.
- Your choice is tied to the exact proposal and the exact old note on screen. If either changed since you looked, nothing happens and the page reloads.
- A note has a scope: `personal`, `brand`, or `project:<name>`. A session can pass its project name to `twin_recall`. Matching project notes get a ranking boost; other notes can still appear. Scope is a retrieval hint, not access control.
- `python3 twin/twin.py export FOLDER` needs a new or empty folder. It writes the twin's active learned files to `notes/`, retired learned files to `replaced/`, active note summaries and metadata to `memory.json`, the rules file and the log. It omits imported source bodies, the voice profile, chat, settings and media. Copy the local data folder and your selected source files separately if you need a full backup.

## What leaves your machine

| Setting | What leaves | Where |
|---|---|---|
| Answers: notes only (the default) | Nothing | Nowhere |
| Answers: Claude | Your question, display name, matched notes with sources, dates, reasons and excerpts, priorities, repo and shipped lists, and voice profile. No further redaction is applied at this call | Claude, through your own `claude` CLI |
| Rewrite it as me | The draft, rules and voice profile. A failed check can trigger a second request with failed-rule feedback. This runs even when answers are set to notes only | Claude, through your own `claude` CLI |
| Connected MCP client | Requested note text, sources, rule results or work summaries | The calling client over local stdio. Its provider policy applies |
| Voice on, system voice | Nothing | Nowhere |
| Voice on, ElevenLabs voice | Reply or preview text on a cache miss | ElevenLabs, through your own key |
| Voice list | An authenticated request for the account's available voices | ElevenLabs, through your own key |
| Cloning a voice | The recording, chosen name and description, per submitted request | ElevenLabs, through your own key |
| Building the head | The cut-out photo per build. CLI side views add their cut-outs. Polls and a mesh download follow | fal, through your own key |
| Photo check | A face-detector download when missing. The photo is checked locally and is not uploaded by the check | GitHub's OpenCV Zoo |
| Photo build model download | A request for missing background-removal weights | The model host used by rembg |

The page labels answer and speech modes. Remote actions have disclosures beside their controls. These labels do not describe a connected client's own traffic. Think does not include chat history or session summaries. Model tools and session persistence are disabled for the CLI calls, but provider retention still follows the provider's terms. Supplied text can still influence an answer or draw out other context in the same request. Do not treat prompt delimiters as isolation between notes.

The server listens on `127.0.0.1` only. API requests need its session token. The page, head and font assets are served without that token to accepted local Host values. This is a local browser-origin boundary, not identified owner authentication. Do not expose the port to a shared network.

## What it is allowed to read

The app reads your selected notes folder, its own learned notes, the selected rules file and voice profile, its local settings/database and bundled assets. Listed repos supply Git history, tracked text and instruction files. Git calls disable hooks, file monitors and optional index locks. These reads do not edit your selected source notes or repo files. The app does write and retire its own notes, save local data, build heads and write exports.

Session discovery is a separate opt-in read. It examines session metadata in `~/.claude/sessions` and transcript tails in `~/.claude/projects`, including the last prompt and working folder. Title filters are applied after those reads. The app does not recursively scan your whole home folder. Setup's source summary is not a per-file preview of every read.

## Keep things out

Four optional settings in `~/.twin/config.json`, each a regular expression:

| Key | Effect |
|---|---|
| `allow_files` | filters selected source notes by file name |
| `allow_terminals` | only sessions whose title matches are shown |
| `deny` | filters note titles/body lines, session summaries and commit subjects. It is not a guarantee that the file is never read |
| `never` | drops matching notes from recall and refuses matching questions. A note must be read before its contents can be tested |

## The microphone

Speech to text runs on your machine with whisper.cpp. Install `whisper-cli` and `ffmpeg`, download a model file, and set `"whisper"` in `~/.twin/config.json` to its path (or `TWIN_WHISPER_MODEL` before the first run). Without it, typing works and the mic says what is missing.

## Your voice rules

**Check a draft** uses one rules file. Claude answers and rewrites also use one voice profile. Both start as labeled examples in `twins/example/`. Build your own with the voice tools, then select both `twin.rules.json` and `twin.md` in Setup under Notes. Changing the rules file does not change the profile. You can also set their paths as `rules` and `persona` in `~/.twin/config.json`. Notes and "Teach it" add to memory. They do not change either file.

## Your data

The local data folder defaults to `~/.twin`; `TWIN_HOME` can select another one. It holds `twin.db` (priorities, questions, answers, pending proposals, reviews, client-use records and the log), `config.json`, learned Markdown notes, submitted build photos/intermediates, heads and cached speech. Questions and priorities can retain the text you entered. Persistent records have no expiry.

Draft checking and local audio conversion use temporary files. Checking or rewriting a draft does not save that draft in chat. Remote providers may retain submitted content under their own terms. The face detector is stored beside `twin/head/build.py`. Background-removal weights use rembg's model cache outside the local data folder by default. Deleting the local data folder does not remove those models or provider-side objects.

- See recorded changes: `python3 twin/twin.py log`. The log includes proposal decisions, note changes and remote-action attestations. It is a local record, not a verified identity trail or a tamper-proof log. Photo build submission records an attestation; voice cloning records it after a successful response. Ticking a checkbox by itself does not create a log entry.
- The log can retain text from earlier events after source removal or filter changes. Export includes that retained history in `log.json`, without reapplying the current note filters. Review it before sharing an export.
- Take a copy: copy the `~/.twin` folder, or run `python3 twin/twin.py export FOLDER` for plain files only.
- Delete local app data: stop the app and connected MCP processes, then delete the selected local data folder. Your selected source files and exported copies remain. Delete a cloned voice through your ElevenLabs account separately. fal builds and other provider data follow those services' retention/deletion terms; local deletion does not prove remote deletion.

## Rules for using it

- Use your own face and voice, or ones you have written consent for. Setup requires self-attestation before remote generation or cloning. The twin cannot verify identity or written permission. Running `twin/head/build.py` by hand needs the `--consent` flag for a photo build too.
- Use writing you have permission to use. Company material needs approval for this purpose. Remove other people's words and identifying or confidential details before scanning or sharing. Another author's writing needs that person's written consent.
- A twin of a person is theirs. Do not use one to monitor or score anyone.

## Limits today

- The session list reads Claude Code sessions only.
- Answers by Claude need the `claude` CLI.
- Voice cloning depends on your ElevenLabs plan allowing instant clones.
- Odd angles, hats and glasses can throw the head's mouth line off. The repo does not establish a broad face-quality test result.
