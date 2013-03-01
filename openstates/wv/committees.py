import re

from billy.scrape.committees import CommitteeScraper, Committee

import lxml.html


class WVCommitteeScraper(CommitteeScraper):
    jurisdiction = "wv"

    def scrape(self, chamber, term):
        getattr(self, 'scrape_' + chamber)()

    def scrape_lower(self):
        url = 'http://www.legis.state.wv.us/committees/house/main.cfm'
        html = self.urlopen(url)
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)

        xpath = '//a[contains(@href, "HouseCommittee")]'
        for link in doc.xpath(xpath):
            text = link.text_content().strip()
            if text == '-':
                continue
            committee = self.scrape_lower_committee(link=link, name=text)
            committee.add_source(url)
            self.save_committee(committee)

    def scrape_lower_committee(self, link, name):
        url = re.sub(r'\s+', '', link.attrib['href'])
        html = self.urlopen(url)
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)

        comm = Committee('lower', name)
        comm.add_source(url)

        xpath = '//a[contains(@href, "delmemview")]'
        for link in doc.xpath(xpath)[2:]:
            name = link.text_content().strip()
            name = re.sub(r'^Delegate\s+', '', name)
            role = link.getnext().text or 'member'
            comm.add_member(name, role.strip())

        return comm

    def scrape_upper(self):
        url = 'http://www.legis.state.wv.us/committees/senate/main.cfm'
        html = self.urlopen(url)
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)

        xpath = '//a[contains(@href, "SenateCommittee")]'
        for link in doc.xpath(xpath):
            text = link.text_content().strip()
            if text == '-':
                continue
            committee = self.scrape_upper_committee(link=link, name=text)
            committee.add_source(url)
            self.save_committee(committee)

    def scrape_upper_committee(self, link, name):
        url = re.sub(r'\s+', '', link.attrib['href'])
        html = self.urlopen(url)
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)

        comm = Committee('upper', name)
        comm.add_source(url)

        xpath = '//a[contains(@href, "senmemview")]'
        for link in doc.xpath(xpath)[2:]:
            name = link.text_content().strip()
            name = re.sub(r'^Delegate\s+', '', name)
            role = link.getnext().text or 'member'
            comm.add_member(name, role.strip())

        return comm
