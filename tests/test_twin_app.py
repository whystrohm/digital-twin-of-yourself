"""The twin server, on the made-up sample. Offline. No model, no network."""
import json, os, subprocess, sys, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class ValidationSafetyTests(unittest.TestCase):
    @staticmethod
    def load_validation(name):
        import contextlib, importlib.util, io
        from unittest import mock
        spec = importlib.util.spec_from_file_location("audit_" + name, os.path.join(ROOT, "validation", name + ".py"))
        module = importlib.util.module_from_spec(spec)
        with mock.patch("subprocess.run", return_value=subprocess.CompletedProcess([], 1, "", "")) as child:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                try: spec.loader.exec_module(module)
                except SystemExit: pass
        return module, child.call_count

    def test_importing_the_loop_does_not_start_paid_sessions(self):
        _, calls = self.load_validation("twin_loop")
        self.assertEqual(calls, 0)

    def test_a_failed_proof_child_fails_and_removes_its_data(self):
        import contextlib, io
        from unittest import mock
        module, _ = self.load_validation("twin_loop")
        self.assertTrue(callable(getattr(module, "main", None)))
        homes = []
        def child(cmd, **kw):
            homes.append(kw["cwd"])
            return subprocess.CompletedProcess(cmd, 3, "", "not a result")
        with mock.patch.object(module.subprocess, "run", side_effect=child):
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertNotEqual(module.main([]), 0)
        self.assertTrue(homes)
        self.assertTrue(all(not os.path.exists(p) for p in homes))

    def test_proof_answers_require_the_current_fact_and_source(self):
        module, _ = self.load_validation("twin_loop")
        self.assertTrue(callable(getattr(module, "answer_matches", None)))
        note = {"title": "Shipping labels are printed in dark green.", "src": "owner correction"}
        self.assertTrue(module.answer_matches({"colour": "dark green", "note": note["title"], "source": "owner correction"}, "dark green", note))
        self.assertFalse(module.answer_matches({"colour": "not green, use black", "note": note["title"], "source": "owner correction"}, "dark green", note))
        self.assertFalse(module.answer_matches({"colour": "dark green", "note": "Shipping labels are printed in black only.", "source": "owner correction"}, "dark green", note))
        self.assertFalse(module.answer_matches({"colour": "dark green", "note": note["title"], "source": "made up"}, "dark green", note))

    def test_proof_tool_use_requires_a_success_from_the_caller_whose_count_changed(self):
        module, _ = self.load_validation("twin_loop")
        before = {"clients": [{"name": "reader", "calls": 5, "last_tool": "twin_recall", "last_result": "ok"},
                              {"name": "other", "calls": 1, "last_tool": "twin_allowed", "last_result": "ok"}]}
        unrelated = {"clients": [dict(before["clients"][0]), dict(before["clients"][1], calls=2)]}
        self.assertFalse(module.LoopProof.used_tool(before, unrelated, "twin_recall"))
        failed = {"clients": [dict(before["clients"][0], calls=6, last_result="error")]}
        self.assertFalse(module.LoopProof.used_tool(before, failed, "twin_recall"))
        successful = {"clients": [dict(before["clients"][0], calls=6)]}
        self.assertTrue(module.LoopProof.used_tool(before, successful, "twin_recall"))

    def test_the_proof_checks_real_owner_state_with_an_offline_client(self):
        import contextlib, io
        from unittest import mock
        module, _ = self.load_validation("twin_loop")
        self.assertTrue(callable(getattr(module, "main", None)))
        real_run = subprocess.run
        def child(cmd, **kw):
            if cmd[0] != "claude":
                return real_run(cmd, **kw)
            answer = {"colour": "unknown", "note": "", "source": ""}
            if "--mcp-config" in cmd:
                proposing = "twin_propose_note" in kw["input"]
                text = module.GREEN if module.GREEN in kw["input"] else module.BLACK
                name = "twin_propose_note" if proposing else "twin_recall"
                args = {"text": text, "area": "taste", "scope": "personal"} if proposing else {"question": "what colour shipping labels"}
                messages = [{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"clientInfo": {"name": "offline-fixture"}}},
                            {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": name, "arguments": args}}]
                run = real_run([sys.executable, os.path.join(ROOT, "twin", "twin_mcp.py")],
                               input="\n".join(json.dumps(m) for m in messages) + "\n", text=True,
                               capture_output=True, timeout=60, cwd=kw["cwd"], env=kw["env"])
                if run.returncode:
                    return run
                response = json.loads(json.loads(run.stdout.splitlines()[-1])["result"]["content"][0]["text"])
                if proposing:
                    answer = {"proposed": response["proposed"]}
                else:
                    notes = [n for n in response.get("notes", []) if n["note"] in (module.BLACK, module.GREEN)]
                    if notes:
                        note = notes[0]
                        answer = {"colour": "dark green" if note["note"] == module.GREEN else "black", "note": note["note"], "source": note["source"]}
            return subprocess.CompletedProcess(cmd, 0, json.dumps(answer), "")
        output = io.StringIO()
        with mock.patch.object(module.subprocess, "run", side_effect=child):
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
                code = module.main([])
        self.assertEqual(code, 0, output.getvalue())

    def test_evaluator_never_reads_a_sample_outside_the_selected_folder(self):
        from unittest import mock
        module, _ = self.load_validation("twin_eval")
        with tempfile.TemporaryDirectory() as d:
            selected = os.path.join(d, "selected"); os.mkdir(selected)
            inside = os.path.join(selected, "normal.md"); outside = os.path.join(d, "outside.md")
            with open(inside, "w") as f: f.write("Ordinary sample writing.")
            with open(outside, "w") as f: f.write("Outside sample content.")
            with mock.patch.object(module.tl, "list_text_files", return_value=[outside, inside]):
                result = module.read_samples(selected, 12000)
            self.assertIn("Ordinary sample writing.", result)
            self.assertNotIn("Outside sample content.", result)

    def test_a_missing_second_judgement_is_not_counted_as_a_win(self):
        import contextlib, io
        from unittest import mock
        module, _ = self.load_validation("twin_eval")
        with tempfile.TemporaryDirectory() as d:
            profile = os.path.join(d, "profile.md"); out = os.path.join(d, "result.json")
            with open(profile, "w") as f: f.write("Use short plain sentences.")
            replies = [("A generic answer.", {}, "end_turn"), ("A personal answer.", {}, "end_turn"),
                       ('{"winner":"A","confidence":3,"reason":"Shorter."}', {}, "end_turn"),
                       (None, {}, "refusal")]
            with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "offline-fixture"}), mock.patch.object(module, "call", side_effect=replies):
                with contextlib.redirect_stdout(io.StringIO()):
                    code = module.main(["--twin", profile, "--tests", "ST-01", "--both-orders", "--out", out])
            with open(out) as f: result = json.load(f)
            self.assertEqual(result["summary"]["twin_wins"], 0)
            self.assertEqual(result["summary"]["errors"], 1)
            self.assertFalse(result["complete"])
            self.assertNotEqual(code, 0)

    @staticmethod
    def evaluator_message(text, stop="end_turn"):
        return {"id": "msg_offline_fixture", "type": "message", "role": "assistant", "model": "offline-fixture",
                "content": [{"type": "text", "text": text}], "stop_reason": stop, "stop_sequence": None,
                "usage": {"input_tokens": 3, "output_tokens": 2}}

    def evaluator_with_transport(self, messages):
        import contextlib, io
        from unittest import mock
        module, _ = self.load_validation("twin_eval")
        with tempfile.TemporaryDirectory() as d:
            profile = os.path.join(d, "profile.md"); out = os.path.join(d, "result.json")
            with open(profile, "w") as f: f.write("Use short plain sentences.")
            responses = [io.BytesIO(json.dumps(message).encode()) for message in messages]
            try:
                with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "offline-fixture"}), mock.patch.object(module.urllib.request, "urlopen", side_effect=responses):
                    with contextlib.redirect_stdout(io.StringIO()):
                        code = module.main(["--twin", profile, "--tests", "ST-01", "--out", out])
                with open(out) as f: result = json.load(f)
            finally:
                for response in responses: response.close()
        return code, result

    def test_truncated_generation_is_not_judged_as_a_complete_answer(self):
        code, result = self.evaluator_with_transport([
            self.evaluator_message("A partial generic answer", "max_tokens"),
            self.evaluator_message("A complete personal answer."),
            self.evaluator_message('{"winner":"A","confidence":3,"reason":"Shorter."}')])
        self.assertEqual(code, 1)
        self.assertFalse(result["complete"])
        self.assertEqual(result["summary"]["errors"], 1)
        self.assertEqual(result["summary"]["twin_wins"] + result["summary"]["generic_wins"], 0)
        self.assertIn("max_tokens", result["tests"][0]["error"])

    def test_truncated_judge_output_does_not_count_even_if_its_json_parses(self):
        code, result = self.evaluator_with_transport([
            self.evaluator_message("A complete generic answer."),
            self.evaluator_message("A complete personal answer."),
            self.evaluator_message('{"winner":"A","confidence":3,"reason":"Shorter."}', "max_tokens")])
        self.assertEqual(code, 1)
        self.assertFalse(result["complete"])
        self.assertEqual(result["tests"][0]["result"], "error")
        self.assertEqual(result["tests"][0]["verdicts"][0]["stop"], "max_tokens")

    def test_missing_generation_content_or_stop_reason_is_not_graded(self):
        missing_text = self.evaluator_message("Unused."); missing_text.pop("content")
        missing_stop = self.evaluator_message("Looks complete."); missing_stop.pop("stop_reason")
        for message, expected in [(missing_text, "empty_response"), (missing_stop, "missing_stop_reason")]:
            with self.subTest(missing=expected):
                code, result = self.evaluator_with_transport([
                    message, self.evaluator_message("A complete personal answer."),
                    self.evaluator_message('{"winner":"A","confidence":3,"reason":"Shorter."}')])
                self.assertEqual(code, 1)
                self.assertFalse(result["complete"])
                self.assertIn(expected, result["tests"][0]["error"])

    def test_evaluation_docs_do_not_guarantee_that_every_judge_reply_parses(self):
        with open(os.path.join(ROOT, "validation", "EVAL.md")) as f: text = f.read()
        self.assertNotIn("reply always parses", text)

    def test_evaluator_refuses_linked_ancestors_before_discovering_samples(self):
        from pathlib import Path
        from unittest import mock
        module, _ = self.load_validation("twin_eval")
        with tempfile.TemporaryDirectory(dir="/tmp") as folder:
            root = Path(folder)
            selected = root / "original" / "samples"
            selected.mkdir(parents=True)
            sample = selected / "nested" / "story.md"
            sample.parent.mkdir()
            sample.write_text("Ordinary reference writing.", encoding="utf-8")
            self.assertIn("Ordinary reference writing.", module.read_samples(selected, 100))
            (root / "alias").symlink_to(selected.parent, target_is_directory=True)
            linked = root / "alias" / "samples"
            with self.subTest(action="read"):
                with self.assertRaises((OSError, ValueError)):
                    module.tl.read_text(linked / "nested" / "story.md", root=linked)
            with self.subTest(action="discover"):
                with mock.patch.object(os, "scandir", wraps=os.scandir) as visits:
                    self.assertEqual(module.read_samples(linked, 100), "")
                    visits.assert_not_called()



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


