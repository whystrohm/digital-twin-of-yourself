#!/usr/bin/env python3
"""One paid smoke check of the learning loop, using six fresh Claude CLI sessions.

Run explicitly: python3 validation/twin_loop.py [--out a-new-result.md]
It uses your Claude account and sends synthetic prompts and sample notes to Claude.
TWIN_HOME and the working directory are temporary. Your CLI credentials still come
from your normal account. Importing this module never starts a session.

Owner actions use the same acceptance function as the page. Checks cover exact
active notes, source citations and per-session tool-count changes. This is a small
smoke check, not a measure of voice fidelity or time saved.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = "mcp__twin__twin_recall,mcp__twin__twin_propose_note,mcp__twin__twin_allowed"
QUESTION = ('What colour do we print our shipping labels in? Return exactly one JSON object with '
            '"colour" ("unknown", "black", or "dark green"), "note" (the exact note text), '
            'and "source" (the exact source returned by twin_recall). For unknown use empty '
            'note and source strings. Do not guess. Do not put the JSON in a code fence.')
BLACK = "Shipping labels are printed in black only."
GREEN = "Shipping labels are printed in dark green."


def answer_matches(answer, colour, note=None):
    """Check explicit fields, not words that may occur in a negated answer."""
    if not isinstance(answer, dict) or answer.get("colour") != colour:
        return False
    if note is None:
        return answer.get("note") == "" and answer.get("source") == ""
    return answer.get("note") == note["title"] and answer.get("source") == note["src"]


def checked_run(cmd, **kwargs):
    result = subprocess.run(cmd, capture_output=True, text=True, **kwargs)
    if result.returncode:
        raise RuntimeError("Child command failed with exit %d; no result was accepted." % result.returncode)
    return result.stdout.strip()


class LoopProof:
    def __init__(self, home, model):
        self.home, self.model, self.log = home, model, []
        self.env = {k: v for k, v in os.environ.items()
                    if not k.startswith(("CLAUDECODE", "CLAUDE_CODE")) and k not in ("FAL_KEY", "ELEVENLABS_API_KEY")}
        self.env["TWIN_HOME"] = home
        self.mcp = os.path.join(home, "mcp.json")
        with open(self.mcp, "w", encoding="utf-8") as f:
            json.dump({"mcpServers": {"twin": {"command": sys.executable,
                      "args": [os.path.join(ROOT, "twin", "twin_mcp.py")], "env": {"TWIN_HOME": home}}}}, f)
        with open(os.path.join(home, "config.json"), "w", encoding="utf-8") as f:
            json.dump({"memory": os.path.join(ROOT, "examples", "twin-notes"),
                       "repos": [], "read_sessions": False}, f)

    def session(self, prompt, twin=True):
        cmd = ["claude", "-p", "--model", self.model, "--setting-sources", "",
               "--no-session-persistence", "--strict-mcp-config", "--tools", ""]
        if twin:
            cmd += ["--mcp-config", self.mcp, "--allowedTools", TOOLS]
        text = checked_run(cmd, input=prompt, timeout=240, cwd=self.home, env=self.env)
        try:
            answer = json.loads(text)
        except (ValueError, TypeError):
            raise RuntimeError("The session did not return the required JSON object.")
        if not isinstance(answer, dict):
            raise RuntimeError("The session result was not a JSON object.")
        return answer

    def owner(self, code):
        """Only constant owner operations run here, against the temporary store."""
        program = ("import sys,json;sys.argv=['x'];sys.path.insert(0,%r);import twin\n" % os.path.join(ROOT, "twin"))
        program += code + "\nprint(json.dumps(result))\ntwin.DB.close()\n"
        text = checked_run([sys.executable, "-c", program], timeout=60, cwd=self.home, env=self.env)
        try:
            return json.loads(text)
        except (ValueError, TypeError):
            raise RuntimeError("The owner action did not return valid JSON.")

    def snapshot(self):
        return self.owner("result={'active':[{k:e[k] for k in ('id','title','src')} for e in twin.IX.get().e "
                          "if 'shipping labels' in e['title'].lower()], 'proposals':twin.proposals(), "
                          "'clients':twin.clients()}")

    @staticmethod
    def used_tool(before, after, tool):
        prior = sum(c["calls"] for c in before["clients"])
        return (sum(c["calls"] for c in after["clients"]) > prior
                and any(c["last_tool"] == tool for c in after["clients"]))

    def step(self, title, data, passed):
        self.log.append((title, data, bool(passed)))
        print("\n## %s\n%s\n%s" % (title, json.dumps(data, ensure_ascii=False, indent=2),
                                       "As expected." if passed else "Not as expected."))

    def propose(self, text):
        before = self.snapshot()
        reply = self.session("The owner just made this decision. Call twin_propose_note exactly once with "
                             "area taste, scope personal, and this exact text: %s. Then return only "
                             'a JSON object with "proposed": true.' % json.dumps(text))
        after = self.snapshot()
        pending = after["proposals"]
        if (not self.used_tool(before, after, "twin_propose_note") or len(pending) != 1
                or pending[0]["text"] != text or pending[0]["area"] != "taste"
                or pending[0].get("scope") != "personal"):
            raise RuntimeError("No single matching proposal was observed. Nothing was accepted.")
        self.step("Session proposes the owner's decision", {"reply": reply, "proposal": pending[0]}, True)
        return pending[0]

    def accept(self, proposal, old=None):
        code = "result=twin.settle(%r,True,%r,%r,%r)" % (
            proposal["id"], bool(old), proposal["uid"], old["id"] if old else None)
        result = self.owner(code)
        state = self.snapshot()
        active = state["active"]
        good = (result == {"ok": 1} and len(active) == 1
                and active[0]["title"] == proposal["text"] and not state["proposals"])
        if old:
            good = good and bool(active) and active[0]["id"] != old["id"]
        self.step("Owner accepts the exact reviewed proposal", {"result": result, "state": state}, good)
        if not good:
            raise RuntimeError("Acceptance did not leave exactly one expected active note.")
        return active[0]

    def recall(self, colour, note=None):
        before = self.snapshot()
        answer = self.session("Call twin_recall for the question, then answer it. " + QUESTION)
        after = self.snapshot()
        good = self.used_tool(before, after, "twin_recall") and answer_matches(answer, colour, note)
        good = good and after["active"] == ([note] if note else [])
        self.step("Fresh session recalls " + colour, {"answer": answer, "state": after}, good)

    def run(self):
        answer = self.session("You have no tools or files. " + QUESTION, twin=False)
        self.step("Fresh session without the twin", answer, answer_matches(answer, "unknown"))
        self.recall("unknown")
        black = self.accept(self.propose(BLACK))
        self.recall("black", black)
        green = self.accept(self.propose(GREEN), black)
        self.recall("dark green", green)
        return all(ok for _, _, ok in self.log)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", help="write a Markdown transcript to this explicit path")
    parser.add_argument("--model", default="sonnet", help="requested Claude CLI model or alias")
    args = parser.parse_args(argv)
    with tempfile.TemporaryDirectory(prefix="twin-loop-") as home:
        proof = LoopProof(home, args.model)
        try:
            passed = proof.run()
        except (RuntimeError, OSError, subprocess.TimeoutExpired) as exc:
            proof.step("Run failed", {"error": str(exc)}, False)
            passed = False
        summary = "%d of %d checked steps came out as expected." % (sum(ok for _, _, ok in proof.log), len(proof.log))
        print("\n" + summary)
        if args.out:
            with open(__file__, "rb") as source:
                source_hash = hashlib.sha256(source.read()).hexdigest()
            with open(args.out, "w", encoding="utf-8") as f:
                f.write("# Learning-loop smoke check\n\nSix fresh sessions on synthetic notes. Requested model: %s.\n"
                        "Harness SHA-256: %s. Python: %s.\n"
                        "Per-step tool counts and exact note state are recorded below. This is not a fidelity benchmark.\n\n**%s**\n"
                        % (args.model, source_hash, sys.version.split()[0], summary))
                for title, data, ok in proof.log:
                    f.write("\n## %s\n\n```json\n%s\n```\n\n%s\n" % (
                        title, json.dumps(data, ensure_ascii=False, indent=2), "As expected." if ok else "Not as expected."))
        return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
