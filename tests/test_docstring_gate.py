#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Tests for scripts/docstring_gate.py.

The check that carries the weight is `count_added_docstrings`: without it, a
claim saying "I added 40 docstrings" would pay out for 40 added lines of
anything at all. These pin that it counts docstrings and nothing else.
"""
import importlib.util
import os
import unittest
from pathlib import Path

os.environ.setdefault("GITHUB_TOKEN", "dummy")
SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "docstring_gate.py"
spec = importlib.util.spec_from_file_location("docstring_gate_under_test", SCRIPT)
dg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dg)


def diff(*added_lines, path="a/x.py"):
    head = f"diff --git {path} b/{path.split('a/')[-1]}\n--- {path}\n+++ b/{path.split('a/')[-1]}\n@@ -1 +1 @@\n"
    return head + "\n".join(added_lines)


class CountingTests(unittest.TestCase):
    def test_counts_one_line_docstrings(self):
        d = diff('+    """Return the name."""', '+    """Do a thing."""')
        self.assertEqual(dg.count_added_docstrings(d)[0], 2)

    def test_multiline_docstring_counts_once(self):
        d = diff('+    """Summary line.', '+', '+    More detail here.', '+    """')
        doc, total, _ = dg.count_added_docstrings(d)
        self.assertEqual(doc, 1, "a multi-line docstring is one unit, not four")
        self.assertEqual(total, 4)

    def test_plain_code_is_not_a_docstring(self):
        d = diff('+x = 1', '+def f():', '+    return 2')
        self.assertEqual(dg.count_added_docstrings(d)[0], 0)

    def test_comments_are_not_docstrings(self):
        d = diff('+# this is a comment', '+    # another one')
        self.assertEqual(dg.count_added_docstrings(d)[0], 0)

    def test_string_assignment_is_not_a_docstring(self):
        """The abuse case: padding a diff with triple-quoted values."""
        d = diff('+SQL = """SELECT 1"""', '+    """A real docstring."""')
        # SQL = """...""" does not OPEN at line start, so only the real one counts.
        self.assertEqual(dg.count_added_docstrings(d)[0], 1)

    def test_single_quote_docstrings(self):
        d = diff("+    '''Alt quoting style.'''")
        self.assertEqual(dg.count_added_docstrings(d)[0], 1)

    def test_removed_lines_do_not_count(self):
        d = diff('+    """Kept."""', '-    """Deleted."""')
        self.assertEqual(dg.count_added_docstrings(d)[0], 1)

    def test_files_are_collected(self):
        d = diff('+    """Doc."""', path="a/generation/provider.py")
        self.assertIn("generation/provider.py", dg.count_added_docstrings(d)[2])

    def test_raw_and_unicode_prefixes(self):
        d = diff('+    r"""Raw docstring."""', '+    u"""Unicode docstring."""')
        self.assertEqual(dg.count_added_docstrings(d)[0], 2)


class ClaimParsingTests(unittest.TestCase):
    def test_recognises_docstring_claims(self):
        self.assertTrue(dg.is_docstring_claim("Claim: docs batch 49 - provider.py docstrings", ""))
        self.assertTrue(dg.is_docstring_claim("Bounty claim: BoTTube docstring PR #1683", ""))

    def test_ignores_review_claims(self):
        self.assertFalse(dg.is_docstring_claim("[Bounty Claim] PR Review - RustChain PR #5395", ""))

    def test_pr_url_extraction(self):
        m = dg.PR_RE.search("PR: https://github.com/Scottcjn/bottube/pull/1696")
        self.assertEqual((m.group(1), m.group(2)), ("Scottcjn/bottube", "1696"))

    def test_count_extraction(self):
        for text, want in [
            ("Functions documented: 7 (get_name, ...)", "7"),
            ("Added docstrings to 5 undocumented methods", "5"),
        ]:
            m = dg.COUNT_RE.search(text)
            self.assertIsNotNone(m, text)
            self.assertEqual(m.group(1), want)


if __name__ == "__main__":
    unittest.main()
