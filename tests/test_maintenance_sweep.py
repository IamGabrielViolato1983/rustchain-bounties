#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Tests for scripts/maintenance_sweep.py.

The correctness risk that matters: this org has TWO maintainer identities
(Scottcjn and sophiaeagent-beep). If only one is recognised, a reply from the
other is read as an external contributor speaking, and the thread is reported
as "waiting on us" forever. Conversely a bot's own comment must not clear a
thread that a human is still waiting on.
"""
import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "maintenance_sweep.py"
spec = importlib.util.spec_from_file_location("sweep_under_test", SCRIPT)
ms = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ms)


class MaintainerIdentityTests(unittest.TestCase):
    def test_both_maintainer_identities_recognised(self):
        self.assertTrue(ms.is_maintainer("Scottcjn"))
        self.assertTrue(ms.is_maintainer("sophiaeagent-beep"))

    def test_case_insensitive(self):
        self.assertTrue(ms.is_maintainer("SCOTTCJN"))
        self.assertTrue(ms.is_maintainer("SophiaEagent-Beep"))

    def test_bots_count_as_us(self):
        for b in ["github-actions[bot]", "dependabot[bot]", "renovate", "copilot"]:
            self.assertTrue(ms.is_maintainer(b), b)

    def test_any_bot_suffix(self):
        self.assertTrue(ms.is_maintainer("some-random-thing[bot]"))

    def test_contributors_are_not_maintainers(self):
        for c in ["leanworld7-netizen", "jaxint", "2balmprune",
                  "Vyacheslav-Tomashevskiy", "waterWang"]:
            self.assertFalse(ms.is_maintainer(c), c)

    def test_empty_is_not_maintainer(self):
        self.assertFalse(ms.is_maintainer(""))
        self.assertFalse(ms.is_maintainer(None))

    def test_lookalike_is_not_maintainer(self):
        """A name merely containing a maintainer's is still external."""
        self.assertFalse(ms.is_maintainer("scottcjn-fan"))
        self.assertFalse(ms.is_maintainer("not-scottcjn"))


class ClassifyTests(unittest.TestCase):
    def setUp(self):
        self._orig = ms.gh_json

    def tearDown(self):
        ms.gh_json = self._orig

    def _item(self, author, n_comments):
        return {"user": {"login": author}, "comments": n_comments,
                "comments_url": "u", "created_at": "2026-07-01T00:00:00Z"}

    def test_external_with_no_comments_is_never_answered(self):
        b, who, _ = ms.classify(self._item("alice", 0), {})
        self.assertEqual(b, "NEVER_ANSWERED")
        self.assertEqual(who, "alice")

    def test_our_own_untouched_pr_is_not_owed_a_reply(self):
        b, _, _ = ms.classify(self._item("Scottcjn", 0), {})
        self.assertIsNone(b)

    def test_beep_own_untouched_pr_is_not_owed_a_reply(self):
        """The second identity must behave identically to the first."""
        b, _, _ = ms.classify(self._item("sophiaeagent-beep", 0), {})
        self.assertIsNone(b)

    def test_contributor_spoke_last_is_ball_in_our_court(self):
        ms.gh_json = lambda a, d: [{"user": {"login": "alice"},
                                    "created_at": "2026-07-20T00:00:00Z"}]
        b, who, when = ms.classify(self._item("alice", 1), {})
        self.assertEqual(b, "BALL_IN_OUR_COURT")
        self.assertEqual(who, "alice")
        self.assertEqual(when, "2026-07-20")

    def test_beep_reply_clears_the_thread(self):
        """A reply from the SECOND identity must count as answered."""
        ms.gh_json = lambda a, d: [{"user": {"login": "alice"},
                                    "created_at": "2026-07-20T00:00:00Z"},
                                   {"user": {"login": "sophiaeagent-beep"},
                                    "created_at": "2026-07-21T00:00:00Z"}]
        b, _, _ = ms.classify(self._item("alice", 2), {})
        self.assertEqual(b, "MOVED_RECENTLY")

    def test_contributor_after_maintainer_reopens_the_ball(self):
        ms.gh_json = lambda a, d: [{"user": {"login": "Scottcjn"},
                                    "created_at": "2026-07-20T00:00:00Z"},
                                   {"user": {"login": "alice"},
                                    "created_at": "2026-07-22T00:00:00Z"}]
        b, _, _ = ms.classify(self._item("alice", 2), {})
        self.assertEqual(b, "BALL_IN_OUR_COURT")


if __name__ == "__main__":
    unittest.main()