class TwinPersistence(unittest.TestCase):
    """Owner decisions survive retries and retain the reviewed source."""

    def setUp(self):
        import importlib.util
        from unittest.mock import patch
        self.tmp = tempfile.TemporaryDirectory(prefix="twin-persistence-")
        self.addCleanup(self.tmp.cleanup)
        for name in ("home", "data", "source", "tmp"):
            os.mkdir(os.path.join(self.tmp.name, name))
        self.env = patch.dict(os.environ, HOME=os.path.join(self.tmp.name, "home"),
                              TWIN_HOME=os.path.join(self.tmp.name, "data"),
                              TMPDIR=os.path.join(self.tmp.name, "tmp"),
                              PYTHONDONTWRITEBYTECODE="1")
        self.env.start(); self.addCleanup(self.env.stop)
        with open(os.path.join(self.tmp.name, "data", "config.json"), "w") as f:
            json.dump({"memory": os.path.join(self.tmp.name, "source"), "read_sessions": False}, f)
        spec = importlib.util.spec_from_file_location("twin_persistence_fixture", os.path.join(ROOT, "twin", "twin.py"))
        self.app = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.app)
        self.addCleanup(self.app.DB.close)

    def proposal(self, text="The loading gate closes at six.", source="fixture client", scope="personal"):
        pid = self.app.propose(text, "work", source, scope)
        return next(p for p in self.app.proposals() if p["id"] == pid)

    def test_proposal_ids_are_not_reused_after_a_drop(self):
        first = self.proposal()
        self.app.settle(first["id"], False, uid=first["uid"])
        second = self.proposal("The loading gate opens at seven.")
        self.assertGreater(second["id"], first["id"])

    def test_approval_checks_the_reviewed_proposal_revision(self):
        row = self.proposal()
        self.app.DB.execute("update proposed set text=? where id=?", ("The loading gate closes at eight.", row["id"]))
        self.app.DB.commit()
        result = self.app.settle(row["id"], True, uid=row["uid"], revision=row["revision"])
        self.assertIn("error", result)
        self.assertEqual(os.listdir(self.app.NOTES), [])

    def test_approval_checks_the_reviewed_old_note_revision(self):
        old = self.app.save_note("The loading gate closes at five.", "work", "fixture")
        self.app.IX.sig = None
        row = self.proposal()
        with open(os.path.join(self.app.NOTES, old[4:] + ".md"), "a") as f:
            f.write("\nAn owner clarification.\n")
        result = self.app.settle(row["id"], True, True, row["uid"], old,
                                 row["revision"], row["conflict"]["revision"])
        self.assertIn("error", result)
        self.assertEqual(len(os.listdir(self.app.NOTES)), 1)

    def test_accept_log_keeps_source_scope_and_ids(self):
        row = self.proposal("Loading gates remain closed. " + "Use the marked entrance. " * 18,
                            "fixture client with a durable source", "project:warehouse")
        self.app.settle(row["id"], True, uid=row["uid"])
        log = self.app.DB.execute("select * from log where action='proposal accepted'").fetchone()
        self.assertEqual(log["source"], row["source"])
        self.assertEqual(log["scope"], row["scope"])
        self.assertEqual(log["proposal_uid"], row["uid"])
        self.assertTrue(log["note_id"].startswith("own:"))

    def test_legacy_migration_reuses_a_staged_file_and_date(self):
        text = "The loading gate closes at four."
        self.app.DB.execute("insert into taught(id,text,area,created) values(?,?,?,?)", (17, text, "work", "2026-01-02T03:04:05"))
        self.app.DB.commit()
        self.app.save_note(text, "work", "taught in the page", uid="legacy-17", accepted="2026-01-02T03:04:05")
        self.app.IX.sig = None
        entries = [e for e in self.app.IX.get().e if e["title"] == text]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["since"], "2026-01-02")
        self.assertEqual(self.app.DB.execute("select count(*) from taught").fetchone()[0], 0)

    def test_acceptance_recovers_after_a_local_write_error(self):
        from unittest.mock import patch
        row = self.proposal()
        original = self.app.save_note
        def saved_then_interrupted(*args, **kwargs):
            original(*args, **kwargs)
            raise OSError("fixture interrupted after writing")
        with patch.object(self.app, "save_note", side_effect=saved_then_interrupted):
            with self.assertRaises(OSError): self.app.settle(row["id"], True, uid=row["uid"])
        self.app.DB.close()
        import sqlite3
        self.app.DB = sqlite3.connect(os.path.join(self.app.STORE, "twin.db"), check_same_thread=False)
        self.app.DB.row_factory = sqlite3.Row
        self.addCleanup(self.app.DB.close)
        self.app.IX.sig = None
        entries = [e for e in self.app.IX.get().e if e["title"] == row["text"]]
        self.assertEqual(len(entries), 1)
        self.assertEqual(self.app.proposals(), [])
        self.assertEqual(self.app.settle(row["id"], True, uid=row["uid"]), {"ok": 1})

    def test_missing_imported_source_is_not_reported_as_restored(self):
        path = os.path.join(self.app.CFG["memory"], "gate.md")
        with open(path, "w") as f:
            f.write("---\ndescription: The loading gate closes at five.\narea: work\n---\n\nThe prior decision.\n")
        row = self.proposal()
        old_id = row["conflict"]["id"]
        self.app.settle(row["id"], True, True, row["uid"])
        os.remove(path)
        self.assertFalse(self.app.restore(old_id))
        self.assertIsNotNone(self.app.DB.execute("select * from replaced where old_id=?", (old_id,)).fetchone())

    def test_legacy_migration_preserves_an_outdated_verdict(self):
        text = "The loading gate closes at two."
        self.app.DB.execute("insert into taught(id,text,area,created) values(18,?,'work','2026-01-02T03:04:05')", (text,))
        self.app.DB.execute("insert into review values('taught:18','outdated','2026-01-03T03:04:05')")
        self.app.DB.commit(); self.app.IX.sig = None
        self.assertNotIn(text, [e["title"] for e in self.app.IX.get().e])
        self.assertEqual(self.app.DB.execute("select count(*) from taught").fetchone()[0], 0)

    def test_replacement_recovers_after_the_old_status_was_written(self):
        from unittest.mock import patch
        old = self.app.save_note("The loading gate closes at five.", "work", "fixture")
        self.app.IX.sig = None; row = self.proposal(); original = self.app.set_status
        def changed_then_interrupted(*args, **kwargs):
            original(*args, **kwargs)
            raise OSError("fixture interrupted after the old status")
        with patch.object(self.app, "set_status", side_effect=changed_then_interrupted):
            with self.assertRaises(OSError): self.app.settle(row["id"], True, True, row["uid"])
        self.app.recover_memory_ops(); self.app.IX.sig = None
        titles = [e["title"] for e in self.app.IX.get().e]
        self.assertIn(row["text"], titles)
        self.assertNotIn("The loading gate closes at five.", titles)
        replaced = self.app.state()["replaced"]
        self.assertEqual(replaced[0]["old_id"], old)
        self.assertNotIn("snapshot", replaced[0])
        self.assertIn("revision", replaced[0])
        self.assertFalse(self.app.restore(old, replaced[0]["by_id"], "stale revision"))

    def test_restore_recovers_after_the_old_note_was_reactivated(self):
        from unittest.mock import patch
        old = self.app.save_note("The loading gate closes at five.", "work", "fixture")
        self.app.IX.sig = None; row = self.proposal()
        self.app.settle(row["id"], True, True, row["uid"]); original = self.app.set_status
        def changed_then_interrupted(*args, **kwargs):
            original(*args, **kwargs)
            raise OSError("fixture interrupted during restore")
        with patch.object(self.app, "set_status", side_effect=changed_then_interrupted):
            with self.assertRaises(OSError): self.app.restore(old)
        self.app.recover_memory_ops(); self.app.IX.sig = None
        titles = [e["title"] for e in self.app.IX.get().e]
        self.assertIn("The loading gate closes at five.", titles)
        self.assertNotIn(row["text"], titles)

    def test_imported_decision_can_be_replaced_and_restored(self):
        path = os.path.join(self.app.CFG["memory"], "gate.md")
        with open(path, "w") as f:
            f.write("---\ndescription: The loading gate closes at five.\narea: work\n---\n\nThe prior decision.\n")
        row = self.proposal(); old = row["conflict"]["id"]
        self.app.settle(row["id"], True, True, row["uid"])
        self.assertTrue(self.app.restore(old))
        titles = [e["title"] for e in self.app.IX.get().e]
        self.assertIn("The loading gate closes at five.", titles)
        self.assertNotIn(row["text"], titles)
        self.assertEqual(self.app.DB.execute("select count(*) from memory_ops where state='pending'").fetchone()[0], 0)
        newer = self.app.state()["replaced"][0]
        self.assertTrue(self.app.restore(newer["old_id"], newer["by_id"], newer["revision"]))
        titles = [e["title"] for e in self.app.IX.get().e]
        self.assertIn(row["text"], titles)
        self.assertNotIn("The loading gate closes at five.", titles)

    def test_pending_replacement_preserves_an_owner_edit(self):
        from unittest.mock import patch
        old = self.app.save_note("The loading gate closes at five.", "work", "fixture")
        self.app.IX.sig = None; row = self.proposal(); original = self.app.save_note
        def saved_then_interrupted(*args, **kwargs):
            original(*args, **kwargs)
            raise OSError("fixture interrupted before replacing")
        with patch.object(self.app, "save_note", side_effect=saved_then_interrupted):
            with self.assertRaises(OSError): self.app.settle(row["id"], True, True, row["uid"])
        path = os.path.join(self.app.NOTES, old[4:] + ".md")
        with open(path, "a") as f: f.write("\nAn owner edit after interruption.\n")
        before = self.app.read_note(path, self.app.NOTES)
        self.app.recover_memory_ops(); self.app.IX.sig = None
        self.assertEqual(self.app.read_note(path, self.app.NOTES), before)
        self.assertNotIn(row["text"], [e["title"] for e in self.app.IX.get().e])
        self.assertEqual(self.app.DB.execute("select count(*) from memory_ops where state='pending'").fetchone()[0], 0)
        self.assertNotEqual(self.app.proposals()[0]["uid"], row["uid"])

    def test_pending_replacement_cannot_follow_a_source_switch(self):
        from unittest.mock import patch
        path = os.path.join(self.app.CFG["memory"], "gate.md")
        with open(path, "w") as f:
            f.write("---\ndescription: The loading gate closes at five.\narea: work\n---\n\nThe prior decision.\n")
        row = self.proposal(); original = self.app.save_note
        def saved_then_interrupted(*args, **kwargs):
            original(*args, **kwargs)
            raise OSError("fixture interrupted before replacing")
        with patch.object(self.app, "save_note", side_effect=saved_then_interrupted):
            with self.assertRaises(OSError): self.app.settle(row["id"], True, True, row["uid"])
        other = os.path.join(self.app.HOME, "other-notes"); os.mkdir(other)
        with open(os.path.join(other, "gate.md"), "w") as f:
            f.write("---\ndescription: The packing line opens at nine.\narea: work\n---\n\nAn unrelated decision.\n")
        with open(self.app.CFG_PATH, "w") as f: json.dump(dict(self.app.CFG, memory=other), f)
        self.app.sync_cfg(); self.app.recover_memory_ops(); self.app.IX.sig = None
        titles = [e["title"] for e in self.app.IX.get().e]
        self.assertIn("The packing line opens at nine.", titles)
        self.assertNotIn(row["text"], titles)
        self.assertEqual(self.app.DB.execute("select count(*) from memory_ops where state='pending'").fetchone()[0], 0)

    def test_imported_verdicts_do_not_follow_a_same_named_file(self):
        path = os.path.join(self.app.CFG["memory"], "gate.md")
        with open(path, "w") as f: f.write("---\ndescription: The gate closes at five.\narea: work\n---\n")
        old = next(e for e in self.app.IX.get().e if e["src"] == "gate.md")
        self.app.DB.execute("insert into review values(?,'outdated','2026-01-03T03:04:05')", (old["id"],))
        self.app.DB.execute("insert into review values('gate','outdated','2026-01-03T03:04:05')")
        self.app.DB.commit()
        other = os.path.join(self.app.HOME, "other-notes"); os.mkdir(other)
        with open(os.path.join(other, "gate.md"), "w") as f:
            f.write("---\ndescription: The packing line opens at nine.\narea: work\n---\n")
        with open(self.app.CFG_PATH, "w") as f: json.dump(dict(self.app.CFG, memory=other), f)
        self.app.sync_cfg(); self.app.IX.sig = None
        self.assertIn("The packing line opens at nine.", [e["title"] for e in self.app.IX.get().e])


