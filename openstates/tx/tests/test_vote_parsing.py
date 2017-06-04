import os

from nose.tools import *  # noqa
import lxml.html

from openstates.tx import votes

here = os.path.dirname(__file__)


def load_fixture(path):
    return lxml.html.fromstring(
        open(os.path.join(here, 'fixtures', path)).read()
    )


class TestVoteParsing(object):
    def test_roll_call(self):
        html = load_fixture('roll_call_vote.html')
        mv = votes.MaybeVote(html.xpath('//div[contains(., "Yeas")]')[0])
        assert_equal(mv.bill_id, 'SR 3')
        assert_equal(mv.chamber, 'upper')
        assert_equal(mv.yeas, 29)
        assert_equal(mv.nays, 2)
        assert_equal(mv.present, 1)
        assert_true(mv.is_valid)
        assert_false(mv.is_amendment)


if __name__ == '__main__':
    unittest.main()
