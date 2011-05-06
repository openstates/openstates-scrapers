from billy.scrape.committees import CommitteeScraper, Committee
import lxml.html
import re


class DCCommitteeScraper(CommitteeScraper):
    state = 'dc'

    def scrape(self, chamber, term):
        # do nothing if they're trying to get a lower chamber
        if chamber == 'lower':
            return

        url = 'http://www.dccouncil.washington.dc.us/committeesoveriew'

        with self.urlopen(url) as data:
            doc = lxml.html.fromstring(data)

            # skip first & last (non-committees)
            for c in doc.xpath('//strong[starts-with(text(), "COMMITTEE ON")]'):
                com = Committee('upper', c.text_content())

                following_divs = c.xpath('../following-sibling::div')
                if not following_divs:
                    following_divs = c.xpath('../../following-sibling::div')

                for div in following_divs:
                    name = div.text_content().strip()

                    if name and 'COMMITTEE' not in name:
                        if name.endswith('Chairperson'):
                            name = name[:-13]
                            role = 'chairperson'
                        else:
                            role = 'member'
                        com.add_member(name, role=role)
                    else:
                        break

                com.add_source(url)
                self.save_committee(com)