class TwinApp(unittest.TestCase):
    @unittest.skipUnless(
        os.path.isfile(os.path.join(os.environ.get("TWIN_SITE_TEST_ROOT", os.path.join(os.path.dirname(ROOT), "whystrohm-twin")), "src", "app", "twin", "page.tsx")),
        "Set TWIN_SITE_TEST_ROOT to a site checkout to check the public Twin page.",
    )
    def test_site_twin_disclosures_and_route_contract(self):
        import re

        site = os.environ.get("TWIN_SITE_TEST_ROOT", os.path.join(os.path.dirname(ROOT), "whystrohm-twin"))
        sources = {}
        for name in ("src/app/twin/page.tsx", "src/lib/nav.ts", "src/app/sitemap.ts", "scripts/write-route-lastmod.mjs"):
            with open(os.path.join(site, name), encoding="utf-8") as f:
                sources[name] = f.read()
        page = sources["src/app/twin/page.tsx"]
        for promise in ("Nothing becomes part of it until you accept it", "Before it reads anything", "no code that writes to, moves or deletes your files", "at all times"):
            with self.subTest(promise=promise):
                self.assertNotIn(promise, page)
        rows = {
            setting.lower(): (what + " " + where).lower()
            for setting, what, where in re.findall(r'\{ setting: "([^"]+)", what: "([^"]+)", where: "([^"]+)" \}', page)
        }
        for topic, fields in (
            ("answers by claude", ("name", "notes", "priorities", "repo", "shipped", "profile")),
            ("rewrite", ("draft", "rules", "profile", "notes-only")),
            ("elevenlabs voice", ("reply", "preview", "voice id")),
            ("voice list", ("key", "elevenlabs")),
            ("cloning", ("recording", "name", "description", "request")),
            ("building", ("photo", "poll", "mesh")),
            ("model downloads", ("github", "weights", "cache")),
            ("coding sessions", ("notes", "sources", "work", "client")),
        ):
            with self.subTest(disclosure=topic):
                matching = [value for key, value in rows.items() if topic in key]
                self.assertEqual(len(matching), 1)
                for field in fields:
                    self.assertIn(field, matching[0])
        for explanation in ("transcript", "self-attestation", "source files", "imported notes", "summary", "model cache"):
            with self.subTest(explanation=explanation):
                self.assertIn(explanation, page.lower())
        self.assertTrue(re.search(r"macOS or Linux[^\n]*Python 3\.9 or newer", page), "State the supported host platforms beside the Python prerequisite.")
        self.assertRegex(page, r"<LazyFilm\b[\s\S]*?\bcontrols\b[\s\S]*?/>")
        self.assertRegex(page, r'<main\b[^>]*\bid="main"[^>]*\bdata-nx=')
        self.assertRegex(sources["src/lib/nav.ts"], r'href:\s*"/twin"')
        self.assertRegex(sources["src/app/sitemap.ts"], r'path:\s*"/twin"')
        self.assertRegex(sources["scripts/write-route-lastmod.mjs"], r'"/twin":\s*"src/app/twin/page\.tsx"')

    def test_sample_notes_load_into_every_area(self):
        e = twin.IX.get().e
        self.assertGreaterEqual(len(e), 15)
        self.assertEqual({x["area"] for x in e}, set(twin.AREAS))

    def test_recall_finds_the_note_and_its_source(self):
        level, ev = twin.IX.search("do we ship on a friday")
        self.assertIn(level, ("strong", "some"))
        self.assertEqual(ev[0]["src"], "ship-days.md")
        self.assertIn("weekend", ev[0]["why"])

    def test_changed_profile_and_rules_stop_model_calls(self):
        from unittest.mock import patch
        with patch.object(twin, "_regular_file", side_effect=OSError("selected file unavailable")), patch.object(twin, "claude") as model:
            self.assertIn("error", twin.rewrite("Use card stock."))
            self.assertIn("error", twin.check("Use card stock."))
            self.assertEqual(twin.think("Which paper?", [], []), "")
            model.assert_not_called()

    def test_repo_scan_skips_an_instruction_file_removed_during_read(self):
        from pathlib import Path
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as folder:
            fp = Path(folder, "AGENTS.md")
            fp.write_text("- Always keep packing slips in the blue folder.")
            def resolve(path, root):
                if path == str(fp) and fp.exists(): fp.unlink()
                return True
            with patch.dict(twin.CFG, repos=[folder]), patch.object(twin, "inside", side_effect=resolve):
                self.assertEqual(twin.scan_repos()["proposed"], 0)

    def test_embedded_privacy_summary_points_to_the_data_table(self):
        self.assertIn("docs/TWIN.md", twin.__doc__)
        self.assertNotIn("Nothing leaves this machine except", twin.__doc__)

    def test_no_evidence_is_an_answer(self):
        a = twin.ask("what is our policy on office plants", "recall")
        self.assertEqual(a["level"], "not enough")
        self.assertEqual(a["sources"], [])

    def test_review_buttons_submit_the_versions_that_were_shown(self):
        from pathlib import Path
        ui = Path(ROOT, "twin", "ui.html").read_text()
        for value in ("p.revision", "p.conflict.revision", "old_revision:", "x.revision", "by_id:"):
            with self.subTest(value=value): self.assertIn(value, ui)
        self.assertIn("revision:", ui.split("api('restore'", 1)[1].split(")).json()", 1)[0])

    def test_restore_without_reviewed_version_is_rejected(self):
        import io
        from unittest.mock import Mock, patch
        raw = b'{"id":"obsolete"}'
        request = Mock(path="/api/restore", headers={"Content-Length": str(len(raw))}, rfile=io.BytesIO(raw))
        with patch.object(twin, "restore") as restore:
            twin.H.do_POST(request)
            self.assertEqual(request.send.call_args.kwargs.get("code"), 400)
            restore.assert_not_called()

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

    def _shared_settings_case(self, body):
        with tempfile.TemporaryDirectory(prefix="twin-settings-", dir="/tmp") as td:
            home = os.path.realpath(os.path.join(td, "home"))
            data = os.path.realpath(os.path.join(td, "data"))
            scratch = os.path.realpath(os.path.join(td, "tmp"))
            for folder in (home, data, scratch): os.makedirs(folder)
            env = {k: v for k, v in os.environ.items() if not any(s in k.upper() for s in ("KEY", "TOKEN", "SECRET"))}
            env.update(HOME=home, TWIN_HOME=data, TMPDIR=scratch, XDG_CACHE_HOME=os.path.join(scratch, "cache"), PYTHONDONTWRITEBYTECODE="1")
            start = "import json, os, sqlite3, sys\nfrom unittest import mock\nsys.path.insert(0, 'twin')\nimport twin\n"
            result = subprocess.run([sys.executable, "-B", "-c", start + body], cwd=ROOT, env=env,
                                    capture_output=True, text=True, timeout=12)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_shared_settings_reload_even_when_mtime_is_reused(self):
        self._shared_settings_case("""
before = os.stat(twin.CFG_PATH)
with open(twin.CFG_PATH) as f: settings = json.load(f)
settings['name'] = 'Nora'
with open(twin.CFG_PATH, 'w') as f: json.dump(settings, f)
os.utime(twin.CFG_PATH, ns=(before.st_atime_ns, before.st_mtime_ns))
twin.sync_cfg()
assert twin.CFG['name'] == 'Nora'
""")

    def test_shared_settings_save_preserves_a_newer_writer(self):
        self._shared_settings_case("""
with open(twin.CFG_PATH) as f: settings = json.load(f)
settings['name'] = 'Nora'
with open(twin.CFG_PATH, 'w') as f: json.dump(settings, f)
result = twin.config({'read_sessions': False})
assert 'error' not in result, result
assert twin.CFG['name'] == 'Nora'
with open(twin.CFG_PATH) as f: assert json.load(f)['name'] == 'Nora'
""")

    def test_shared_settings_failed_save_applies_nothing(self):
        self._shared_settings_case("""
before = dict(twin.CFG)
logs = twin.DB.execute('select count(*) from log').fetchone()[0]
replace = os.replace
def fail_config(source, target):
    if target == twin.CFG_PATH: raise OSError('synthetic disk failure')
    return replace(source, target)
with mock.patch.object(os, 'replace', side_effect=fail_config):
    try: twin.config({'name': 'Nora', 'read_sessions': True})
    except OSError: pass
assert twin.CFG == before
assert twin.DB.execute('select count(*) from log').fetchone()[0] == logs
assert not os.path.exists(twin.CFG_PATH + '.tmp')
""")

    def test_shared_settings_lock_can_be_nested(self):
        self._shared_settings_case("""
with twin.locked():
    with twin.locked():
        pass
""")

    def test_shared_settings_repo_identity_revokes_same_named_source(self):
        self._shared_settings_case("""
first = os.path.join(twin.HOME, 'first', 'shared')
second = os.path.join(twin.HOME, 'second', 'shared')
for folder in (first, second): os.makedirs(os.path.join(folder, '.git'))
def sample_git(args, cwd, timeout=8):
    if args[:1] == ['log'] and '--since=30.days' in args:
        return 'abc123|2999-01-01T00:00:00|Synthetic work from the first repo'
    if args[:1] == ['rev-parse'] and '-q' in args: return 'abc123'
    if args[:1] == ['log']: return '2999-01-01T00:00:00|Synthetic work'
    return ''
twin.CFG['repos'] = [first]
with mock.patch.object(twin, 'git', side_effect=sample_git): twin.repos()
assert len(twin.shipped()) == 1
twin.CFG['repos'] = [second]
assert twin.shipped() == []
""")

    def test_shared_settings_review_revision_is_seen_across_processes(self):
        self._shared_settings_case("""
note = twin.IX.search('do we ship on a friday')[1][0]
other = sqlite3.connect(os.path.join(twin.STORE, 'twin.db'))
other.execute('insert or replace into review values(?,?,?)', (note['id'], 'true', '2026-01-01T00:00:00'))
other.commit()
assert any(e['id'] == note['id'] for e in twin.IX.get().e)
other.execute('update review set verdict=? where key=?', ('outdated', note['id']))
other.commit()
assert not any(e['id'] == note['id'] for e in twin.IX.get().e)
other.close()
""")

    def test_shared_settings_unknown_action_is_not_permission(self):
        self._shared_settings_case("""
result = twin.allowed('rename a local variable')
assert result['needs_owner_yes'] is None
assert result['verdict'] == 'no_rule_found'
""")

    def test_shared_settings_filter_reload_precedes_chat(self):
        self._shared_settings_case("""
with open(twin.CFG_PATH) as f: settings = json.load(f)
settings['never'] = 'synthetic copper'
with open(twin.CFG_PATH, 'w') as f: json.dump(settings, f)
result = twin.ask('synthetic copper status', 'recall')
assert result['gate'] is True
assert twin.DB.execute('select count(*) from chat').fetchone()[0] == 0
""")

    def test_shared_settings_startup_refuses_a_dangling_config_link(self):
        self._shared_settings_case("""
child = os.path.join(twin.HOME, 'child-store'); os.mkdir(child)
outside = os.path.join(twin.HOME, 'outside-config.json')
os.symlink(outside, os.path.join(child, 'config.json'))
env = dict(os.environ, TWIN_HOME=child)
result = __import__('subprocess').run([sys.executable, '-B', '-c', "import sys; sys.path.insert(0, 'twin'); import twin"],
                                    cwd=os.getcwd(), env=env, capture_output=True, text=True, timeout=5)
assert result.returncode != 0
assert not os.path.exists(outside)
""")

    def test_shared_settings_startup_rejects_invalid_session_type(self):
        self._shared_settings_case("""
child = os.path.join(twin.HOME, 'child-store'); os.mkdir(child)
with open(os.path.join(child, 'config.json'), 'w') as f: json.dump({'read_sessions': 'false'}, f)
env = dict(os.environ, TWIN_HOME=child)
result = __import__('subprocess').run([sys.executable, '-B', '-c', "import sys; sys.path.insert(0, 'twin'); import twin"],
                                    cwd=os.getcwd(), env=env, capture_output=True, text=True, timeout=5)
assert result.returncode != 0
""")

    def test_shared_settings_session_revocation_clears_cached_records(self):
        self._shared_settings_case("""
sessions = os.path.join(twin.HOME, '.claude', 'sessions')
project = os.path.join(twin.HOME, '.claude', 'projects', 'sample-project')
os.makedirs(sessions); os.makedirs(project)
record = {'pid': os.getpid(), 'sessionId': 'sample-session', 'cwd': twin.HOME, 'status': 'busy'}
with open(os.path.join(sessions, 'sample.json'), 'w') as f: json.dump(record, f)
with open(os.path.join(project, 'sample-session.jsonl'), 'w') as f:
    f.write(json.dumps({'aiTitle': 'Synthetic packing session'}, separators=(',', ':')))
assert 'error' not in twin.config({'read_sessions': True})
assert twin.cached('t', 100, twin.terminals)[0][0]['title'] == 'Synthetic packing session'
before = os.stat(twin.CFG_PATH)
with open(twin.CFG_PATH) as f: settings = json.load(f)
settings['read_sessions'] = False
with open(twin.CFG_PATH, 'w') as f: json.dump(settings, f)
os.utime(twin.CFG_PATH, ns=(before.st_atime_ns, before.st_mtime_ns))
with mock.patch.object(twin, '_regular_file', side_effect=AssertionError('no session file may be opened')):
    assert twin.cached('t', 100, twin.terminals) == ([], 0)
""")

    def test_shared_settings_inflight_cache_uses_the_current_revision(self):
        self._shared_settings_case("""
calls = []
def read_workspace():
    calls.append(1)
    if len(calls) == 1:
        with open(twin.CFG_PATH) as f: settings = json.load(f)
        settings['name'] = 'Nora'
        with open(twin.CFG_PATH, 'w') as f: json.dump(settings, f)
        return 'old workspace'
    return 'current workspace'
assert twin.cached('sample', 100, read_workspace) == 'current workspace'
assert len(calls) == 2
""")

    def test_shared_settings_review_does_not_cross_source_roots(self):
        self._shared_settings_case("""
first = os.path.join(twin.HOME, 'first-notes'); second = os.path.join(twin.HOME, 'second-notes')
for folder, title in ((first, 'Crates in the first source are blue.'), (second, 'Crates in the second source are green.')):
    os.mkdir(folder)
    with open(os.path.join(folder, 'crate.md'), 'w') as f:
        f.write('---\\ndescription: ' + title + '\\narea: taste\\n---\\n\\n' + title)
assert 'error' not in twin.config({'memory': first})
old = next(e for e in twin.IX.get().e if e['src'] == 'crate.md')
twin.DB.execute('insert or replace into review values(?,?,?)', (old['id'], 'outdated', twin.now())); twin.DB.commit(); twin.IX.sig = None
assert old['id'] not in [e['id'] for e in twin.IX.get().e]
assert 'error' not in twin.config({'memory': second})
new = next(e for e in twin.IX.get().e if e['src'] == 'crate.md')
assert new['id'] != old['id']
assert new['title'] == 'Crates in the second source are green.'
""")

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

    def test_confined_note_fields_round_trip_without_changing_the_body(self):
        text = 'Inspection cards: use "ivory" stock.\n\nstatus: replaced\nKeep the packing note.\n'
        source = 'Owner review: "packing"\nSecond reference'
        nid = twin.save_note(text, "work", source)
        path = os.path.join(twin.NOTES, nid[4:] + ".md")
        with open(path) as f: raw = f.read()
        self.assertEqual(twin.fm(raw, "source"), source)
        self.assertEqual(raw.split("\n---\n", 1)[1], "\n" + text)
        self.assertTrue(twin.set_status(nid, "replaced", "own:next-note"))
        with open(path) as f: changed = f.read()
        self.assertEqual(changed.split("\n---\n", 1)[1], "\n" + text)
        self.assertEqual(twin.fm(changed, "status"), "replaced")

    def test_confined_note_body_edits_change_the_recalled_entry(self):
        nid = twin.save_note("Inspection cards use ivory stock.", "taste", "a test")
        path = os.path.join(twin.NOTES, nid[4:] + ".md")
        with open(path) as f: raw = f.read()
        with open(path, "w") as f: f.write(raw.split("\n---\n", 1)[0] + "\n---\n\nInspection cards use grey stock.\n")
        twin.IX.sig = None
        entry = next(e for e in twin.IX.get().e if e["id"] == nid)
        self.assertEqual(entry["title"], "Inspection cards use grey stock.")
        self.assertIn("grey stock", entry["body"])
        self.assertNotIn("ivory stock", entry["body"])

    def test_confined_note_filename_filter_applies_to_learned_notes(self):
        nid = twin.save_note("Inspection cards stay beside the press.", "work", "a test")
        keep = twin.ALLOW_F
        try:
            twin.ALLOW_F = twin._Rx(r"^feedback-", True); twin.IX.sig = None
            self.assertNotIn(nid, [e["id"] for e in twin.IX.get().e])
        finally:
            twin.ALLOW_F = keep; twin.IX.sig = None

    def test_confined_note_directory_is_checked_again_before_writing(self):
        with tempfile.TemporaryDirectory() as outside:
            held = twin.NOTES + ".held"
            os.rename(twin.NOTES, held)
            try:
                os.symlink(outside, twin.NOTES)
                with self.assertRaises((OSError, ValueError)):
                    twin.save_note("Inspection cards are checked daily.", "work", "a test")
                self.assertEqual(os.listdir(outside), [])
            finally:
                if os.path.islink(twin.NOTES): os.unlink(twin.NOTES)
                os.rename(held, twin.NOTES); twin.IX.sig = None

    def test_confined_note_bad_calendar_date_does_not_escape_to_the_page(self):
        nid = twin.save_note("Inspection cards are numbered.", "work", "a test")
        path = os.path.join(twin.NOTES, nid[4:] + ".md")
        with open(path) as f: raw = f.read()
        import re
        raw = re.sub(r"^accepted:.*$", "accepted: 2026-02-31", raw, flags=re.M)
        with open(path, "w") as f: f.write(raw)
        twin.IX.sig = None
        entry = next(e for e in twin.IX.get().e if e["id"] == nid)
        self.assertNotEqual(entry["since"], "2026-02-31")
        __import__("datetime").date.fromisoformat(entry["since"])

    def test_confined_export_rejects_linked_destination_components(self):
        with tempfile.TemporaryDirectory() as root:
            real = os.path.join(root, "real"); os.mkdir(real)
            link = os.path.join(root, "link"); os.symlink(real, link)
            with self.assertRaises((OSError, ValueError, SystemExit)):
                twin.export(os.path.join(link, "copy"))
            self.assertEqual(os.listdir(real), [])

    def test_confined_export_drops_filtered_notes_from_active_and_replaced(self):
        nid = twin.save_note("Inspection marker stays private.", "work", "a test")
        self.assertTrue(twin.set_status(nid, "replaced", "own:later"))
        keep = twin.DENY
        try:
            twin.DENY = twin._Rx("inspection marker", None); twin.IX.sig = None
            with tempfile.TemporaryDirectory() as dest:
                twin.export(dest)
                copied = [name for _, _, names in os.walk(dest) for name in names]
                self.assertNotIn(nid[4:] + ".md", copied)
        finally:
            twin.DENY = keep; twin.IX.sig = None

    def test_confined_platform_without_safe_file_support_stops_before_creating_data(self):
        with tempfile.TemporaryDirectory() as root:
            data = os.path.join(root, "new-data")
            code = "import os,sys;os.supports_dir_fd=set();sys.path.insert(0,sys.argv[1]);import twin"
            p = subprocess.run([sys.executable, "-B", "-c", code, os.path.join(ROOT, "twin")],
                               env=dict(os.environ, TWIN_HOME=data), capture_output=True, text=True, timeout=15)
            self.assertNotEqual(p.returncode, 0)
            self.assertIn("confined file access", p.stderr)
            self.assertFalse(os.path.exists(data))

    def test_confined_note_retry_keeps_leading_blank_lines(self):
        text = "\n\nInspection cards are signed at shift change.\n"
        first = twin.save_note(text, "work", "a test", uid="inspection-leading-lines")
        try: second = twin.save_note(text, "work", "a test", uid="inspection-leading-lines")
        except ValueError: self.fail("A retry must return the existing unchanged note.")
        self.assertEqual(first, second)

    def test_confined_export_write_failure_leaves_a_retryable_destination(self):
        from unittest.mock import patch
        for existing in (False, True):
            with self.subTest(existing=existing), tempfile.TemporaryDirectory() as root:
                dest = os.path.join(root, "copy")
                if existing: os.mkdir(dest)
                original = twin._write_at
                def fail_after_one_write(*args, **kwargs):
                    original(*args, **kwargs)
                    raise OSError(28, "simulated export write failure")
                with patch.object(twin, "_write_at", fail_after_one_write):
                    with self.assertRaises(SystemExit) as error: twin.export(dest)
                if existing: self.assertEqual(os.listdir(dest), [])
                else: self.assertFalse(os.path.exists(dest))
                self.assertEqual(sorted(os.listdir(root)), ["copy"] if existing else [])
                self.assertIn("simulated export write failure", str(error.exception))
                twin.export(dest)
                self.assertTrue(os.path.isfile(os.path.join(dest, "memory.json")))

    def test_confined_export_rechecks_the_destination_before_publishing(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as root:
            dest = os.path.join(root, "copy"); os.mkdir(dest)
            original = twin._write_at; changed = []
            def owner_adds_a_file(*args, **kwargs):
                original(*args, **kwargs)
                if not changed:
                    with open(os.path.join(dest, "owner.txt"), "w") as f: f.write("keep this file")
                    changed.append(True)
            with patch.object(twin, "_write_at", owner_adds_a_file):
                with self.assertRaises(SystemExit): twin.export(dest)
            self.assertEqual(os.listdir(dest), ["owner.txt"])
            with open(os.path.join(dest, "owner.txt")) as f: self.assertEqual(f.read(), "keep this file")
            self.assertEqual(os.listdir(root), ["copy"])

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

    def test_incomplete_upload_never_starts_its_action(self):
        import io
        from unittest.mock import Mock, patch
        for route, action in (("/api/listen", "listen"), ("/api/voice/clone?consent=1", "clone_voice"),
                              ("/api/setup/check", "check_photo"), ("/api/setup/photo?consent=1", "build_head")):
            with self.subTest(route=route), patch.object(twin, action) as start:
                request = Mock(path=route, headers={"Content-Length": "8"}, rfile=io.BytesIO(b"part"))
                twin.H.do_POST(request)
                start.assert_not_called()
                self.assertEqual(request.send.call_args.kwargs.get("code"), 400)

    def test_timed_out_upload_stops_before_dispatch(self):
        import socket
        from unittest.mock import Mock, patch
        request = Mock(path="/api/setup/check", headers={"Content-Length": "8"})
        request.rfile.read.side_effect = socket.timeout("upload paused")
        with patch.object(twin, "check_photo") as start:
            twin.H.do_POST(request)
            start.assert_not_called()
        self.assertEqual(request.send.call_args.kwargs.get("code"), 408)

    def test_disconnected_upload_closes_without_reply(self):
        from unittest.mock import Mock, patch
        request = Mock(path="/api/setup/check", headers={"Content-Length": "8"})
        request.rfile.read.side_effect = ConnectionResetError("upload cancelled")
        with patch.object(twin, "check_photo") as start:
            twin.H.do_POST(request)
            start.assert_not_called()
        request.send.assert_not_called()
        self.assertIs(request.close_connection, True)





class PrivacyDocs(unittest.TestCase):
    def read_doc(self, name):
        with open(os.path.join(ROOT, name), encoding="utf-8") as f:
            return f.read()

    def test_public_data_tables_name_optional_transfers(self):
        for name in ("README.md", "docs/TWIN.md"):
            with self.subTest(document=name):
                text = self.read_doc(name)
                section = text.split("## What leaves your machine", 1)[1].split("\n## ", 1)[0]
                for transfer in ("Connected MCP client", "Voice list", "Photo check", "Photo build model download"):
                    self.assertIn("| " + transfer + " |", section)
                self.assertIn("display name", section)
                self.assertIn("notes only", section)

    def test_session_and_read_inventory_names_the_actual_inputs(self):
        text = self.read_doc("docs/TWIN.md").lower()
        for item in ("session metadata", "transcript", "last prompt", "working folder", "rules file", "voice profile", "learned notes"):
            with self.subTest(input=item):
                self.assertIn(item, text)

    def test_storage_and_token_claims_are_scoped(self):
        text = self.read_doc("docs/TWIN.md")
        for promise in ("Questions and drafts you type are stored there as typed.",
                        "refuses requests without its session token.",
                        "It has no code that writes to, moves or deletes your files."):
            self.assertNotIn(promise, text)
        self.assertIn("temporary", text.lower())
        self.assertIn("API requests", text)
        self.assertIn("model cache", text.lower())

    def test_profile_setup_and_input_permission_are_explicit(self):
        text = self.read_doc("docs/TWIN.md")
        self.assertIn("twin.rules.json", text)
        self.assertIn("twin.md", text)
        for name in ("README.md", "docs/TWIN.md", "SKILL.md"):
            with self.subTest(document=name):
                self.assertIn("permission to use", self.read_doc(name).lower())

    def test_proof_does_not_claim_exclusive_retrieval(self):
        text = self.read_doc("README.md")
        self.assertNotIn("uses the new one only", text)
        self.assertIn("sample run", text.lower())

    def test_safety_checklist_scopes_redaction_and_validation(self):
        text = self.read_doc("SAFETY_CHECKLIST.md")
        self.assertNotIn("before anything is counted or written", text)
        self.assertNotIn("is the one networked file", text)
        self.assertNotIn("SAFE to share publicly", text)
        self.assertIn("checker examines raw", text.lower())
        self.assertIn("validation/twin_loop.py", text)

    def test_current_changelog_does_not_overstate_data_contracts(self):
        text = self.read_doc("CHANGELOG.md").split("## [3.0.1]", 1)[0]
        for promise in ("writes everything", "ten offline tests", "A proposal does nothing"):
            self.assertNotIn(promise, text)
        self.assertIn("pending", text.lower())
        self.assertIn("profile", text.lower())

    def test_platform_requirements_distinguish_app_and_voice_scripts(self):
        readme = self.read_doc("README.md")
        app = readme.split("## Try it in one minute", 1)[1].split("## Make it yours", 1)[0]
        start = self.read_doc("docs/TWIN.md").split("## Make it yours", 1)[0]
        for text in (app, start):
            self.assertIn("macOS", text)
            self.assertIn("Linux", text)
            self.assertIn("native Windows", text)
        self.assertIn("legacy voice scripts", readme.lower())
        evaluator = self.read_doc("validation/EVAL.md")
        self.assertIn("POSIX", evaluator)
        self.assertIn("native Windows", evaluator)

    def test_export_log_discloses_historical_text(self):
        text = self.read_doc("docs/TWIN.md")
        self.assertIn("log.json", text)
        for boundary in ("earlier events", "source removal", "filter changes"):
            self.assertIn(boundary, text)

    def test_public_docs_meet_copy_rules(self):
        import re
        banned = re.compile(r"\b(?:delve|transformative|robust|game-changing|revolutionize|unlock|elevate|seamless|leverage|automat\w*)\b|\u2014|[\U0001F300-\U0001FAFF]", re.I)
        for name in ("README.md", "docs/TWIN.md", "SKILL.md", "SAFETY_CHECKLIST.md", "CHANGELOG.md", "validation/EVAL.md"):
            with self.subTest(document=name):
                self.assertIsNone(banned.search(self.read_doc(name)))

    def test_default_demo_distinguishes_local_http_from_remote_transfer(self):
        text = self.read_doc("README.md").split("## What leaves your machine", 1)[1].split("\n## ", 1)[0]
        self.assertNotIn("makes no network requests", text)
        self.assertIn("sends nothing off this machine", text)
        self.assertIn("local HTTP", text)

    def test_mcp_tool_list_describes_recall_scope_and_local_writes(self):
        request = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
        reply = subprocess.run(
            [sys.executable, os.path.join(ROOT, "twin", "twin_mcp.py")],
            input=json.dumps(request) + "\n", text=True, capture_output=True,
            timeout=20, check=True,
        )
        tools = {t["name"]: t for t in json.loads(reply.stdout)["result"]["tools"]}
        with self.subTest(tool="twin_recall"):
            project = tools["twin_recall"]["inputSchema"]["properties"]["project"]["description"]
            self.assertIn("ranking boost", project.lower())
            self.assertIn("summaries", tools["twin_recall"]["description"].lower())
        with self.subTest(tool="twin_propose_note"):
            self.assertIn("pending proposal", tools["twin_propose_note"]["description"].lower())
        with self.subTest(tool="twin_audit"):
            self.assertIn("client use", tools["twin_audit"]["description"].lower())
        with self.subTest(tool="twin_allowed"):
            self.assertIn("unknown", tools["twin_allowed"]["description"].lower())

    def test_readme_explains_what_mcp_recall_and_limits_return(self):
        text = self.read_doc("README.md")
        self.assertIn("Note summaries with their sources", text)
        self.assertIn("An unmatched request leaves permission unknown", text)





class DraftLengthBounds(unittest.TestCase):
    def test_readme_states_the_draft_check_limit(self):
        from pathlib import Path
        text = (Path(ROOT) / "README.md").read_text()
        self.assertIn("Checks drafts up to 60,000 characters", text)

    def test_repo_audit_reports_a_draft_it_could_not_check(self):
        from pathlib import Path
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root) / "sample"
            (repo / ".git").mkdir(parents=True)
            (repo / "draft.md").write_text("X" * 60001)
            def sample_git(args, cwd, **kw):
                return "draft.md" if args[0] == "log" else ""
            with patch.object(twin, "HOME", root), patch.dict(twin.CFG, repos=["sample"]), patch.object(twin, "git", side_effect=sample_git):
                result = twin.audit()
            self.assertTrue(any(row["kind"] == "Draft not checked" and "draft.md" in row["what"]
                                for row in result["findings"]))

    def test_draft_limits_are_visible_before_submission(self):
        for name in ("twin/ui.html", "docs/TWIN.md"):
            with self.subTest(document=name):
                with open(os.path.join(ROOT, name), encoding="utf-8") as f:
                    text = f.read()
                self.assertIn("60,000", text)
                self.assertIn("6,000", text)

    def test_readme_requires_review_before_sharing_patterns(self):
        with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as f:
            text = f.read()
        self.assertNotIn("The prompt extracts principles, not data", text)
        self.assertNotIn("Share your patterns freely", text)
        self.assertIn("Review patterns before sharing", text)

    def test_check_rejects_a_draft_with_unchecked_suffix(self):
        draft = "Done.\n" * 10000 + "I think maybe."
        result = twin.check(draft)
        self.assertIn("error", result)
        self.assertIn("60,000", result["error"])

    def test_rewrite_rejects_long_drafts_before_calling_a_model(self):
        from unittest.mock import patch
        with patch.object(twin, "claude", return_value="Done.") as model:
            result = twin.rewrite("Done.\n" * 1001)
        model.assert_not_called()
        self.assertIn("error", result)
        self.assertIn("6,000", result["error"])

    def test_check_accepts_a_draft_at_its_limit(self):
        result = twin.check("Done.\n" * 10000)
        self.assertNotIn("error", result)
        self.assertTrue(result["passed"])

    def test_rewrite_accepts_a_draft_at_its_limit(self):
        from unittest.mock import patch
        with patch.object(twin, "claude", return_value="Done.") as model:
            result = twin.rewrite("Done.\n" * 1000)
        model.assert_called_once()
        self.assertNotIn("error", result)
        self.assertEqual(result["text"], "Done.")


