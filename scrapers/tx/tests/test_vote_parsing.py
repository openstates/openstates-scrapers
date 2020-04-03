import os

import unittest
import lxml.html

from ..tx import votes

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


if __name__ == "__main__":
    unittest.main()
