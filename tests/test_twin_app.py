"""The twin server, on the made-up sample. Offline. No model, no network."""
import json, os, subprocess, sys, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_fixtures = tempfile.TemporaryDirectory(prefix="twin-test-")
_previous_store = os.environ.get("TWIN_HOME")
os.environ["TWIN_HOME"] = os.path.join(_fixtures.name, "data")


def test_folder():
    return tempfile.mkdtemp(dir=_fixtures.name)


def tearDownModule():
    twin.DB.close()
    if _previous_store is None:
        os.environ.pop("TWIN_HOME", None)
    else:
        os.environ["TWIN_HOME"] = _previous_store
    _fixtures.cleanup()

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

    def test_setup_copy_describes_the_saved_sources_and_network_actions(self):
        from pathlib import Path
        from unittest.mock import patch
        with patch.dict(twin.CFG, read_sessions=True):
            inventory = twin.will_read().lower()
        self.assertIn("transcript", inventory)
        self.assertIn("last prompt", inventory)
        self.assertNotIn("nothing else", inventory)
        ui = Path(ROOT, "twin", "ui.html").read_text()
        for phrase in ("display name", "voice profile", "temporary copy", "account voices", "transcript", "last prompt"):
            with self.subTest(phrase=phrase): self.assertIn(phrase, ui.lower())
        self.assertNotIn("Nothing is uploaded unless a step says so", ui)

    def test_page_reloads_edited_entries_with_the_same_count(self):
        from pathlib import Path
        import shutil
        if not shutil.which("node"): self.skipTest("Node is needed for this page check")
        ui = Path(ROOT, "twin", "ui.html").read_text()
        refresh = ui[ui.index("async function refresh(full)"):ui.index("function fitName()")]
        shell = """
let S,E=[],idx={},stF=[],hot,pin,N=0,version=0;
const draw=()=>{},tl=()=>{};
const api=async()=>({ok:true,json:async()=>({terminals:[],entries:[
  {id:'one',title:version?'New decision':'Old decision',since:'2026-01-01'}]})});
"""
        verify = """
(async()=>{await refresh(); version++; await refresh();
  if(E[0].title!=='New decision') throw new Error('stale page entry')})()
"""
        proc = subprocess.run(["node", "-e", shell + refresh + verify], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_offline_suite_removes_its_test_folders(self):
        from pathlib import Path
        with tempfile.TemporaryDirectory() as folder:
            env = dict(os.environ, TMPDIR=folder, PYTHONDONTWRITEBYTECODE="1")
            proc = subprocess.run([sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-p",
                                   "test_twin_app.py", "-k", "test_an_open_session_loses"],
                                  cwd=ROOT, env=env, capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(list(Path(folder).iterdir()), [])

    def test_redaction(self):
        r = twin.redact("mail sam@example.com or call 617-555-0100, it cost $1,200")
        for leak in ("sam@example.com", "555-0100", "1,200"):
            self.assertNotIn(leak, r)

    def test_draft_check_uses_the_example_rules(self):
        self.assertFalse(twin.check("I think maybe we could perhaps look at it.")["passed"])

    def test_http_rejects_bad_shapes_without_dispatch(self):
        import io
        from unittest.mock import Mock
        for endpoint, body in (("ask", {"q": 2}), ("config", []), ("proposal", {"id": 1, "accept": "no", "uid": "old"}), ("teach", {"text": ""})):
            with self.subTest(endpoint=endpoint):
                data = json.dumps(body).encode()
                request = Mock(path="/api/" + endpoint, headers={"Content-Length": str(len(data))}, rfile=io.BytesIO(data))
                twin.H.do_POST(request)
                self.assertEqual(request.send.call_args.kwargs.get("code"), 400)

    def test_head_preflight_discards_original_and_busy_jobs_do_not_log_consent(self):
        from pathlib import Path
        from unittest.mock import Mock, patch
        with tempfile.TemporaryDirectory() as folder:
            head = Path(folder) / "head"
            with patch.object(twin, "HEAD", str(head)), patch.object(twin, "run", return_value='{"ok": true}'):
                self.assertTrue(twin.check_photo(b"sample")["ok"])
                self.assertFalse(list(head.glob("*")))
            with patch.dict(twin.BUILD, proc=Mock(**{"poll.return_value": None})), patch.object(twin, "audit_log") as log:
                self.assertIn("Already", twin.build_head(b"sample")["status"])
                log.assert_not_called()

    def test_head_builder_checks_permission_and_key_before_loading_models(self):
        import pathlib
        script = os.path.join(ROOT, "twin", "head", "build.py")
        with tempfile.TemporaryDirectory() as folder:
            dest = pathlib.Path(folder) / "output"
            for switches, reason in (([], "consent"), (["--consent"], "FAL_KEY")):
                job = subprocess.run([sys.executable, "-BS", script, "--photo", "example.jpg", "--out", str(dest)] + switches,
                                     env={k: v for k, v in os.environ.items() if k != "FAL_KEY"}, capture_output=True, text=True)
                self.assertNotEqual(job.returncode, 0)
                self.assertIn(reason, job.stderr)
                self.assertFalse(dest.exists())

    def test_local_reads_close_streams_and_respect_profile_filter(self):
        import gc, warnings
        from unittest.mock import patch
        with warnings.catch_warnings(record=True) as found, patch.object(twin, "claude", return_value=""), patch.object(twin, "state", return_value={"priorities": [], "repos": [], "shipped": []}):
            warnings.simplefilter("always", ResourceWarning)
            twin.think("What paper?", [], [])
            twin.rewrite("Use card stock.")
            gc.collect()
        self.assertFalse([str(w.message) for w in found if issubclass(w.category, ResourceWarning)])
        with patch.object(twin, "HARD", twin._Rx("sample private phrase", None)), patch.object(twin.subprocess, "run") as model:
            self.assertEqual(twin.claude("sample private phrase", "ordinary text"), "")
            model.assert_not_called()

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
        d = test_folder(); out = test_folder(); secret = os.path.join(out, "secret.md")
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
        d = test_folder(); twin.export(d)
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
        out = test_folder(); secret = os.path.join(out, "s.md")
        with open(secret, "w") as f: f.write("---\ndescription: The safe is behind the boiler\narea: limits\n---\n\nx\n")
        os.symlink(secret, os.path.join(twin.NOTES, "linked.md")); twin.IX.sig = None
        try: self.assertFalse(any("boiler" in e["title"] for e in twin.IX.get().e))
        finally: os.remove(os.path.join(twin.NOTES, "linked.md")); twin.IX.sig = None

    def test_removing_a_source_removes_its_notes_in_a_running_process(self):
        self.assertTrue(twin.IX.search("do we ship on a friday")[1])
        keep = dict(twin.CFG); empty = test_folder()
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
        d = test_folder()
        with open(os.path.join(d, "mine.txt"), "w") as f: f.write("keep")
        with self.assertRaises(SystemExit): twin.export(d)

    def test_an_open_session_loses_a_source_the_owner_removed(self):
        home = test_folder(); notes = test_folder(); empty = test_folder()
        with open(os.path.join(notes, "paint.md"), "w") as f: f.write("---\ndescription: The racking is painted signal orange\narea: taste\n---\n")
        cfg = os.path.join(home, "config.json")
        with open(cfg, "w") as f: json.dump({"memory": notes}, f)
        call = lambda i: json.dumps({"jsonrpc": "2.0", "id": i, "method": "tools/call", "params": {"name": "twin_recall", "arguments": {"question": "what colour is the racking painted"}}}) + "\n"
        p = subprocess.Popen([sys.executable, os.path.join(ROOT, "twin", "twin_mcp.py")], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, env=dict(os.environ, TWIN_HOME=home))
        try:
            p.stdin.write(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}) + "\n" + call(2)); p.stdin.flush()
            p.stdout.readline(); first = p.stdout.readline()
            self.assertIn("signal orange", first)
            with open(cfg) as f: now_cfg = json.load(f)
            with open(cfg, "w") as f: json.dump(dict(now_cfg, memory=empty), f)        # the owner removes the folder in the page
            os.utime(cfg, (5, 5))
            p.stdin.write(call(3)); p.stdin.flush()
            self.assertNotIn("signal orange", p.stdout.readline())
        finally:
            p.stdin.close(); p.wait(timeout=20); p.stdout.close()

    def test_an_older_data_folder_upgrades_without_losing_notes(self):
        twin.DB.execute("insert into taught(text,area,created) values('Returns are logged the same day.','work','2026-01-02T03:04:05')"); twin.DB.commit(); twin.IX.sig = None
        self.assertIn("Returns are logged the same day.", [e["title"] for e in twin.IX.get().e])
        self.assertEqual(twin.DB.execute("select count(*) from taught").fetchone()[0], 0)
        self.assertEqual(len([f for f in os.listdir(twin.NOTES) if "returns-are-logged" in f]), 1)

    def test_a_retry_after_a_crash_does_not_duplicate(self):
        pid = twin.propose("Bins are emptied at noon.", "work", "a test"); row = [p for p in twin.proposals() if p["id"] == pid][0]
        twin.save_note(row["text"], row["area"], row["source"], row["scope"], "", row["uid"])      # the file was written, then the process died
        self.assertEqual(twin.settle(pid, True, False, row["uid"]), {"ok": 1})
        self.assertEqual(len([f for f in os.listdir(twin.NOTES) if "bins-are-emptied" in f]), 1)
        self.assertEqual([p for p in twin.proposals() if p["id"] == pid], [])

    def test_mcp_server_lists_its_tools(self):
        msgs = [{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
                {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "twin_allowed", "arguments": {"action": "send the supplier email"}}}]
        out = subprocess.run([sys.executable, os.path.join(ROOT, "twin", "twin_mcp.py")], input="\n".join(json.dumps(m) for m in msgs) + "\n",
                             capture_output=True, text=True, timeout=60, env=dict(os.environ)).stdout.strip().splitlines()
        self.assertEqual(len(json.loads(out[1])["result"]["tools"]), 7)
        self.assertTrue(json.loads(json.loads(out[2])["result"]["content"][0]["text"])["needs_owner_yes"])


if __name__ == "__main__":
    unittest.main()
