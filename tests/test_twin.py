"""Tests for the twin scripts. Standard library only. Synthetic fixtures only.

Run: python3 -m unittest discover -s tests -v   (or scripts/test.sh)
"""

import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from contextlib import redirect_stdout, redirect_stderr

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)

import twinlib as tl  # noqa: E402
import twin_scan  # noqa: E402
import twin_check  # noqa: E402
import twin_report  # noqa: E402
import twin_diff  # noqa: E402

FIX = os.path.join(ROOT, "tests", "fixtures")
SAMPLE = os.path.join(ROOT, "examples", "sample-corpus")
PAIRS = os.path.join(ROOT, "examples", "edit-pairs")
RULES = os.path.join(ROOT, "twins", "example", "twin.rules.json")

FAKE_PRIVATE = ["test.person@example.com", "010-0199", "12,500", "3,000 dollars",
                "ops@larkfield.example", "617-555-0142", "4,200"]


def run(main, argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        try:
            code = main(argv)
        except SystemExit as exc:
            code = exc.code
    return code, out.getvalue(), err.getvalue()


class Tmp(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="twin-test-")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def p(self, name):
        return os.path.join(self.tmp, name)


class TestText(unittest.TestCase):
    def lines(self):
        return tl.classify_lines(tl.read_text(os.path.join(FIX, "edge", "edge.md")))

    def test_redaction(self):
        counts = {}
        out = tl.redact(tl.read_text(os.path.join(FIX, "edge", "edge.md")), counts)
        for s in ("test.person@example.com", "(555) 010-0199", "$12,500", "3,000 dollars"):
            self.assertNotIn(s, out)
        self.assertEqual(counts, {"email": 1, "phone": 1, "amount": 2})

    def test_redaction_leaves_plain_numbers(self):
        self.assertEqual(tl.redact("We shipped 300 boxes in 2026."), "We shipped 300 boxes in 2026.")

    def test_sentences(self):
        sents = tl.split_sentences(self.lines())
        texts = [s["text"] for s in sents]
        self.assertIn("Dr. Vale met Mr. Ortiz at 9 a.m. and the meeting ran long.", texts)
        self.assertIn("Is this a question?", texts)
        self.assertIn("Yes!", texts)
        self.assertIn("Another list item with no full stop", texts)
        self.assertFalse(any("heading" in t for t in texts), "headings are not sentences")
        self.assertFalse(any("code blocks" in t for t in texts), "code is skipped")
        self.assertFalse(any("title:" in t for t in texts), "front matter is skipped")

    def test_sentence_line_numbers(self):
        sents = tl.split_sentences(self.lines())
        by_text = {s["text"]: s["line"] for s in sents}
        self.assertEqual(by_text["It ended at noon."], 7)
        self.assertEqual(by_text["Is this a question?"], 9)

    def test_phrase_regex_matches_foundrkit_rules(self):
        rx = tl.phrase_regex("delve")
        self.assertTrue(rx.search("Delve in"))
        self.assertFalse(rx.search("delved"))
        self.assertTrue(tl.phrase_regex("\u2014").search("a\u2014b"))

    def test_literal_regex(self):
        self.assertTrue(tl.literal_regex("/\\u2014/").search("x \u2014 y"))
        self.assertTrue(tl.literal_regex("/abc/").search("ABC"), "no flags means case-insensitive")
        self.assertFalse(tl.literal_regex("/abc/g").search("ABC"))
        with self.assertRaises(ValueError):
            tl.literal_regex("abc")

    def test_snippet_is_short(self):
        s = tl.snippet("word " * 100, 200, 205, width=40)
        self.assertLessEqual(len(s), 46)


class TestScan(Tmp):
    def scan(self, *corpora, extra=()):
        out = self.p("patterns.json")
        args = []
        for c in corpora:
            args += ["--corpus", c]
        code, stdout, _ = run(twin_scan.main, args + ["--out", out] + list(extra))
        self.assertEqual(code, 0)
        with open(out, encoding="utf-8") as fh:
            return json.load(fh), fh.name, stdout

    def test_deterministic(self):
        _, a, _ = self.scan(SAMPLE)
        with open(a, "rb") as fh:
            first = fh.read()
        _, b, _ = self.scan(SAMPLE)
        with open(b, "rb") as fh:
            self.assertEqual(first, fh.read())

    def test_sample_patterns(self):
        data, path, _ = self.scan(SAMPLE)
        c = data["corpora"][0]
        self.assertEqual(c["totals"]["files"], 7)
        phrases = {p["phrase"]: p["count"] for p in c["crutch_phrases"]}
        self.assertEqual(phrases.get("one owner per task"), 5)
        self.assertIn("log is the memory", phrases)
        self.assertNotIn("problem down before you fix", phrases, "overlapping windows collapse")
        drifting = {f["file"] for f in c["drift"]["files"] if f["drifting"]}
        self.assertIn("board-memo.md", drifting)
        self.assertNotIn("weekly-note-01.md", drifting)
        kinds = {f["kind"] for f in c["flags"]["items"]}
        self.assertEqual(kinds, {"hedge", "long_sentence", "dash"})
        self.assertEqual(c["redactions"], {"email": 1, "phone": 1, "amount": 1})
        self.assertIsInstance(c["score"]["value"], int)
        with open(path, encoding="utf-8") as fh:
            raw = fh.read()
        for s in FAKE_PRIVATE:
            self.assertNotIn(s, raw)

    def test_hedge_fix_never_deletes_a_modal(self):
        data, _, _ = self.scan(SAMPLE)
        for f in data["corpora"][0]["flags"]["items"]:
            if f["kind"] == "hedge" and f["match"].lower() == "might":
                self.assertFalse(f["fix_is_rewrite"])

    def test_comparison(self):
        data, _, _ = self.scan("notes=" + SAMPLE, "edits=" + PAIRS)
        self.assertEqual([c["name"] for c in data["corpora"]], ["notes", "edits"])
        cmp_ = data["comparison"]
        self.assertEqual(cmp_["corpora"], ["notes", "edits"])
        metrics = {r["metric"] for r in cmp_["table"]}
        self.assertIn("hedge_rate", metrics)

    def test_hide_filenames(self):
        data, path, _ = self.scan(SAMPLE, extra=["--hide-filenames"])
        with open(path, encoding="utf-8") as fh:
            self.assertNotIn("board-memo", fh.read())

    def test_custom_metaphors(self):
        words = self.p("m.json")
        with open(words, "w") as fh:
            json.dump({"families": {"kitchen": ["bowl*", "bench*"]}}, fh)
        data, _, _ = self.scan(SAMPLE, extra=["--metaphors", words])
        fam = data["corpora"][0]["metaphor_families"]
        self.assertEqual(fam[0]["family"], "kitchen")
        self.assertGreater(fam[0]["count"], 0)

    def test_missing_corpus(self):
        code, _, _ = run(twin_scan.main, ["--corpus", self.p("nope"), "--out", self.p("x.json")])
        self.assertEqual(code, 2)


class TestCheck(Tmp):
    def test_good_draft_passes(self):
        code, out, _ = run(twin_check.main, ["--rules", RULES, os.path.join(FIX, "drafts", "good.md")])
        self.assertEqual(code, 0, out)
        self.assertIn("result      PASS", out)

    def test_bad_draft_fails_with_lines(self):
        code, out, _ = run(twin_check.main, ["--rules", RULES, os.path.join(FIX, "drafts", "bad.md"),
                                             "--format", "json"])
        self.assertEqual(code, 1)
        res = {r["id"]: r for r in json.loads(out)["results"]}
        self.assertFalse(res["no-hedges"]["passed"])
        self.assertEqual([(h["line"], h["column"], h["match"]) for h in res["no-hedges"]["hits"]],
                         [(3, 1, "I think"), (3, 19, "maybe")])
        self.assertEqual(res["no-dashes"]["hits"][0]["line"], 7)
        self.assertEqual(res["sentence-length"]["hits"][0]["line"], 9)
        self.assertTrue(res["no-emoji"]["passed"])

    def test_github_annotations(self):
        code, out, _ = run(twin_check.main, ["--rules", RULES, os.path.join(FIX, "drafts", "bad.md"),
                                             "--format", "github"])
        self.assertEqual(code, 1)
        lines = out.splitlines()
        self.assertTrue(any(l.startswith("::error file=") and "line=3,col=1" in l and "no-hedges" in l for l in lines))
        self.assertTrue(any(l.startswith("::warning file=") and "sentence-length" in l for l in lines))
        self.assertTrue(lines[-1].startswith("twin_check: FAIL"))

    def test_strict_fails_on_warnings(self):
        draft = self.p("warn.md")
        with open(draft, "w") as fh:
            fh.write("Let us touch base on Friday.\n")
        self.assertEqual(run(twin_check.main, ["--rules", RULES, draft])[0], 0)
        self.assertEqual(run(twin_check.main, ["--rules", RULES, draft, "--strict"])[0], 1)

    def test_rate_rule(self):
        draft = self.p("q.md")
        with open(draft, "w") as fh:
            fh.write("We ship today! Truly!\n")
        code, out, _ = run(twin_check.main, ["--rules", RULES, draft, "--format", "json"])
        res = {r["id"]: r for r in json.loads(out)["results"]}
        self.assertFalse(res["no-exclamations"]["passed"])
        self.assertEqual(list(res["no-exclamations"]["measured"].values()), [1.0])

    def test_calibration_on_own_voice(self):
        """The example rules must pass the on-voice files they were drawn from."""
        on_voice = [os.path.join(SAMPLE, f) for f in sorted(os.listdir(SAMPLE)) if f != "board-memo.md"]
        code, out, _ = run(twin_check.main, ["--rules", RULES] + on_voice + ["--strict"])
        self.assertEqual(code, 0, out)

    def test_invalid_rules(self):
        bad = self.p("bad.json")
        with open(bad, "w") as fh:
            json.dump({"contract": "twin-rules", "version": "1", "brand": "x", "profile_version": "1.0",
                       "rules": [{"id": "A", "type": "nope", "severity": "loud"}]}, fh)
        code, _, err = run(twin_check.main, ["--rules", bad, os.path.join(FIX, "drafts", "good.md")])
        self.assertEqual(code, 2)
        self.assertIn("profile_version", err)
        self.assertIn("lowercase", err)

    def test_missing_draft(self):
        code, _, _ = run(twin_check.main, ["--rules", RULES, self.p("missing.md")])
        self.assertEqual(code, 2)

    def test_redacts_snippets(self):
        draft = self.p("pii.md")
        with open(draft, "w") as fh:
            fh.write("I think you should email test.person@example.com about it.\n")
        _, out, _ = run(twin_check.main, ["--rules", RULES, draft])
        self.assertNotIn("test.person@example.com", out)
        self.assertIn("[redacted-email]", out)


class TestFoundrkitExport(Tmp):
    def test_export_shape(self):
        out = self.p("foundrkit.config.json")
        code, stdout, _ = run(twin_check.main, ["--rules", RULES, "--export-foundrkit", out])
        self.assertEqual(code, 0)
        with open(out) as fh:
            cfg = json.load(fh)
        self.assertEqual(list(cfg), ["forbidden"])
        for item in cfg["forbidden"]:
            self.assertTrue(set(item) <= {"pattern", "severity", "suggestion", "category"})
            self.assertIn(item["severity"], ("error", "warn"))
        patterns = [i["pattern"] for i in cfg["forbidden"]]
        self.assertIn("i think", patterns)
        self.assertIn("/\\u2014/", patterns)
        self.assertIn("skipped sentence-length", stdout)
        self.assertIn("skipped no-emoji", stdout)

    def test_python_only_regex_is_not_exported(self):
        doc = {"contract": "twin-rules", "version": "1", "brand": "x", "profile_version": "1.0.0",
               "rules": [{"id": "named", "type": "banned_pattern", "severity": "error",
                          "pattern": "/(?P<w>foo)/"}]}
        cfg, skipped = twin_check.foundrkit_export(doc)
        self.assertEqual(cfg["forbidden"], [])
        self.assertEqual(skipped[0][0], "named")

    @unittest.skipUnless(os.environ.get("FOUNDRKIT_LINT"), "set FOUNDRKIT_LINT to foundrkit-lint's bin/foundrkit-lint.js")
    def test_same_hits_as_foundrkit_lint(self):
        work = self.p("fk")
        os.makedirs(os.path.join(work, "docs"))
        for f in ("board-memo.md", "weekly-note-01.md"):
            shutil.copy(os.path.join(SAMPLE, f), os.path.join(work, "docs", f))
        shutil.copy(os.path.join(FIX, "drafts", "bad.md"), os.path.join(work, "docs", "bad.md"))
        run(twin_check.main, ["--rules", RULES, "--export-foundrkit", os.path.join(work, "foundrkit.config.json")])
        proc = subprocess.run(["node", os.environ["FOUNDRKIT_LINT"], "docs", "--reporter=json"],
                              cwd=work, capture_output=True, text=True)
        theirs = set()
        for r in json.loads(proc.stdout)["results"]:
            for h in r.get("hits", r.get("issues", [])):
                theirs.add((os.path.basename(r["file"]), h["line"], h["column"], h["match"].lower()))
        _, out, _ = run(twin_check.main, ["--rules", RULES, os.path.join(work, "docs"), "--format", "json"])
        ours = set()
        for r in json.loads(out)["results"]:
            if r["type"] in ("banned_phrase", "banned_pattern"):
                for h in r["hits"]:
                    ours.add((os.path.basename(h["file"]), h["line"], h["column"], h["match"].lower()))
        self.assertEqual(theirs, ours)


class TestDiff(Tmp):
    def setUp(self):
        super().setUp()
        self.rules = self.p("twin.rules.json")
        shutil.copy(RULES, self.rules)
        self.props = self.p("twin.proposals.md")
        self.log = self.p("TWIN_CHANGELOG.md")

    def propose(self):
        with open(self.rules, "rb") as fh:
            before = fh.read()
        code, out, _ = run(twin_diff.main, ["propose", PAIRS, "--rules", self.rules, "--out", self.props])
        self.assertEqual(code, 0)
        with open(self.rules, "rb") as fh:
            self.assertEqual(before, fh.read(), "propose must never touch the rules")
        with open(self.props, encoding="utf-8") as fh:
            return fh.read()

    def tick(self, text, *ids):
        for pid in ids:
            text = re.sub(r"(## %s\. [^\n]*\n\n)- \[ \] accept" % pid, r"\1- [x] accept", text)
        with open(self.props, "w", encoding="utf-8") as fh:
            fh.write(text)

    def test_proposals(self):
        text = self.propose()
        self.assertIn('Ban "really"', text)
        self.assertIn('Ban "basically"', text)
        self.assertIn("Lower the sentence limit", text)
        self.assertNotIn('Ban "maybe"', text, "already banned phrases are not proposed again")
        self.assertNotRegex(text, r"(?m)^- \[x\] accept")

    def test_accept_only_ticked(self):
        text = self.propose()
        pid = re.search(r'## (P\d+)\. Ban "really"', text).group(1)
        self.tick(text, pid)
        code, _, _ = run(twin_diff.main, ["accept", self.props, "--rules", self.rules,
                                          "--changelog", self.log, "--date", "2026-01-01"])
        self.assertEqual(code, 0)
        doc = tl.load_json(self.rules)
        self.assertEqual(doc["profile_version"], "1.1.0")
        rule = [r for r in doc["rules"] if r["id"] == "deleted-in-edits"][0]
        self.assertEqual(rule["phrases"], ["really"])
        self.assertEqual(rule["source"], "diff")
        self.assertEqual(twin_check.validate_rules(doc), [])
        with open(self.log, encoding="utf-8") as fh:
            log = fh.read()
        self.assertIn("## 1.1.0 (2026-01-01)", log)
        self.assertIn('Ban "really"', log)
        self.assertIn("Not accepted:", log)

    def test_stale_proposals_refused(self):
        text = self.propose()
        self.tick(text, "P1")
        with open(self.rules, "a") as fh:
            fh.write("\n")
        code, _, err = run(twin_diff.main, ["accept", self.props, "--rules", self.rules, "--changelog", self.log])
        self.assertEqual(code, 2)
        self.assertIn("changed after", err)
        self.assertFalse(os.path.exists(self.log))

    def test_nothing_ticked_changes_nothing(self):
        self.propose()
        with open(self.rules, "rb") as fh:
            before = fh.read()
        code, out, _ = run(twin_diff.main, ["accept", self.props, "--rules", self.rules, "--changelog", self.log])
        self.assertEqual(code, 0)
        self.assertIn("Nothing changed", out)
        with open(self.rules, "rb") as fh:
            self.assertEqual(before, fh.read())

    def test_changelog_newest_first(self):
        text = self.propose()
        self.tick(text, "P1")
        run(twin_diff.main, ["accept", self.props, "--rules", self.rules, "--changelog", self.log, "--date", "2026-01-01"])
        text = self.propose()
        self.tick(text, "P1")
        run(twin_diff.main, ["accept", self.props, "--rules", self.rules, "--changelog", self.log, "--date", "2026-01-02"])
        with open(self.log, encoding="utf-8") as fh:
            log = fh.read()
        self.assertLess(log.index("## 1.2.0"), log.index("## 1.1.0"))


class TestReport(Tmp):
    def build(self, *corpora):
        pj = self.p("patterns.json")
        args = []
        for c in corpora:
            args += ["--corpus", c]
        run(twin_scan.main, args + ["--out", pj])
        out = self.p("report.html")
        code, _, _ = run(twin_report.main, [pj, "--out", out])
        self.assertEqual(code, 0)
        with open(out, encoding="utf-8") as fh:
            return fh.read(), pj

    def test_self_contained(self):
        page, _ = self.build(SAMPLE)
        self.assertNotRegex(page, r"(?i)https?://")
        self.assertNotRegex(page, r"(?i)\bsrc\s*=")
        self.assertNotRegex(page, r"(?i)@import|url\(|<link")
        self.assertIn("<svg", page)
        self.assertIn('data-theme="light"', page)
        self.assertIn("prefers-color-scheme", page)

    def test_sections(self):
        page, _ = self.build(SAMPLE)
        for heading in ("Patterns you repeat", "Where your voice drifts",
                        "Flagged lines with a suggested fix", "Score"):
            self.assertIn(heading, page)

    def test_palette_only(self):
        page, _ = self.build(SAMPLE)
        hexes = {h.upper() for h in re.findall(r"#[0-9A-Fa-f]{6}\b", page)}
        self.assertEqual(hexes, {"#07080A", "#F6F5F2", "#E4552A"})
        rgba = set(re.findall(r"rgba\((\d+,\d+,\d+)", page))
        self.assertEqual(rgba, {"246,245,242", "7,8,10"})

    def test_redacts_even_unredacted_input(self):
        """A hand-edited patterns.json with raw contact details still gets redacted."""
        _, pj = self.build(SAMPLE)
        data = tl.load_json(pj)
        flag = data["corpora"][0]["flags"]["items"][0]
        flag["snippet"] = "Call 617-555-0142 or write to test.person@example.com about the $9,999 quote"
        flag["fix"] = flag["snippet"]
        tl.write_json(pj, data)
        out = self.p("r2.html")
        run(twin_report.main, [pj, "--out", out])
        with open(out, encoding="utf-8") as fh:
            page = fh.read()
        for s in ("617-555-0142", "test.person@example.com", "9,999"):
            self.assertNotIn(s, page)

    def test_comparison_section(self):
        page, _ = self.build("notes=" + SAMPLE, "edits=" + PAIRS)
        self.assertIn("Across corpora", page)

    def test_rejects_other_json(self):
        bad = self.p("x.json")
        with open(bad, "w") as fh:
            json.dump({"hello": 1}, fh)
        self.assertEqual(run(twin_report.main, [bad, "--out", self.p("o.html")])[0], 2)


class TestRepo(unittest.TestCase):
    def test_scripts_make_no_network_calls(self):
        banned = re.compile(r"^\s*(import|from)\s+(socket|urllib|http|requests|httpx|ftplib|smtplib|ssl)\b", re.M)
        for name in sorted(os.listdir(SCRIPTS)):
            if name.endswith(".py"):
                with open(os.path.join(SCRIPTS, name), encoding="utf-8") as fh:
                    self.assertIsNone(banned.search(fh.read()), "%s imports a network module" % name)

    def test_skill_zip_matches_skill_md(self):
        with zipfile.ZipFile(os.path.join(ROOT, "digital-twin-skill.zip")) as z:
            names = z.namelist()
            self.assertEqual(names, ["SKILL.md"])
            zipped = z.read("SKILL.md")
        with open(os.path.join(ROOT, "SKILL.md"), "rb") as fh:
            self.assertEqual(zipped, fh.read(), "rebuild the zip: scripts/build_zip.sh")

    def test_every_twin_is_valid(self):
        twins = os.path.join(ROOT, "twins")
        found = 0
        for brand in sorted(os.listdir(twins)):
            path = os.path.join(twins, brand, "twin.rules.json")
            if os.path.isfile(path):
                found += 1
                doc = tl.load_json(path)
                self.assertEqual(twin_check.validate_rules(doc), [], path)
                self.assertEqual(doc["brand"], brand, "brand must match its folder name")
                self.assertTrue(os.path.isfile(os.path.join(twins, brand, "twin.md")), brand)
                self.assertTrue(os.path.isfile(os.path.join(twins, brand, "TWIN_CHANGELOG.md")), brand)
        self.assertGreater(found, 0)

    def test_no_em_dashes_or_emoji_in_new_files(self):
        paths = [os.path.join(SCRIPTS, n) for n in os.listdir(SCRIPTS) if n.endswith(".py")]
        paths += [os.path.join(ROOT, "tests", "test_twin.py")]
        for p in paths:
            with open(p, encoding="utf-8") as fh:
                text = fh.read()
            literal_dash = [ln for ln in text.splitlines() if "\u2014" in ln]
            self.assertEqual(literal_dash, [], p)


class TestEval(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, os.path.join(ROOT, "validation"))
        import twin_eval
        self.ev = twin_eval

    def test_parses_all_fifteen(self):
        tests = self.ev.parse_stress_tests(os.path.join(ROOT, "validation", "STRESS_TESTS.md"))
        self.assertEqual([t["id"] for t in tests], ["ST-%02d" % i for i in range(1, 16)])
        self.assertTrue(all(len(t["prompt"]) > 40 for t in tests))

    def test_dry_run_sends_nothing(self):
        import urllib.request
        def boom(*a, **k):
            raise AssertionError("dry run opened a connection")
        real = urllib.request.urlopen
        urllib.request.urlopen = boom
        try:
            code, out, _ = run(self.ev.main, ["--twin", os.path.join(ROOT, "twins", "example", "twin.md"),
                                              "--samples", SAMPLE, "--dry-run"])
        finally:
            urllib.request.urlopen = real
        self.assertEqual(code, 0)
        self.assertIn("dry run: nothing sent", out)

    def test_same_model_refused(self):
        code, _, _ = run(self.ev.main, ["--twin", os.path.join(ROOT, "twins", "example", "twin.md"),
                                        "--gen-model", "x", "--judge-model", "x", "--dry-run"])
        self.assertEqual(code, 2)

    def test_sign_test(self):
        self.assertEqual(self.ev.sign_test(12, 3), 0.0352)
        self.assertIsNone(self.ev.sign_test(0, 0))


class TestReviewRegressions(Tmp):
    """One test per bug found in the pre-merge review."""

    def write(self, name, text, encoding="utf-8"):
        path = self.p(name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding=encoding) as fh:
            fh.write(text)
        return path

    def rules(self, rule):
        return self.write("r.json", json.dumps({"contract": "twin-rules", "version": "1", "brand": "x",
                                                "profile_version": "1.0.0", "rules": [rule]}))

    def test_match_text_is_redacted(self):
        rules = self.rules({"id": "reach", "type": "banned_pattern", "severity": "error",
                            "pattern": "/reach me at .*/"})
        draft = self.write("d.md", "Reach me at bob@example.com or 617-555-0100 today.\n")
        for fmt in ("json", "github", "text"):
            _, out, _ = run(twin_check.main, ["--rules", rules, draft, "--format", fmt])
            self.assertNotIn("bob@example.com", out, fmt)
            self.assertNotIn("555-0100", out, fmt)

    def test_redaction_coverage(self):
        for raw in ("+44 20 7946 0958", "555-1234", "617.555.0100x22", "USD 500", "EUR 40", "$500k",
                    "\u00a55000", "\u20b95,000", "1,200 euros", "**bob**@example.com"):
            self.assertTrue(tl.redact(raw).startswith("[redacted-"), raw)
        for keep in ("Call 2026-10-02 at 9.30", "version 1.2.3", "We shipped 300 boxes in 2026.",
                     "+21.9", "z +4.2", "-2.5", "Dashes per 1k words", "score 92/100", "+25.0", "2.0.0",
                     "1,200 words", "ran 5k steps", "p=0.035", "+3 points"):
            self.assertEqual(tl.redact(keep), keep)

    def test_emphasised_email_never_reaches_output(self):
        corpus = self.p("c")
        self.write("c/a.md", "Write to **bob**@example.com today, I think.\n")
        out = self.p("p.json")
        run(twin_scan.main, ["--corpus", corpus, "--out", out])
        with open(out, encoding="utf-8") as fh:
            self.assertNotIn("bob@example.com", fh.read())

    def test_file_names_are_redacted(self):
        corpus = self.p("c")
        self.write("c/john@acme.com notes.md", "One owner per task. One owner per task. One owner per task.\n")
        out = self.p("p.json")
        run(twin_scan.main, ["--corpus", corpus, "--out", out])
        with open(out, encoding="utf-8") as fh:
            self.assertNotIn("john@acme.com", fh.read())
        pairs = self.p("pairs")
        for side, text in (("draft", "I really think so.\n"), ("edited", "So.\n")):
            self.write("pairs/bob@acme.com.%s.md" % side, text)
        props = self.p("props.md")
        run(twin_diff.main, ["propose", pairs, "--rules", RULES, "--out", props, "--min-pairs", "1"])
        with open(props, encoding="utf-8") as fh:
            self.assertNotIn("bob@acme.com", fh.read())

    def test_line_numbers_on_wrapped_lines(self):
        sents = tl.split_sentences(tl.classify_lines("First one.\nSecond one.\nThird one."))
        self.assertEqual([x["line"] for x in sents], [1, 2, 3])
        rules = self.rules({"id": "h", "type": "banned_phrase", "severity": "error", "phrases": ["maybe"]})
        draft = self.write("d.md", "We ship today.\nMaybe Friday.\n")
        _, out, _ = run(twin_check.main, ["--rules", rules, draft, "--format", "json"])
        self.assertEqual(json.loads(out)["results"][0]["hits"][0]["line"], 2)

    def test_bad_pattern_type_exits_2(self):
        rules = self.rules({"id": "p", "type": "banned_pattern", "severity": "error", "pattern": 5})
        self.assertEqual(run(twin_check.main, ["--rules", rules, os.path.join(FIX, "drafts", "good.md")])[0], 2)

    def test_empty_match_pattern_rejected(self):
        rules = self.rules({"id": "p", "type": "banned_pattern", "severity": "error", "pattern": "/x?/"})
        code, _, err = run(twin_check.main, ["--rules", rules, os.path.join(FIX, "drafts", "good.md")])
        self.assertEqual(code, 2)
        self.assertIn("empty string", err)

    def test_no_phantom_phrases(self):
        pairs = self.p("pairs")
        for i in (1, 2):
            self.write("pairs/p%d.draft.md" % i, "Mail sam%d@example.com now. We ship Friday.\n" % i)
            self.write("pairs/p%d.edited.md" % i, "We ship Friday.\n")
        props = self.p("props.md")
        run(twin_diff.main, ["propose", pairs, "--rules", RULES, "--out", props])
        with open(props, encoding="utf-8") as fh:
            text = fh.read()
        self.assertNotIn('Ban "email"', text)
        self.assertNotIn('Ban "now we', text)
        corpus = self.p("c")
        for i in range(3):
            self.write("c/f%d.md" % i, "Send it to a%d@example.com and your team today.\n" % i)
        out = self.p("p.json")
        run(twin_scan.main, ["--corpus", corpus, "--out", out])
        phrases = [x["phrase"] for x in tl.load_json(out)["corpora"][0]["crutch_phrases"]]
        self.assertFalse(any("email" in ph or "redacted" in ph for ph in phrases), phrases)

    def test_bom(self):
        path = self.write("b.md", "---\ntitle: x\n---\nI think so.\n", encoding="utf-8-sig")
        sents = tl.split_sentences(tl.classify_lines(tl.read_text(path)))
        self.assertEqual([x["text"] for x in sents], ["I think so."])
        rules = self.rules({"id": "h", "type": "banned_phrase", "severity": "error", "phrases": ["i think"]})
        _, out, _ = run(twin_check.main, ["--rules", rules, path, "--format", "json"])
        self.assertEqual(json.loads(out)["results"][0]["hits"][0]["column"], 1)

    def test_github_property_escaping(self):
        self.assertEqual(twin_check._ghp("dir,a:b/f.md"), "dir%2Ca%3Ab/f.md")

    def test_flagged_never_exceeds_sentences(self):
        corpus = self.p("c")
        self.write("c/a.md", "# One \u2014 two\n## Three \u2014 four\n### Five \u2014 six\n\nOne sentence.\n")
        out = self.p("p.json")
        run(twin_scan.main, ["--corpus", corpus, "--out", out])
        c = tl.load_json(out)["corpora"][0]
        self.assertLessEqual(c["flags"]["flagged_sentences"], c["totals"]["sentences"])

    def test_eval_survives_bad_judge_reply(self):
        sys.path.insert(0, os.path.join(ROOT, "validation"))
        import twin_eval
        calls = []

        def fake(model, key, prompt, system=None, schema=None, effort="medium", retries=3):
            calls.append(model)
            if schema:
                return "not json", {"input_tokens": 1, "output_tokens": 1}, "end_turn"
            return "an answer", {"input_tokens": 1, "output_tokens": 1}, "end_turn"

        real, twin_eval.call = twin_eval.call, fake
        os.environ["ANTHROPIC_API_KEY"] = "test-key-not-real"
        out = self.p("eval.json")
        try:
            code, _, _ = run(twin_eval.main, ["--twin", os.path.join(ROOT, "twins", "example", "twin.md"),
                                              "--samples", SAMPLE, "--tests", "ST-01,ST-02", "--out", out])
        finally:
            twin_eval.call = real
            del os.environ["ANTHROPIC_API_KEY"]
        self.assertEqual(code, 0)
        data = tl.load_json(out)
        self.assertTrue(data["complete"])
        self.assertEqual([t["result"] for t in data["tests"]], ["error", "error"])


if __name__ == "__main__":
    unittest.main()
