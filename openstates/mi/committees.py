import re
import urllib

from billy.scrape.committees import CommitteeScraper, Committee
import lxml.html

class MICommitteeScraper(CommitteeScraper):
    state = 'mi'

    def scrape(self, chamber, term):
        self.validate_term(term, latest_only=True)

        if chamber == 'lower':
            self.scrape_house_committees()
        else:
            self.scrape_senate_committees()

    def scrape_house_committees(self):
        base_url = 'http://house.michigan.gov/committeeinfo.asp?'
        with self.urlopen('http://house.michigan.gov/committees.asp') as html:
            doc = lxml.html.fromstring(html)

            # get values out of drop down
            for cname in doc.xpath('//option/@value'):
                # skip subcommittee, redirects to a PDF
                if cname in ('subcommittee', 'statutorycommittee'):
                    continue
                com_url = base_url + urllib.urlencode({'lstcommittees':cname})
                with self.urlopen(com_url) as com_html:
                    cdoc = lxml.html.fromstring(com_html)
                    name = cdoc.xpath('//h4/text()')[0]
                    com = Committee(chamber='lower', committee=name)
                    com.add_source(com_url)

                    # all links to http:// pages in servicecolumn2 are legislators
                    for a in cdoc.xpath('//div[@class="servicecolumn2"]//a[starts-with(@href, "http")]'):
                        name = a.text.strip()
                        text = a.xpath('../following-sibling::font[1]/text()')
                        print text[0],
                        if text[0].startswith('Committee Chair'):
                            role = 'chairman'
                        elif 'Vice-Chair' in text[0]:
                            role = 'vice chairman'
                        else:
                            role = 'member'
                        print role
                        com.add_member(name, role=role)

                    self.save_committee(com)

    def scrape_senate_committees(self):
        url = 'http://www.senate.michigan.gov/committee/committeeinfo.htm'
        with self.urlopen(url) as html:
            doc = lxml.html.fromstring(html)

            for strong in doc.xpath('//strong')[2:]:

                # if this isn't a link, this isn't a normal committee (skip it)
                if not strong.xpath('a'):
                    continue

                # trim off trailing :
                name = strong.text_content()[:-1]
                com = Committee(chamber='upper', committee=name)

                legislators = strong.tail.replace('Senators', '').strip()
                for leg in re.split(', | and ', legislators):
                    if leg.endswith('(C)'):
                        role = 'chairman'
                        leg = leg[:-4]
                    elif leg.endswith('(VC)'):
                        role = 'vice chairman'
                        leg = leg[:-5]
                    elif leg.endswith('(MVC)'):
                        role = 'minority vice chairman'
                        leg = leg[:-6]
                    else:
                        role = 'member'
                    com.add_member(leg, role=role)

                com.add_source(url)
                self.save_committee(com)
