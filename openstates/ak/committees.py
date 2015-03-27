from billy.scrape.committees import CommitteeScraper, Committee

import lxml.html


class AKCommitteeScraper(CommitteeScraper):
    jurisdiction = 'ak'

    def scrape(self, chamber, term):
        url = ("http://www.legis.state.ak.us/basis/commbr_info.asp"
               "?session=%s" % term)

        page = self.get(url).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        chamber_abbrev = {'upper': 'S', 'lower': 'H'}[chamber]

        for link in page.xpath("//a[contains(@href, 'comm=')]"):
            name = link.text.strip().title()

            if name.startswith('Conference Committee'):
                continue

            url = link.attrib['href']
            if ('comm=%s' % chamber_abbrev) in url:
                self.scrape_committee(chamber, name, url)

    def scrape_committee(self, chamber, name, url):
        page = self.get(url).text
        page = lxml.html.fromstring(page)

        if page.xpath("//h3[. = 'Joint Committee']"):
            chamber = 'joint'

        subcommittee = page.xpath("//h3[@align='center']/text()")[0]
        if not "Subcommittee" in subcommittee:
            subcommittee = None

        comm = Committee(chamber, name, subcommittee=subcommittee)
        comm.add_source(url)

        for link in page.xpath("//a[contains(@href, 'member=')]"):
            member = link.text.strip()

            mtype = link.xpath("string(../preceding-sibling::td[1])")
            mtype = mtype.strip(": \r\n\t").lower()

            comm.add_member(member, mtype)

        if not comm['members']:
            self.warning('not saving %s, appears to be empty' % name)
        else:
            self.save_committee(comm)
