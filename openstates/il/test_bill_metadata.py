#!/usr/bin/env python

import unittest
from openstates.il import metadata
from openstates.il.bills import DOC_TYPES, ILBillScraper

class TestBillMetadata(unittest.TestCase):
    """Run a basic sanity check to ensure that something would get scraped for each session in the metadata"""
    
    def setUp(self):
        self.scraper = ILBillScraper(metadata)

    def test_lists(self):
        chambers = ['H','S']
        sessions = []
        for term in metadata['terms']:
            sessions.extend(term['sessions'])
        self.assertTrue(len(sessions) > 0, "Expected non-zero list of sessions")

        for session in sessions:
            for chamber in chambers:
                session_chamber_count = 0
                for doc_type in DOC_TYPES:
                    session_chamber_count += len(list(self.scraper.get_bill_urls(chamber, session, doc_type)))
                self.assertTrue(session_chamber_count > 0, "Expected non-zero bill count for Session %s, Chamber %s" % (session, chamber))

if __name__ == '__main__':
    unittest.main()