class McpCheckResultTests(unittest.TestCase):
    def test_a_checker_error_reaches_the_client_and_its_usage_record(self):
        import contextlib, sqlite3
        for size, expected in ((5, "ok"), (60001, "error")):
            with self.subTest(expected=expected), tempfile.TemporaryDirectory() as store:
                request = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {
                    "name": "twin_check_draft", "arguments": {"text": "a" * size}}}
                run = subprocess.run([sys.executable, os.path.join(ROOT, "twin", "twin_mcp.py")],
                                     input=json.dumps(request) + "\n", text=True, capture_output=True,
                                     env=dict(os.environ, TWIN_HOME=store), timeout=30, check=True)
                result = json.loads(run.stdout)["result"]
                with contextlib.closing(sqlite3.connect(os.path.join(store, "twin.db"))) as db:
                    recorded = db.execute("select last_result from clients").fetchone()[0]
                self.assertEqual((result.get("isError", False), recorded), (expected == "error", expected))


class JudgeSchemaTests(unittest.TestCase):
    def test_invalid_rules_and_unknown_test_ids_fail_before_any_provider_call(self):
        import contextlib, io
        from pathlib import Path
        from unittest import mock
        module, _ = ValidationSafetyTests.load_validation("twin_eval")
        with tempfile.TemporaryDirectory() as folder:
            profile = Path(folder, "profile.md"); profile.write_text("Use short sentences.")
            invalid = Path(folder, "rules.json"); invalid.write_text("{}")
            destination = Path(folder, "result.json")
            cases = [(["--tests", "ST-01,ST-missing"], "ST-missing"),
                     (["--rules", str(invalid)], "not a valid"),
                     (["--rules", str(Path(folder, "missing.json"))], "cannot read")]
            for options, problem in cases:
                with self.subTest(options=options):
                    errors = io.StringIO()
                    with mock.patch.object(module, "call", side_effect=AssertionError("unexpected model call")) as call:
                        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "offline-fixture"}):
                            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(errors):
                                with self.assertRaises(SystemExit) as stopped:
                                    module.main(["--twin", str(profile), "--out", str(destination)] + options)
                    call.assert_not_called()
                    self.assertEqual(stopped.exception.code, 2)
                    self.assertIn(problem, errors.getvalue())
                    self.assertFalse(destination.exists())

    def test_a_valid_selected_rule_set_checks_both_completed_answers(self):
        import contextlib, io
        from pathlib import Path
        from unittest import mock
        module, _ = ValidationSafetyTests.load_validation("twin_eval")
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder, "result.json")
            example = Path(ROOT, "twins", "example")
            replies = [("Done.", {}, "end_turn"), ("Done.", {}, "end_turn"),
                       ('{"winner":"tie","confidence":3,"reason":"Same text."}', {}, "end_turn")]
            with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "offline-fixture"}), mock.patch.object(module, "call", side_effect=replies):
                with contextlib.redirect_stdout(io.StringIO()):
                    code = module.main(["--twin", str(example / "twin.md"), "--rules", str(example / "twin.rules.json"),
                                        "--tests", "ST-01", "--out", str(output)])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(output.read_text())["summary"]["rule_pass"], {"generic": 1, "twin": 1})

    def test_incomplete_or_invalid_judge_fields_cannot_score_a_win(self):
        fixture = ValidationSafetyTests()
        good = {"winner": "A", "confidence": 3, "reason": "Shorter."}
        cases = [(dict(good), True), ({"winner": "A"}, False), (dict(good, reason=7), False),
                 (dict(good, confidence=True), False), (dict(good, confidence=6), False),
                 (dict(good, other="unexpected"), False)]
        for verdict, valid in cases:
            with self.subTest(verdict=verdict):
                answers = ["One complete answer.", "Another complete answer.", json.dumps(verdict)]
                code, result = fixture.evaluator_with_transport([fixture.evaluator_message(a) for a in answers])
                self.assertEqual(code, 0 if valid else 1)
                self.assertEqual(result["complete"], valid)
                summary = result["summary"]
                self.assertEqual(summary["twin_wins"] + summary["generic_wins"], int(valid))


if __name__ == "__main__":
    unittest.main()
