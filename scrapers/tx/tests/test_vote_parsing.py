import collections
import os

import unittest
import lxml.html

from tx import votes

here = os.path.dirname(__file__)


def load_fixture(path):
    return lxml.html.fromstring(open(os.path.join(here, "fixtures", path)).read())


class TestVoteParsing(unittest.TestCase):
    def test_roll_call(self):
        html = load_fixture("roll_call_vote.html")
        mv = votes.MaybeVote(html.xpath('//div[contains(., "Yeas")]')[0])
        self.assertEqual(mv.bill_id, "SR 3")
        self.assertEqual(mv.chamber, "upper")
        self.assertEqual(mv.yeas, 29)
        self.assertEqual(mv.nays, 2)
        self.assertEqual(mv.present, 1)
        self.assertTrue(mv.is_valid)
        self.assertFalse(mv.is_amendment)

    def test_roll_call_voters_and_counts(self):
        # trimmed from 89RDAY45FINAL
        html = lxml.html.fromstring(
            "<div>"
            '<div class="textpara">SB 503 was read third time.</div><br>'
            '<div class="textpara">SB 503 was passed by (Record 211): '
            "2 Yeas, 1 Nays, 1 Present, not voting.</div><br>"
            '<div class="textpara">Yeas — Alders; Allen.</div><br>'
            '<div class="textpara">Nays — Cain.</div><br>'
            '<div class="textpara">Present, not voting — Mr. Speaker(C).</div><br>'
            '<div class="textpara">Absent, Excused — Cole; Collier.</div><br>'
            '<div class="textpara">Absent — Anchía.</div><br>'
            '<div class="textpara">HB 120 was read third time.</div>'
            "</div>"
        )
        (vote,) = votes.record_votes_with_yeas(html, "89R", "lower", set(), "Burrows")
        counts = {c["option"]: c["value"] for c in vote.counts}
        voters = collections.defaultdict(list)
        for v in vote.votes:
            voters[v["option"]].append(v["voter_name"])
        self.assertEqual(voters["not voting"], ["Burrows"])
        self.assertEqual(voters["absent"], ["Cole", "Collier", "Anchía"])
        self.assertEqual(counts["absent"], 3)
        self.assertEqual(vote.motion_classification, ["passage"])

    def test_failed_of_adoption(self):
        html = lxml.html.fromstring(
            '<div class="textpara">SJR 35 failed of adoption (not receiving the '
            "necessary two-thirds vote) by (Record 2041): 88 Yeas, 0 Nays, 54 "
            "Present, not voting.</div>"
        )
        self.assertFalse(votes.MaybeVote(html).passed)


if __name__ == "__main__":
    unittest.main()
