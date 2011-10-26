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
                        if text[0].startswith('Committee Chair'):
                            role = 'chairman'
                        elif 'Vice-Chair' in text[0]:
                            role = 'vice chairman'
                        else:
                            role = 'member'
                        com.add_member(name, role=role)

                    self.save_committee(com)

    def scrape_senate_committees(self):
        base_url = 'http://www.senate.michigan.gov/committee/'
        url = 'http://www.senate.michigan.gov/committee/committeeinfo.shtm'
        with self.urlopen(url) as html:
            doc = lxml.html.fromstring(html)

            for opt in doc.xpath('//option/@value'):
                com_url = base_url + opt
                if opt == 'appropssubcommittee.htm':
                    self.scrape_approp_subcommittees(com_url)
                elif opt != 'statutory.htm':
                    self.scrape_senate_committee(com_url)


    def scrape_senate_committee(self, url):
        html = self.urlopen(url)
        doc = lxml.html.fromstring(html)

        name = doc.xpath('//h6/text()')[0]

        com = Committee(chamber='upper', committee=name)

        for member in doc.xpath('//div[@id="committeelist"]//a'):
            member_name = member.text.strip()

            # don't add clerks
            if member_name == 'Committee Clerk':
                continue

            if 'Committee Chair' in member.tail:
                role = 'chair'
            elif 'Majority Vice' in member.tail:
                role = 'majority vice chair'
            elif 'Minority Vice' in member.tail:
                role = 'minority vice chair'
            else:
                role = 'member'

            com.add_member(member_name, role=role)

        com.add_source(url)
        self.save_committee(com)


    def scrape_approp_subcommittees(self, url):
        html = self.urlopen(url)
        doc = lxml.html.fromstring(html)

        for strong in doc.xpath('//strong'):
            com = Committee(chamber='upper', committee='Appropriations',
                            subcommittee=strong.text.strip())
            com.add_source(url)

            legislators = strong.getnext().tail.replace('Senators', '').strip()
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

            self.save_committee(com)
