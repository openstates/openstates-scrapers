from fiftystates.scrape.committees import CommitteeScraper, Committee

class EXCommitteeScraper(CommitteeScraper):

    state = 'ex'

    def scrape(self, chamber, year):
        com = Committee('lower', 'Committee on Finance')
        com.add_source('http://example.com')
        # can optionally specify role
        com.add_member('Lou Adams', 'chairman')
        com.add_member('Bill Smith')

        # can also specify subcommittees
        subcom = Committee('lower', 'Finance Subcommittee on Banking', 'Committee on Finance')
        com.add_source('http://example.com')
        com.add_member('Bill Smith')
