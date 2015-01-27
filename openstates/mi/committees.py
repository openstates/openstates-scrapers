import re
import urllib

from billy.scrape.committees import CommitteeScraper, Committee
import lxml.html

class MICommitteeScraper(CommitteeScraper):
    jurisdiction = 'mi'

    def scrape(self, chamber, term):
        self.validate_term(term, latest_only=True)

        if chamber == 'lower':
            self.scrape_house_committees()
        else:
            self.scrape_senate_committees()

    def scrape_house_committees(self):
        base_url = 'http://house.mi.gov/MHRPublic/CommitteeInfo.aspx?comkey='
        html = self.urlopen('http://house.mi.gov/mhrpublic/committee.aspx')
        doc = lxml.html.fromstring(html)

        # get values out of drop down
        for opt in doc.xpath('//option'):
            name = opt.text
            # skip invalid choice
            if opt.text in ('Statutory Committees', 'Select One'):
                continue
            if 'have not been created' in opt.text:
                self.warning('no committees yet for the house')
                return
            com_url = base_url + opt.get('value')
            com_html =  self.urlopen(com_url)
            cdoc = lxml.html.fromstring(com_html)
            com = Committee(chamber='lower', committee=name)
            com.add_source(com_url)

            for a in doc.xpath('//a[starts-with(@id, "memberLink")]'):
                name = a.text.strip()

            # all links to http:// pages in servicecolumn2 are legislators
            for a in cdoc.xpath('//div[@class="servicecolumn2"]//a[starts-with(@href, "http")]'):
                name = a.text.strip()
                text = a.xpath('following-sibling::span/text()')[0]
                if 'Committee Chair' in text:
                    role = 'chair'
                elif 'Vice-Chair' in text:
                    role = 'vice chair'
                else:
                    role = 'member'
                com.add_member(name, role=role)

            self.save_committee(com)

    def scrape_senate_committees(self):
        url = 'http://www.senate.michigan.gov/committee.html'
        html = self.urlopen(url)
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)

        for link in doc.xpath('//li/a[contains(@href, "/committee/")]/@href'):
            if link.endswith('appropssubcommittee.html'):
                self.scrape_approp_subcommittees(link)
            elif not link.endswith(('statutory.htm','pdf','taskforce.html')):
                self.scrape_senate_committee(link)


    def scrape_senate_committee(self, url):
        html = self.urlopen(url)
        doc = lxml.html.fromstring(html)

        name = doc.xpath('//h3/text()')[0]
        name = name.replace(' Committee', '')

        com = Committee(chamber='upper', committee=name)

        for member in doc.xpath('//div[@id="committeeright"]//a'):
            member_name = member.text.strip()

            # don't add clerks
            if member_name == 'Committee Clerk':
                continue

            # skip phone links
            if member.get("href").startswith("tel:"):
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
