#!/usr/bin/env python

import unittest
from .il import metadata
from .il.bills import DOC_TYPES, ILBillScraper
import logging

log = logging.getLogger("openstates.il.tests.test_bill_metadata")


class TestBillMetadata(unittest.TestCase):
    """Run a basic sanity check to ensure that something would get scraped for each session in the metadata"""

    def setUp(self):
        self.scraper = ILBillScraper(metadata, "/tmp", True)

    @unittest.skip("fixme")
    def test_lists(self):
        chambers = ["H", "S"]
        sessions = []
        for term in metadata["terms"]:
            sessions.extend(term["sessions"])
        self.assertTrue(len(sessions) > 0, "Expected non-zero list of sessions")

        for session in sessions:
            for chamber in chambers:
                session_chamber_count = 0
                for doc_type in DOC_TYPES:
                    count = len(
                        list(self.scraper.get_bill_urls(chamber, session, doc_type))
                    )
                    log.info(
                        "Session: %s Chamber: %s Doc Type: %s Count: %i"
                        % (session, chamber, doc_type, count)
                    )
                    session_chamber_count += count
                self.assertTrue(
                    session_chamber_count > 0,
                    "Expected non-zero bill count for Session %s, Chamber %s"
                    % (session, chamber),
                )


if __name__ == "__main__":
    unittest.main()
