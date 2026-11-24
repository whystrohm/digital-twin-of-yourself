"""The twin server, on the made-up sample. Offline. No model, no network."""
import json, os, subprocess, sys, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ["TWIN_HOME"] = tempfile.mkdtemp(prefix="twin-test-")
sys.path.insert(0, os.path.join(ROOT, "twin"))
_argv, sys.argv = sys.argv, sys.argv[:1]
import twin  # noqa: E402
sys.argv = _argv


class TwinApp(unittest.TestCase):
    def test_sample_notes_load_into_every_area(self):
        e = twin.IX.get().e
        self.assertGreaterEqual(len(e), 15)
        self.assertEqual({x["area"] for x in e}, set(twin.AREAS))

    def test_recall_finds_the_note_and_its_source(self):
        level, ev = twin.IX.search("do we ship on a friday")
        self.assertIn(level, ("strong", "some"))
        self.assertEqual(ev[0]["src"], "ship-days.md")
        self.assertIn("weekend", ev[0]["why"])

    def test_no_evidence_is_an_answer(self):
        a = twin.ask("what is our policy on office plants", "recall")
        self.assertEqual(a["level"], "not enough")
        self.assertEqual(a["sources"], [])

    def test_push_needs_a_yes(self):
        self.assertTrue(twin.ask("push the site live", "recall")["gate"])
        self.assertTrue(twin.allowed("delete the old export folder")["needs_owner_yes"])
        self.assertFalse(twin.allowed("rename a local variable")["needs_owner_yes"])

    def test_a_session_can_only_propose(self):
        before = len(twin.IX.get().e)
        pid = twin.propose("Labels print in black only.", "taste", "a test")
        self.assertEqual(len(twin.IX.get().e), before)          # proposed is not memory
        twin.settle(pid, True)
        self.assertEqual(len(twin.IX.get().e), before + 1)       # accepted is

    def test_redaction(self):
        r = twin.redact("mail sam@example.com or call 617-555-0100, it cost $1,200")
        for leak in ("sam@example.com", "555-0100", "1,200"):
            self.assertNotIn(leak, r)

    def test_draft_check_uses_the_example_rules(self):
        self.assertFalse(twin.check("I think maybe we could perhaps look at it.")["passed"])

    def test_priorities_by_command(self):
        twin.ask("add call the electrician to my priorities", "recall")
        self.assertIn("call the electrician", [p["text"] for p in twin.priorities()])
        twin.ask("done with 1", "recall")
        self.assertTrue(all(p["done"] for p in twin.priorities()))

    def test_audit_reads_nothing_when_no_repo_is_listed(self):
        self.assertEqual(twin.audit()["read"], [])

    def test_mcp_server_lists_its_tools(self):
        msgs = [{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
                {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "twin_allowed", "arguments": {"action": "send the supplier email"}}}]
        out = subprocess.run([sys.executable, os.path.join(ROOT, "twin", "twin_mcp.py")], input="\n".join(json.dumps(m) for m in msgs) + "\n",
                             capture_output=True, text=True, timeout=60, env=dict(os.environ)).stdout.strip().splitlines()
        self.assertEqual(len(json.loads(out[1])["result"]["tools"]), 7)
        self.assertTrue(json.loads(json.loads(out[2])["result"]["content"][0]["text"])["needs_owner_yes"])


if __name__ == "__main__":
    unittest.main()
