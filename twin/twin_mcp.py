#!/usr/bin/env python3
"""The twin as an MCP server, so every coding session shares one memory and one set of limits.

Standard library only. Talks JSON-RPC over stdin/stdout. Uses no model and no network.
It can read the twin's notes and propose a new one. A proposal does nothing until the owner accepts it in the page.

Turn it on for Claude Code:   claude mcp add twin -- python3 /full/path/to/twin_mcp.py
Turn it off:                  claude mcp remove twin
"""
import json, os, sys
sys.argv = sys.argv[:1]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import twin

S = lambda **p: {"type": "object", "properties": p, "required": list(p)}
STR = lambda d: {"type": "string", "description": d}
TOOLS = {
    "twin_brief": ("What is going on right now in the owner's workspace: open sessions, what shipped, what is not pushed, priorities, stale notes. Counted by code.", S(), lambda a: twin.brief()),
    "twin_recall": ("Look up what the owner has already decided, likes, or ruled out. Returns their own notes word for word with sources, or says there is not enough evidence. Call this before guessing a preference.",
                    {"type": "object", "properties": {"question": STR("Plain question, for example: do we use emojis in videos"), "project": STR("Optional. The repo or project name, so notes scoped to it rank first")}, "required": ["question"]}, lambda a: recall(a["question"], a.get("project", ""))),
    "twin_check_draft": ("Check a draft against the owner's voice rules. Code checks it; same answer every time. Call before showing the owner any copy.", S(text=STR("The draft")), lambda a: draft(a["text"])),
    "twin_allowed": ("Ask whether an action needs the owner's yes first. Call before pushing, publishing, sending, spending or deleting.", S(action=STR("What you are about to do")), lambda a: twin.allowed(a["action"])),
    "twin_propose_note": ("Propose something the owner just decided or corrected, so future sessions know it. It is only a proposal: the owner accepts or drops it in the twin page. One short sentence, their decision and the reason.",
                          {"type": "object", "properties": {"text": STR("The decision or preference"), "area": {"type": "string", "enum": twin.AREAS}, "scope": STR("personal, brand, or project:<name>. Default personal")}, "required": ["text"]},
                          lambda a: ({"proposed": True, "note": "Waiting for the owner to accept it in the twin page."} if twin.propose(a["text"], a.get("area", "decisions"), CLIENT[0], a.get("scope", "personal")) else {"proposed": False, "note": "Not kept. It is outside this workspace or empty."})),
    "twin_priorities": ("The owner's ordered priority list.", S(), lambda a: [p["text"] for p in twin.priorities() if not p["done"]]),
    "twin_audit": ("Read-only audit of the owner's listed repos: work not pushed or committed, drafts that fail the voice rules, possible keys in tracked files, old notes. Writes and deletes nothing.", S(), lambda a: twin.audit()),
}


CLIENT = ["a coding session"]


def recall(q, project=""):
    twin.sync_cfg()
    if twin.HARD.search(q): return {"evidence": "none", "note": "That is outside this workspace."}
    level, ev = twin.IX.search(q, project=project)
    return {"evidence": level, "notes": [{"note": e["title"], "why": e["why"], "since": e["since"], "source": e["src"], "scope": e.get("scope", "personal")} for e in ev[:4]]}


def draft(text):
    c = twin.check(text)
    if "error" in c: return c
    return {"passed": c["passed"], "fails": [{"rule": r["id"], "severity": r["severity"], "fix": r.get("suggestion", ""), "found": sorted({h.get("match", "") for h in r.get("hits", []) if h.get("match")})[:6]} for r in c["results"] if not r["passed"]]}


def reply(i, result=None, error=None):
    m = {"jsonrpc": "2.0", "id": i}; m.update({"error": error} if error else {"result": result}); sys.stdout.write(json.dumps(m) + "\n"); sys.stdout.flush()


for line in sys.stdin:
    try: m = json.loads(line)
    except Exception: continue
    i, meth = m.get("id"), m.get("method", "")
    if meth == "initialize":
        CLIENT[0] = str((m.get("params", {}).get("clientInfo") or {}).get("name") or "a coding session")[:60]
        reply(i, {"protocolVersion": m.get("params", {}).get("protocolVersion", "2024-11-05"), "capabilities": {"tools": {}}, "serverInfo": {"name": "twin", "version": "4.0.0"},
                                       "instructions": "The owner's twin. Recall before guessing a preference, check drafts before showing them, ask twin_allowed before anything that cannot be undone."})
    elif meth == "tools/list": reply(i, {"tools": [{"name": n, "description": d, "inputSchema": s} for n, (d, s, _) in TOOLS.items()]})
    elif meth == "tools/call":
        p = m.get("params", {}); t = TOOLS.get(p.get("name"))
        if not t: reply(i, error={"code": -32602, "message": "Unknown tool"}); continue
        try:
            twin.sync_cfg()                      # settings may have changed in the page since this session started
            out = t[2](p.get("arguments") or {}); twin.client_seen(CLIENT[0], p.get("name"), "ok"); reply(i, {"content": [{"type": "text", "text": out if isinstance(out, str) else json.dumps(out, indent=1)}]})
        except Exception as e:
            try: twin.client_seen(CLIENT[0], p.get("name"), "error")
            except Exception: pass
            reply(i, {"content": [{"type": "text", "text": "The twin could not answer: " + type(e).__name__}], "isError": True})
    elif meth == "ping": reply(i, {})
    elif i is not None: reply(i, error={"code": -32601, "message": "Method not found"})
