#!/usr/bin/env python3
"""The learning loop, end to end, with real fresh sessions.

  1. A fresh session with no twin is asked something only the owner knows.
  2. A fresh session with the twin is asked the same thing. The twin has no note yet.
  3. The owner corrects it. A session proposes the note. The owner accepts it.
  4. Another fresh session is asked again. It should use the note and name its source.
  5. The owner changes the decision. The new note replaces the old one.
  6. Another fresh session is asked again. It should use the new decision only.

This calls your own `claude` CLI seven times, so it uses your Claude account. It runs on a throwaway data
folder and the made-up sample notes. Nothing is written to your real twin.

  python3 validation/twin_loop.py                 prints the transcript
  python3 validation/twin_loop.py --out FILE.md   also writes it as Markdown

The "owner accepts" steps are done by calling the same function the page's Accept and Replace buttons call.
"""
import json, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOME_ = tempfile.mkdtemp(prefix="twin-loop-")
ENV = dict(os.environ, TWIN_HOME=HOME_)
MCP = os.path.join(HOME_, "mcp.json")
with open(MCP, "w") as f:
    json.dump({"mcpServers": {"twin": {"command": sys.executable, "args": [os.path.join(ROOT, "twin", "twin_mcp.py")], "env": {"TWIN_HOME": HOME_}}}}, f)
TOOLS = "mcp__twin__twin_recall,mcp__twin__twin_propose_note,mcp__twin__twin_allowed"
Q = "What colour do we print our shipping labels in? Answer in one short line. If you used a note, name its source. If you do not know, say so plainly and do not guess."
log = []


def session(prompt, twin=True):
    cmd = ["claude", "-p", "--model", "sonnet", "--setting-sources", "", "--no-session-persistence", "--strict-mcp-config"]
    cmd += ["--mcp-config", MCP, "--allowedTools", TOOLS] if twin else ["--tools", ""]
    env = {k: v for k, v in ENV.items() if not k.startswith(("CLAUDECODE", "CLAUDE_CODE"))}
    r = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=240, cwd=HOME_, env=env)
    return " ".join(r.stdout.split()) or "(no answer)"


def owner(code):
    """Runs one owner action against the throwaway twin."""
    return subprocess.run([sys.executable, "-c", "import sys,json;sys.argv=['x'];sys.path.insert(0,%r);import twin\n%s" % (os.path.join(ROOT, "twin"), code)],
                          capture_output=True, text=True, env=ENV, timeout=60).stdout.strip()


def step(title, text, check=None):
    ok = None if check is None else bool(check(text.lower()))
    log.append((title, text, ok)); print("\n## %s\n%s%s" % (title, text, "" if ok is None else "\n-> %s" % ("as expected" if ok else "NOT as expected")))


unsure = lambda t: any(w in t for w in ("don't know", "do not know", "no note", "not enough", "no evidence", "don't have", "do not have", "cannot", "can't", "no information", "unknown", "not sure", "no record"))
step("1. Fresh session, no twin", session("You have no tools and no files in this session. " + Q, twin=False), unsure)
step("2. Fresh session, with the twin, before any note exists", session("Use the twin tools. " + Q), unsure)
step("3a. The owner corrects it, and a session proposes the note",
     session("The owner just told you: our shipping labels are printed in black only. Propose that to the twin as a taste note with twin_propose_note. Then reply with one line saying what you proposed."))
step("3b. The owner accepts it", owner("p=twin.proposals();print(p[0]['text'] if p else 'no proposal');twin.settle(p[0]['id'],True) if p else None"), lambda t: "black" in t)
step("4. Another fresh session", session("Use the twin tools. " + Q), lambda t: "black" in t)
step("5a. The owner changes the decision, and a session proposes it",
     session("The owner just told you: from now on our shipping labels are printed in dark green, not black. Propose that to the twin as a taste note with twin_propose_note. Then reply with one line saying what you proposed."))
step("5b. The owner picks Replace the old one", owner("p=twin.proposals();print((p[0]['text']+' | clashes with: '+str((p[0]['conflict'] or {}).get('title'))) if p else 'no proposal');twin.settle(p[0]['id'],True,True) if p else None"), lambda t: "green" in t and "black" in t)
step("6. Another fresh session", session("Use the twin tools. " + Q), lambda t: "green" in t and "black only" not in t)
step("The twin's own log", owner("print(chr(10).join(r['at']+' | '+r['action']+' | '+r['detail'] for r in twin.DB.execute('select at,action,detail from log order by id')))"))
step("Who asked", owner("print(json.dumps([{k:c[k] for k in ('name','last_tool','calls')} for c in twin.clients()]))"))

checked = [ok for _, _, ok in log if ok is not None]
summary = "%d of %d checked steps came out as expected." % (sum(checked), len(checked))
print("\n" + summary)
if "--out" in sys.argv:
    with open(sys.argv[sys.argv.index("--out") + 1], "w") as f:
        f.write("# The learning loop, one real run\n\nEvery answer below is the real output of `validation/twin_loop.py`: fresh `claude` sessions on a throwaway twin with the made-up sample notes. One run. A model's wording varies from run to run.\n\n**%s**\n" % summary)
        for title, text, ok in log:
            f.write("\n## %s\n\n```\n%s\n```\n%s" % (title, text, "" if ok is None else ("\nAs expected.\n" if ok else "\nNot as expected.\n")))
import shutil
shutil.rmtree(HOME_, ignore_errors=True)
