import re

from billy.scrape.committees import CommitteeScraper, Committee

import lxml.html


class WVCommitteeScraper(CommitteeScraper):
    jurisdiction = "wv"

    # Manually resolved links between subcommittees and parent committees.
    subcommittee_parent_map = {
        'Post Audits Subcommittee': 'Government and Finance',
        'Parks, Recreation and Natural Resources Subcommittee': \
            'Government and Finance',
        'Tax Reform Subcommittee A': 'Joint Tax Reform',
    }

    def scrape(self, chamber, term):
        getattr(self, 'scrape_' + chamber)()

    def scrape_lower(self):
        url = 'http://www.legis.state.wv.us/committees/house/main.cfm'
        html = self.get(url).text
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

        url = 'http://www.legis.state.wv.us/committees/interims/interims.cfm'
        html = self.get(url).text
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)
        xpath = '//a[contains(@href, "committee.cfm")]'
        for link in doc.xpath(xpath):
            text = link.text_content().strip()
            if text == '-':
                continue
            committee = self.scrape_interim_committee(link=link, name=text)
            committee.add_source(url)
            self.save_committee(committee)

    def scrape_lower_committee(self, link, name):
        url = re.sub(r'\s+', '', link.attrib['href'])
        html = self.get(url).text
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)

        comm = Committee('lower', name)
        comm.add_source(url)

        xpath = '//a[contains(@href, "?member=")]'
        for link in doc.xpath(xpath):
            name = link.text_content().strip()
            name = re.sub(r'^Delegate\s+', '', name)
            role = link.getnext().text or 'member'
            comm.add_member(name, role.strip())

        return comm

    def scrape_interim_committee(self, link, name):
        url = re.sub(r'\s+', '', link.attrib['href'])
        html = self.get(url).text
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)

        if 'Subcommittee' in name:
            # Check whether the parent committee is manually defined first
            # before attempting to automatically resolve it.
            parent = WVCommitteeScraper.subcommittee_parent_map.get(name, None)
            if parent is None:
                parent = name.partition('Subcommittee')[0].strip()

            comm = Committee('joint', parent, subcommittee=name)
        else:
            comm = Committee('joint', name)
        comm.add_source(url)

        xpath = '//a[contains(@href, "?member=")]'
        for link in doc.xpath(xpath):
            name = link.text_content().strip()
            name = re.sub(r'^Delegate\s+', '', name)
            name = re.sub(r'^Senator\s+', '', name)
            role = link.getnext().text or 'member'
            comm.add_member(name, role.strip())

        return comm

    def scrape_upper(self):
        url = 'http://www.legis.state.wv.us/committees/senate/main.cfm'
        html = self.get(url).text
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
        html = self.get(url).text
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)

        comm = Committee('upper', name)
        comm.add_source(url)

        xpath = '//a[contains(@href, "?member=")]'
        for link in doc.xpath(xpath):
            name = link.text_content().strip()
            name = re.sub(r'^Delegate\s+', '', name)
            role = link.getnext().text or 'member'
            comm.add_member(name, role.strip())

        return comm
