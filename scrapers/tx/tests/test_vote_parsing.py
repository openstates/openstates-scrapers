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


def journal(*paragraphs):
    # padded like a real journal: the parser looks at the paragraphs around
    # the vote
    paragraphs = ("(Speaker in the chair)",) + paragraphs + ("(Speaker in the chair)",)
    return lxml.html.fromstring(
        "<div>"
        + "<br>".join('<div class="textpara">%s</div>' % p for p in paragraphs)
        + "</div>"
    )


class TestMotionText(unittest.TestCase):
    def motion(self, *paragraphs):
        (vote,) = votes.record_votes_with_yeas(
            journal(*paragraphs), "892", "lower", set(), "Burrows"
        )
        return vote.motion_text, vote.motion_classification

    def test_unnamed_motion_is_not_passage(self):
        # 89C2DAY04FINAL: a request to extend speaking time on CSHB 4
        self.assertEqual(
            self.motion(
                "Pursuant to Rule 5, Section 28, of the House Rules, "
                "Representative Thompson requested an extension of speaking "
                "time on CSHB 4.",
                "The request was granted by (Record 8): 136 Yeas, 1 Nays, "
                "0 Present, not voting.",
            ),
            ("other", []),
        )

    def test_bill_passed_to_engrossment(self):
        self.assertEqual(
            self.motion(
                "CSHB 4, as amended, was passed to engrossment by (Record 25): "
                "88 Yeas, 52 Nays, 0 Present, not voting."
            ),
            ("passage to engrossment", ["passage"]),
        )

    def test_bill_passed_to_third_reading(self):
        self.assertEqual(
            self.motion(
                "SB 8 was passed to third reading by (Record 40): 85 Yeas, "
                "50 Nays, 1 Present, not voting."
            ),
            ("passage", ["passage"]),
        )

    def test_bill_result_beats_previous_motion(self):
        # 89S2SJ: the paragraph before names the motion to place HB 4 on
        # final passage, but this vote is the passage itself
        self.assertEqual(
            self.motion(
                "Senator King moved that HB 4 be placed on final passage.",
                "HB 4 was passed by the following vote: Yeas 18, Nays 11.",
            ),
            ("passage", ["passage"]),
        )

    def test_resolution_adopted(self):
        self.assertEqual(
            self.motion(
                "SR 26, Recognizing the service of a senator.",
                "On motion of Senator Perry and by unanimous consent, the "
                "resolution was considered immediately and was adopted by the "
                "following vote: Yeas 31, Nays 0.",
            ),
            ("adoption", ["passage"]),
        )

    def test_amendment_vote_stays_amendment(self):
        self.assertEqual(
            self.motion(
                "The amendment to HB 900 was read and failed of adoption by "
                "the following vote: Yeas 12, Nays 19."
            ),
            ("adoption of amendment", ["amendment"]),
        )

    def test_motion_named_in_vote_sentence(self):
        self.assertEqual(
            self.motion(
                "CSHB 4 - (consideration continued)",
                "The motion to table prevailed by (Record 30): 87 Yeas, "
                "52 Nays, 1 Present, not voting.",
            ),
            ("table", []),
        )

    def test_bill_again_finally_passed(self):
        self.assertEqual(
            self.motion(
                "SB 1 as again amended was finally passed by the following "
                "vote: Yeas 20, Nays 11."
            ),
            ("passage", ["passage"]),
        )

    def test_verified_vote_takes_motion_of_vote_it_verifies(self):
        # 89RDAY55FINAL
        html = journal(
            "HB 3326, A bill to be entitled An Act relating to certain duties "
            "of a public institution of higher education.",
            "The vote of the house was taken on final passage of HB 3326 and "
            "the vote was announced yeas 69, nays 70.",
            "A verification of the vote was requested and was granted.",
            "The roll of those voting yea and nay was again called and the "
            "verified vote resulted, as follows (Record 1276): 69 Yeas, "
            "71 Nays, 1 Present, not voting.",
        )
        announced, verified = votes.record_votes_with_yeas(
            html, "89R", "lower", set(), "Burrows"
        )
        self.assertEqual(
            (announced.motion_text, announced.motion_classification),
            ("passage", ["passage"]),
        )
        self.assertEqual(
            (verified.motion_text, verified.motion_classification),
            ("passage", ["passage"]),
        )
        self.assertEqual(verified.result, "fail")
