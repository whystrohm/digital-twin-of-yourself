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

    def test_a_matching_limit_is_never_cleared(self):
        r = twin.allowed("change the price on order 12")
        self.assertTrue(r["needs_owner_yes"])
        self.assertTrue(r["matching_limits"])

    def test_sessions_are_off_until_turned_on(self):
        self.assertFalse(twin.state()["sessions_on"])
        self.assertEqual(twin.terminals(), ([], 0))

    def test_a_symlink_cannot_lead_out_of_the_notes_folder(self):
        d = tempfile.mkdtemp(); out = tempfile.mkdtemp(); secret = os.path.join(out, "secret.md")
        with open(secret, "w") as f: f.write("---\ndescription: The vault code is nine nine nine\narea: limits\n---\n")
        os.symlink(secret, os.path.join(d, "linked.md"))
        with open(os.path.join(d, "real.md"), "w") as f: f.write("---\ndescription: A real note about packing\narea: work\n---\n")
        keep = twin.CFG["memory"]; twin.CFG["memory"] = d; twin.IX.sig = None
        try: titles = [e["title"] for e in twin.IX.get().e]
        finally: twin.CFG["memory"] = keep; twin.IX.sig = None
        self.assertIn("A real note about packing", titles)
        self.assertFalse(any("vault" in x for x in titles))
        self.assertFalse(twin.inside(os.path.join(d, "linked.md"), d))

    def test_changes_are_logged(self):
        pid = twin.propose("Pallets are wrapped twice.", "decisions", "a test"); twin.settle(pid, True)
        rows = [r["action"] for r in twin.DB.execute("select action from log")]
        self.assertIn("proposal accepted", rows)

    def test_what_it_learns_is_a_plain_file(self):
        pid = twin.propose("Invoices go out on the first working day.", "decisions", "a test"); twin.settle(pid, True)
        files = [f for f in os.listdir(twin.NOTES) if "invoices-go-out" in f]
        self.assertEqual(len(files), 1)
        with open(os.path.join(twin.NOTES, files[0])) as f: raw = f.read()
        self.assertIn("source: a test", raw)
        self.assertIn("area: decisions", raw)

    def test_a_new_decision_can_replace_an_old_one_and_be_restored(self):
        twin.settle(twin.propose("Crates are stacked four high on the dock.", "decisions", "a test"), True)
        pid = twin.propose("Crates are stacked three high on the dock.", "decisions", "a test")
        clash = [p for p in twin.proposals() if p["id"] == pid][0]["conflict"]
        self.assertIn("four high", clash["title"])
        twin.settle(pid, True, True)
        titles = [e["title"] for e in twin.IX.get().e]
        self.assertIn("Crates are stacked three high on the dock.", titles)
        self.assertNotIn("Crates are stacked four high on the dock.", titles)
        self.assertTrue(twin.restore(clash["id"]))
        after = [e["title"] for e in twin.IX.get().e]
        self.assertIn("Crates are stacked four high on the dock.", after)
        self.assertNotIn("Crates are stacked three high on the dock.", after)       # only one of the two stays active

    def test_export_writes_plain_files(self):
        d = tempfile.mkdtemp(); twin.export(d)
        self.assertTrue(os.path.isfile(os.path.join(d, "memory.json")))
        self.assertTrue(os.path.isfile(os.path.join(d, "log.json")))

    def test_a_stale_approval_does_nothing(self):
        pid = twin.propose("Forklifts are charged overnight.", "decisions", "a test")
        row = [p for p in twin.proposals() if p["id"] == pid][0]
        self.assertIn("error", twin.settle(pid, True, False, "not-the-uid"))
        self.assertIn("error", twin.settle(pid, True, True, row["uid"], "own:some-other-note"))
        self.assertNotIn("Forklifts are charged overnight.", [e["title"] for e in twin.IX.get().e])
        self.assertEqual(twin.settle(pid, True, False, row["uid"]), {"ok": 1})

    def test_scopes_clash_unless_they_are_two_different_projects(self):
        twin.settle(twin.propose("Pallet tags are printed in blue ink.", "taste", "a test", "personal"), True)
        self.assertTrue(twin.conflict("Pallet tags are printed in red ink.", "taste", "brand"))
        twin.settle(twin.propose("Dock doors are painted grey here.", "taste", "a test", "project:north"), True)
        self.assertIsNone(twin.conflict("Dock doors are painted white here.", "taste", "project:south"))

    def test_accepting_twice_makes_one_file(self):
        a = twin.save_note("Gloves are worn on line two.", "limits", "a test", uid="abc123")
        b = twin.save_note("Gloves are worn on line two.", "limits", "a test", uid="abc123")
        self.assertEqual(a, b)

    def test_body_text_is_never_read_as_a_field(self):
        nid = twin.save_note("status: replaced", "decisions", "a test"); twin.IX.sig = None
        self.assertIn(nid, [e["id"] for e in twin.IX.get().e])

    def test_a_link_in_the_twins_own_notes_is_ignored(self):
        out = tempfile.mkdtemp(); secret = os.path.join(out, "s.md")
        with open(secret, "w") as f: f.write("---\ndescription: The safe is behind the boiler\narea: limits\n---\n\nx\n")
        os.symlink(secret, os.path.join(twin.NOTES, "linked.md")); twin.IX.sig = None
        try: self.assertFalse(any("boiler" in e["title"] for e in twin.IX.get().e))
        finally: os.remove(os.path.join(twin.NOTES, "linked.md")); twin.IX.sig = None

    def test_removing_a_source_removes_its_notes_in_a_running_process(self):
        self.assertTrue(twin.IX.search("do we ship on a friday")[1])
        keep = dict(twin.CFG); empty = tempfile.mkdtemp()
        try:
            with open(twin.CFG_PATH, "w") as f: json.dump(dict(keep, memory=empty), f)
            os.utime(twin.CFG_PATH, (1, 1))                     # another process saved new settings
            self.assertEqual([e for e in twin.IX.search("do we ship on a friday")[1] if e["src"] == "ship-days.md"], [])
        finally:
            with open(twin.CFG_PATH, "w") as f: json.dump(keep, f)
            os.utime(twin.CFG_PATH, (2, 2)); twin.sync_cfg()

    def test_a_bad_settings_change_applies_nothing(self):
        self.assertIn("error", twin.config({"rules": "/no/such/file.json", "read_sessions": True}))
        self.assertFalse(twin.CFG["read_sessions"])
        self.assertIn("error", twin.config({"read_sessions": "false"}))
        self.assertIn("error", twin.config({"name": 5}))

    def test_a_polite_request_is_still_a_request(self):
        self.assertTrue(twin.ask("Could you send the supplier email?", "recall")["gate"])
        self.assertFalse(twin.ask("should we send the supplier an email", "recall")["gate"])

    def test_shipped_history_follows_the_listed_repos(self):
        twin.DB.execute("insert or ignore into shipped values('abc','gone-repo','2999-01-01T00:00:00','old work')"); twin.DB.commit()
        self.assertEqual(twin.shipped(), [])

    def test_export_needs_an_empty_folder(self):
        d = tempfile.mkdtemp()
        with open(os.path.join(d, "mine.txt"), "w") as f: f.write("keep")
        with self.assertRaises(SystemExit): twin.export(d)

    def test_mcp_server_lists_its_tools(self):
        msgs = [{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
                {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "twin_allowed", "arguments": {"action": "send the supplier email"}}}]
        out = subprocess.run([sys.executable, os.path.join(ROOT, "twin", "twin_mcp.py")], input="\n".join(json.dumps(m) for m in msgs) + "\n",
                             capture_output=True, text=True, timeout=60, env=dict(os.environ)).stdout.strip().splitlines()
        self.assertEqual(len(json.loads(out[1])["result"]["tools"]), 7)
        self.assertTrue(json.loads(json.loads(out[2])["result"]["content"][0]["text"])["needs_owner_yes"])


if __name__ == "__main__":
    unittest.main()
