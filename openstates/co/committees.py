import re
import lxml.html

from billy.scrape.committees import CommitteeScraper, Committee

COMMITTEE_URL = ("https://www.colorado.gov/pacific/cga-legislativecouncil/committees-3")


class COCommitteeScraper(CommitteeScraper):
    jurisdiction = "co"

    def lxmlize(self, url):
        text = self.get(url).text
        page = lxml.html.fromstring(text)
        page.make_links_absolute(url)
        return page, text

    def scrape_page(self, a, chamber, term):
        page, text = self.lxmlize(a.attrib['href'])
        committee = a.text_content()
        twitter_ids = re.findall("setUser\('(.*)'\)", text)
        twitter_id = twitter_ids[0] if twitter_ids != [] else None
        roles = {
            ", Chair": "chair",
            ", Vice-Chair": "member"
        }

        committee = Committee(chamber, committee,
                              twitter=twitter_id)

        committee.add_source(a.attrib['href'])

        tables = page.xpath("//table")
        added = False

        seen_people = set([])
        for table in tables:
            people = table.xpath(
                ".//a[contains(@href, 'MemberDetailPage')]")
            for person in people:
                person = person.text_content().strip()
                role = "member"
                for flag in roles:
                    if person.endswith(flag):
                        role = roles[flag]
                        person = person[:-len(flag)].strip()
                if person in seen_people:
                    continue

                if person in "":
                    continue

                seen_people.add(person)
                committee.add_member(person, role)
                added = True

        if added:
            self.save_committee(committee)
            return

        tables = page.xpath("//table")
        added = False
        seen_people = set([])
        for table in tables:
            if "committee members" in table.text_content().lower():
                for person in table.xpath(".//td/text()"):
                    person = person.strip()
                    if person != "":
                        if person in seen_people:
                            continue
                        seen_people.add(person)
                        committee.add_member(person, "member")
                        added = True

        if added:
            self.save_committee(committee)
            return

        self.warning("Unable to scrape!")

    def scrape(self, term, chambers):
        page, _ = self.lxmlize(COMMITTEE_URL)
        comms = page.xpath(".//li[contains(@class, 'is-leaf')]")
        chambers = {'senate':'upper',
                    'house':'lower',
                    'joint':'joint'}
        for comm in comms:
            link = comm.xpath('./a')[0]
            if re.search(r'\d\d\d\d', link.text):
                #this is an archive of a previous year, ditch it
                continue
            chamber = 'joint'
            for c in chambers:
                if c in link.attrib['href']:
                    chamber = chambers[c]
            if chamber:
                self.scrape_page(link, chamber, term)
